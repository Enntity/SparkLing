# SPDX-License-Identifier: AGPL-3.0-only
"""--model (or SPARKLING_MODEL) picks the pinned checkpoint ./start.sh downloads and serves."""
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def pin(name, mode):
    return json.loads((ROOT/'install'/name).read_text())[mode]['repository']


class Models(unittest.TestCase):
    def download(self, *args, env_text='', **env):
        """The repository ./start.sh asks hf for, or None when it stops first; and its stderr."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shutil.copy2(ROOT/'start.sh', root/'start.sh')
            (root/'install').symlink_to(ROOT/'install', target_is_directory=True)
            (root/'.env').write_text(env_text)
            hf = root/'hf'
            hf.write_text('#!/bin/sh\nprintf "%s\\n" "$@" > "$MODEL_ROOT/hf-args"\nexit 42\n')
            hf.chmod(0o755)
            models = root/'models'
            clean = {k: v for k, v in os.environ.items() if k not in ('MODEL', 'SPARKLING_MODEL', 'MODE', 'QUANT')}
            run = subprocess.run(['bash', str(root/'start.sh'), *args, 'download'], capture_output=True, text=True,
                                 env={**clean, 'PATH': f"{root}:{os.environ['PATH']}", 'HOME': tmp,
                                      'MODEL_ROOT': str(models), 'DRAFTER': 'none', **env})
            calls = models/'hf-args'
            return (calls.read_text().splitlines()[1] if calls.exists() else None), run

    def test_default_is_ling(self):
        for args in [(), ('--model', 'ling-3.2-air')]:
            with self.subTest(args=args):
                self.assertEqual(self.download(*args)[0], pin('checkpoint.json', 'spark'))

    def test_lingsante_by_its_name_by_env_and_by_its_older_name(self):
        spark = pin('checkpoint-sante-nvfp4.json', 'spark')
        cases = [(('--model', 'lingsante-3.1-air-vl'), '', {}),
                 (('--mode', 'spark', '--model', 'lingsante-3.1-air-vl'), '', {}),
                 ((), 'SPARKLING_MODEL=lingsante-3.1-air-vl\n', {}),
                 ((), '', {'SPARKLING_MODEL': 'lingsante-3.1-air-vl'}),
                 (('--model', 'sante-air-vl'), '', {}),
                 ((), 'MODEL=sante-air-vl\n', {})]
        for args, env_text, env in cases:
            with self.subTest(args=args, env_text=env_text, env=env):
                self.assertEqual(self.download(*args, env_text=env_text, **env)[0], spark)
        strict = self.download('--model', 'lingsante-3.1-air-vl', '--mode', 'strict')[0]
        self.assertEqual(strict, pin('checkpoint-sante-air-vl.json', 'strict'))

    def test_unknown_model_is_refused_with_the_names(self):
        repo, run = self.download('--model', 'lingsante')
        self.assertIsNone(repo)
        self.assertEqual(run.returncode, 2)
        self.assertIn('ling-3.2-air or lingsante-3.1-air-vl', run.stderr)


if __name__ == '__main__':
    unittest.main()
