# SPDX-License-Identifier: AGPL-3.0-only
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import check_files
import serve

HERE = Path(__file__).parent


class InstallTests(unittest.TestCase):
    def test_published_artifacts_have_separate_pins(self):
        pin = json.loads((HERE / 'checkpoint.json').read_text())
        self.assertEqual(pin['strict']['repository'], 'inclusionAI/Ling-3.2-air')
        self.assertNotEqual(pin['spark']['revision'], pin['strict']['revision'])
        for mode, count in [('strict', 13), ('spark', 43)]:
            files = pin[mode]['files']
            self.assertEqual(sum(f.endswith('.safetensors') for f in files), count)
            self.assertIn('model.safetensors.index.json', files)
            self.assertIn('chat_template.jinja', files)

    def test_sante_checkpoints_context_and_caches(self):
        pin = json.loads((HERE/'checkpoint-sante-air-vl.json').read_text())
        self.assertEqual(pin['strict']['repository'], 'inclusionAI/LingSante-3.1-air-VL')
        self.assertEqual(pin['spark']['repository'], 'inclusionAI/LingSante-3.1-air-VL-MXFP4')
        for mode in serve.MODES:
            files = pin[mode]['files']
            self.assertEqual(sum(n.endswith('.safetensors') for n in files), 50)
            self.assertIn('processor_config.json', files)
            env = {'MODEL_PATH': '/model', 'SPARKLING_MODE': mode, 'SPARKLING_MODEL': 'sante-air-vl',
                   'SPARKLING_PREFIX_CACHE_GB': '48'}
            args, settings = serve.launch(env, json.loads((HERE/'profiles/default.json').read_text()))
            self.assertIn('--max-seq-len=131072', args)
            self.assertEqual(settings['ATLAS_KV_MAX_BLOCKS'], '8193')
            self.assertIn(f'sante-air-vl-{mode}-kv2', settings['ATLAS_KV_NVME_DIR'])
            with self.assertRaisesRegex(ValueError, 'checkpoint precision'):
                serve.launch({**env, 'SPARKLING_DECODE_PRECISION': 'nvfp4'},
                             json.loads((HERE/'profiles/default.json').read_text()))

    def test_immutable_weight_and_template_checks(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            content = b'abc'
            (directory/'weights').write_bytes(content)
            (directory/'template').write_bytes(content)
            pin = {'weights': {'bytes': 3, 'sha256': hashlib.sha256(content).hexdigest()},
                   'template': {'bytes': 3, 'git_blob': hashlib.sha1(b'blob 3\0abc').hexdigest()}}
            check_files.verify(directory, pin)
            (directory/'template').write_bytes(b'xyz')
            with self.assertRaisesRegex(ValueError, 'template'):
                check_files.verify(directory, pin)

    def test_nvfp4_prefill_is_explicit_and_keeps_its_own_cache(self):
        profile = json.loads((HERE/'profiles/default.json').read_text())
        options = {'MODEL_PATH': '/model', 'SPARKLING_PREFILL_PRECISION': 'nvfp4',
                   'SPARKLING_PREFIX_CACHE_GB': '48'}
        with self.assertRaisesRegex(ValueError, 'spark mode'):
            serve.launch(options, profile)
        args, env = serve.launch({**options, 'SPARKLING_MODE': 'spark'}, profile)
        self.assertIn('--max-prefill-tokens=8192', args)
        self.assertEqual(env['ATLAS_LING_W4A4_PREFILL'], '1')
        self.assertEqual(env['ATLAS_KV_NVME_DIR'], '/prefix-cache/spark-kv2-prefill-nvfp4/kv')

    def test_nvfp4_decode_is_explicit_and_keeps_its_own_cache(self):
        profile = json.loads((HERE/'profiles/default.json').read_text())
        options = {'MODEL_PATH': '/model', 'SPARKLING_DECODE_PRECISION': 'nvfp4',
                   'SPARKLING_PREFIX_CACHE_GB': '48'}
        with self.assertRaisesRegex(ValueError, 'spark mode'):
            serve.launch(options, profile)
        _, env = serve.launch({**options, 'SPARKLING_MODE': 'spark'}, profile)
        self.assertEqual(env['ATLAS_LING_NVFP4_DECODE'], '1')
        self.assertEqual(env['ATLAS_KV_NVME_DIR'], '/prefix-cache/spark-kv2-decode-nvfp4-tensor-v2/kv')
        self.assertNotIn('ATLAS_LING_W4A4_PREFILL', env)
        self.assertEqual(env['ATLAS_LING_EXPERT_UNION'], 'tensor')

    def test_nvfp4_head_uses_separate_weights_and_cache(self):
        profile = json.loads((HERE/'profiles/default.json').read_text())
        options = {'MODEL_PATH': '/model', 'SPARKLING_DECODE_PRECISION': 'nvfp4-head',
                   'SPARKLING_PREFIX_CACHE_GB': '48'}
        with self.assertRaisesRegex(ValueError, 'spark mode'):
            serve.launch(options, profile)
        args, env = serve.launch({**options, 'SPARKLING_MODE': 'spark'}, profile)
        self.assertIn('--lm-head-dtype=nvfp4', args)
        self.assertEqual(env['ATLAS_LING_EXPERT_UNION'], 'tensor')
        self.assertEqual(env['ATLAS_KV_NVME_DIR'], '/prefix-cache/spark-kv2-decode-nvfp4-head/kv')

    def test_launcher_profiles_preserve_the_mode_and_one_spark(self):
        for path in (HERE/'profiles').glob('*.json'):
            profile = json.loads(path.read_text())
            for mode in serve.MODES:
                args, env = serve.launch({'MODEL_PATH': '/model', 'SPARKLING_MODE': mode}, profile)
                self.assertIn('--kernel-target=ling-3.2-air', args)
                self.assertIn('--port=8897', args)
                self.assertEqual(env['SPARKLING_MODE'], mode)
                self.assertEqual('--reference-mode' in args, mode == 'strict')
                length = int(next(a.split('=')[1] for a in args if a.startswith('--max-seq-len=')))
                if mode == 'strict' or length >= 262144:
                    self.assertEqual(int(env['ATLAS_KV_MAX_BLOCKS']), (length + 15) // 16 + 1)
                else:
                    self.assertNotIn('ATLAS_KV_MAX_BLOCKS', env)
            profile['server_argv'].append('--tp-size=2')
            with self.assertRaisesRegex(ValueError, 'one Spark'):
                serve.launch({'MODEL_PATH': '/model'}, profile)
