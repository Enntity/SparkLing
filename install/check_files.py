#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Verify the complete inference snapshot, including config, processor and template."""
import argparse
import hashlib
import json
from pathlib import Path


def verify(directory, files):
    for name, entry in files.items():
        path = directory / name
        if path.stat().st_size != entry['bytes']:
            raise ValueError(f'{name}: wrong size')
        if 'sha256' in entry:
            digest, expected = hashlib.sha256(), entry['sha256']
        else:
            digest, expected = hashlib.sha1(), entry['git_blob']
            digest.update(f"blob {entry['bytes']}\0".encode())
        with path.open('rb') as stream:
            for block in iter(lambda: stream.read(4 << 20), b''):
                digest.update(block)
        if digest.hexdigest() != expected:
            raise ValueError(f'{name}: digest mismatch')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('strict', 'spark'))
    parser.add_argument('directory', type=Path)
    args = parser.parse_args()
    pin = json.loads(Path(__file__).with_name('checkpoint.json').read_text())
    verify(args.directory, pin[args.mode]['files'])
