# SPDX-License-Identifier: AGPL-3.0-only
import hashlib
import json
import os
import shutil
import subprocess
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
            # Air-VL's native window: Spark sizes the pool from memory, Strict
            # stops at eight whole windows.
            self.assertIn('--max-seq-len=131072', args)
            self.assertEqual(settings.get('ATLAS_KV_MAX_BLOCKS'), '65537' if mode == 'strict' else None)
            self.assertIn(f'sante-air-vl-{mode}-kv2', settings['ATLAS_KV_NVME_DIR'])
            self.assertIn(f'sante-air-vl-{mode}-kv2', settings['ATLAS_SSM_TIER_SWAP_DIR'])
            with self.assertRaisesRegex(ValueError, 'checkpoint precision'):
                serve.launch({**env, 'SPARKLING_DECODE_PRECISION': 'nvfp4'},
                             json.loads((HERE/'profiles/default.json').read_text()))

    def test_air_spark_download_uses_published_pin_and_reuses_verified_conversion(self):
        pin = json.loads((HERE / 'checkpoint-sante-nvfp4.json').read_text())
        snapshot = pin['spark']
        self.assertEqual(snapshot['repository'], 'Enntity/LingSante-3.1-air-VL-NVFP4')
        self.assertRegex(snapshot['revision'], r'^[a-f0-9]{40}$')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            launcher = root / 'start.sh'
            shutil.copy2(HERE.parent / 'start.sh', launcher)
            (root / 'install').symlink_to(HERE.resolve(), target_is_directory=True)
            hf = root / 'hf'
            hf.write_text('#!/bin/sh\nprintf "%s\\n" "$@" > "$MODEL_ROOT/hf-args"\nexit 42\n')
            hf.chmod(0o755)
            models = root / 'models'
            # The weights alone: the default drafter would also fetch Ling's predictor.
            env = {'PATH': f"{root}:{os.environ['PATH']}", 'HOME': tmp, 'MODEL_ROOT': str(models), 'DRAFTER': 'none'}
            args = [str(launcher), '--model', 'sante-air-vl', '--mode', 'spark', 'download']
            self.assertEqual(subprocess.run(args, env=env).returncode, 42)
            cache = models / snapshot['cache_directory']
            calls = models / 'hf-args'
            self.assertEqual(calls.read_text().splitlines(), [
                'download', snapshot['repository'], '--revision', snapshot['revision'], '--local-dir', str(models.resolve() / cache.name)
            ])
            calls.unlink()
            cache.mkdir()
            (cache / '.sparkling-verified').touch()
            subprocess.run(args, env=env, check=True)
            self.assertFalse(calls.exists())

    def test_air_derived_quant_and_publisher_cache_separation(self):
        profile = json.loads((HERE/'profiles/default.json').read_text())
        env = {'MODEL_PATH': '/model', 'SPARKLING_MODE': 'spark', 'SPARKLING_MODEL': 'sante-air-vl',
               'SPARKLING_QUANT': 'nvfp4', 'SPARKLING_PREFIX_CACHE_GB': '48'}
        _, exact = serve.launch(env, profile)
        args, fast = serve.launch({**env, 'SPARKLING_DECODE_PRECISION': 'nvfp4',
                                  'SPARKLING_PREFILL_PRECISION': 'nvfp4'}, profile)
        self.assertIn('--max-seq-len=131072', args)
        self.assertIn('sante-air-vl-nvfp4-rne-v1-kv2', exact['ATLAS_KV_NVME_DIR'])
        self.assertNotEqual(exact['ATLAS_KV_NVME_DIR'], fast['ATLAS_KV_NVME_DIR'])
        self.assertNotIn('ATLAS_LING_NVFP4_DECODE', exact)
        self.assertEqual(fast['ATLAS_LING_NVFP4_DECODE'], '1')
        for name, head in [('nvfp4-mlp-head', 'nvfp4'), ('nvfp4-mlp-fp8-head', 'fp8')]:
            args, settings = serve.launch({**env, 'SPARKLING_DECODE_PRECISION': name}, profile)
            self.assertIn(f'--lm-head-dtype={head}', args)
            self.assertEqual(settings['ATLAS_LING_NVFP4_MLP_DECODE'], '1')
            self.assertIn(name, settings['ATLAS_KV_NVME_DIR'])
        for invalid in ({'SPARKLING_MODE': 'strict'}, {'SPARKLING_MODEL': 'ling-3.2-air'}):
            with self.assertRaisesRegex(ValueError, 'Air-VL Spark'):
                serve.launch({**env, **invalid}, profile)

    def test_native_draft_requires_a_checkpoint_head(self):
        profile = json.loads((HERE/'profiles/default.json').read_text())
        env = {'MODEL_PATH': '/model', 'SPARKLING_DRAFTER': 'mtp', 'SPARKLING_PREFIX_CACHE_GB': '48'}
        args, settings = serve.launch(env, profile)
        self.assertIn('--speculative', args)
        self.assertIn('--num-drafts=1', args)
        # Up to four active requests draft, verified in one batched forward;
        # from five the batch decodes plainly. Drafter prefill is Atlas's default.
        self.assertEqual(settings['ATLAS_MTP_MAX_SEQS'], '4')
        for obsolete in ('ATLAS_MTP_DRAFTER_PREFILL', 'ATLAS_MTP_CATCHUP'):
            self.assertNotIn(obsolete, settings)
        self.assertTrue(settings['ATLAS_KV_NVME_DIR'].endswith('-mtp1/kv'))
        with self.assertRaisesRegex(ValueError, 'embedded'):
            serve.launch({**env, 'SPARKLING_MODEL': 'sante-air-vl'}, profile)

    def test_transferred_draft_on_medical_nvfp4(self):
        profile = json.loads((HERE/'profiles/default.json').read_text())
        env = {'MODEL_PATH': '/model', 'SPARKLING_MODE': 'spark', 'SPARKLING_QUANT': 'nvfp4',
               'SPARKLING_MODEL': 'sante-air-vl', 'SPARKLING_DRAFTER': 'ling-mtp', 'SPARKLING_PREFIX_CACHE_GB': '48'}
        args, settings = serve.launch(env, profile)
        self.assertIn('--num-drafts=1', args)
        self.assertTrue(settings['ATLAS_KV_NVME_DIR'].endswith('-ling-mtp1/kv'))
        for override in ({'SPARKLING_QUANT': 'publisher'}, {'SPARKLING_MODE': 'strict'}):
            with self.assertRaises(ValueError):
                serve.launch({**env, **override}, profile)

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
            serve.launch({**options, 'SPARKLING_MODE': 'strict'}, profile)
        args, env = serve.launch({**options, 'SPARKLING_MODE': 'spark'}, profile)
        self.assertIn('--max-prefill-tokens=8192', args)
        self.assertEqual(env['ATLAS_LING_W4A4_PREFILL'], '1')
        self.assertEqual(env['ATLAS_KV_NVME_DIR'], '/prefix-cache/spark-kv2-prefill-nvfp4/kv')

    def test_nvfp4_decode_is_explicit_and_keeps_its_own_cache(self):
        profile = json.loads((HERE/'profiles/default.json').read_text())
        options = {'MODEL_PATH': '/model', 'SPARKLING_DECODE_PRECISION': 'nvfp4',
                   'SPARKLING_PREFIX_CACHE_GB': '48'}
        with self.assertRaisesRegex(ValueError, 'spark mode'):
            serve.launch({**options, 'SPARKLING_MODE': 'strict'}, profile)
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
            serve.launch({**options, 'SPARKLING_MODE': 'strict'}, profile)
        args, env = serve.launch({**options, 'SPARKLING_MODE': 'spark'}, profile)
        self.assertIn('--lm-head-dtype=nvfp4', args)
        self.assertEqual(env['ATLAS_LING_EXPERT_UNION'], 'tensor')
        self.assertEqual(env['ATLAS_KV_NVME_DIR'], '/prefix-cache/spark-kv2-decode-nvfp4-head/kv')

    def test_spark_with_the_measured_precision_is_the_default(self):
        profile = json.loads((HERE/'profiles/default.json').read_text())
        args, env = serve.launch({'MODEL_PATH': '/model'}, profile)
        self.assertEqual(env['SPARKLING_MODE'], 'spark')
        self.assertNotIn('--reference-mode', args)
        self.assertEqual(serve.default_precision('spark', 'ling-3.2-air'), 'nvfp4')
        self.assertEqual(serve.default_drafter('spark', 'ling-3.2-air'), 'mtp')
        self.assertEqual(serve.default_precision('spark', 'sante-air-vl', 'nvfp4'), 'nvfp4')
        self.assertEqual(serve.default_drafter('spark', 'sante-air-vl', 'nvfp4'), 'ling-mtp')
        for mode, model_id, quant in [('strict', 'ling-3.2-air', 'publisher'), ('spark', 'sante-air-vl', 'publisher'),
                                      ('strict', 'sante-air-vl', 'publisher')]:
            self.assertEqual(serve.default_drafter(mode, model_id, quant), 'none')
            self.assertEqual(serve.default_precision(mode, model_id, quant), 'checkpoint')
        args, env = serve.launch({'MODEL_PATH': '/model', 'SPARKLING_DRAFTER': 'mtp'}, profile)
        self.assertIn('--speculative', args)
        self.assertEqual(env['ATLAS_MTP_MAX_SEQS'], '4')
        for mode, model_id in [('strict', 'ling-3.2-air'), ('spark', 'sante-air-vl'), ('strict', 'sante-air-vl')]:
            self.assertEqual(serve.default_precision(mode, model_id), 'checkpoint')

    def test_every_profile_decodes_video(self):
        # Ling-3.2-air and Air-VL take video_url input; MP4, WebM and AVI need
        # the image's ffmpeg, which Atlas only runs with this flag.
        for path in (HERE/'profiles').glob('*.json'):
            profile = json.loads(path.read_text())
            self.assertIn('--video-allow-ffmpeg', profile['server_argv'], path.name)
            # Ling turns its loop watchdog off (MODEL.toml), so the plain-decode
            # rollback ring (5.1 GB at eight requests) would never be read.
            self.assertEqual(profile['environment']['ATLAS_SSM_DECODE_RING'], '0', path.name)
            # A 90-second 720p H.264 clip is about 47 MB as a base64 data URI.
            self.assertGreaterEqual(int(profile['environment']['ATLAS_MAX_BODY_BYTES']), 256 << 20, path.name)

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
                # Ling's full window everywhere but the benchmark rig, with a
                # pool sized by memory and no expert paging.
                self.assertEqual(length, 40960 if path.stem == 'rigmark-40k' else 262144, path.name)
                # Spark sizes the pool from memory; Strict streams experts
                # from disk, so its pool stops at whole windows (8 x 262K in
                # 17 GB of latent rows) and leaves the rest to the page cache.
                if mode == 'strict':
                    seqs = min(8, int(next(a.split('=')[1] for a in args if a.startswith('--max-num-seqs='))))
                    self.assertEqual(int(env['ATLAS_KV_MAX_BLOCKS']), seqs * length // 16 + 1, path.name)
                else:
                    self.assertNotIn('ATLAS_KV_MAX_BLOCKS', env)
                self.assertNotIn('ATLAS_LING_LONG_KV', env)
                carveout = path.stem != 'rigmark-40k'
                self.assertEqual(args[1:2] == ['display-carveout'], carveout, path.name)
                if carveout:
                    self.assertIn('--lock=/run/lock/sparkglm/display-carveout.lock', args)
                    off, _ = serve.launch({'MODEL_PATH': '/model', 'SPARKLING_MODE': mode,
                                           'SPARKLING_DISPLAY_CARVEOUT': '0'}, profile)
                    self.assertNotIn('display-carveout', off)
            profile['server_argv'].append('--tp-size=2')
            with self.assertRaisesRegex(ValueError, 'one Spark'):
                serve.launch({'MODEL_PATH': '/model'}, profile)
