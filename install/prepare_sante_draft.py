# SPDX-License-Identifier: AGPL-3.0-only
"""Build an experimental Air-VL NVFP4 target with Ling-3.2-air's draft block."""
import argparse
import errno
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import tempfile


def load(path):
    return json.loads(path.read_text())


def link_or_copy(source, destination):
    try:
        os.link(source.resolve(), destination)
    except OSError as error:
        if error.errno != errno.EXDEV:
            raise
        shutil.copyfile(source, destination)


def extract(source, destination, names):
    """Stream just the donor predictor tensors into a safetensors shard."""
    with source.open('rb') as src:
        length, = struct.unpack('<Q', src.read(8))
        header = json.loads(src.read(length))
        data_size = sum(header[key]['data_offsets'][1] - header[key]['data_offsets'][0] for key in names)
        if set(header) - {'__metadata__'} == set(names):
            link_or_copy(source, destination)
            return data_size
        offset = 0
        subset = {'__metadata__': {'format': 'pt'}}
        for key in names:
            begin, end = header[key]['data_offsets']
            subset[key] = {**header[key], 'data_offsets': [offset, offset + end - begin]}
            offset += end - begin
        encoded = json.dumps(subset, separators=(',', ':')).encode()
        encoded += b' ' * (-len(encoded) % 8)
        with destination.open('wb') as dst:
            dst.write(struct.pack('<Q', len(encoded)))
            dst.write(encoded)
            for key in names:
                begin, end = header[key]['data_offsets']
                src.seek(8 + length + begin)
                remaining = end - begin
                while remaining:
                    data = src.read(min(1 << 20, remaining))
                    if not data:
                        raise ValueError(f'{source} has a truncated {key}')
                    dst.write(data)
                    remaining -= len(data)
        return data_size


def assemble(target, donor, out):
    target_config = load(target/'config.json')
    donor_config = load(donor/'config.json')
    geometry = ('hidden_size', 'num_hidden_layers', 'num_attention_heads', 'vocab_size',
                'num_experts', 'num_experts_per_tok', 'kv_lora_rank', 'qk_rope_head_dim')
    target_text = target_config['text_config']
    donor_text = donor_config['text_config']
    if (target_config.get('model_type') != 'bailing_moe_v3_vl'
            or target_config.get('quantization_config', {}).get('format') != 'nvfp4-pack-quantized'
            or target_text.get('num_nextn_predict_layers', 0) != 0
            or donor_text.get('num_nextn_predict_layers') != 1
            or any(target_text[k] != donor_text[k] for k in geometry)):
        raise ValueError('expected Air-VL NVFP4 and a compatible Ling predictor')
    if len(set((target.resolve(), donor.resolve(), out.resolve()))) != 3:
        raise ValueError('input and output directories must differ')
    index = load(target/'model.safetensors.index.json')
    donor_index = load(donor/'model.safetensors.index.json')['weight_map']
    prefix = f"model.layers.{target_text['num_hidden_layers']}."
    groups = {}
    for name, shard in donor_index.items():
        if name.startswith(prefix):
            groups.setdefault(shard, []).append(name)
    if not groups or any(name.startswith(prefix) for name in index['weight_map']):
        raise ValueError('unexpected predictor tensor index')
    receipt = {'target_config_sha256': hashlib.sha256((target/'config.json').read_bytes()).hexdigest(),
               'donor_config_sha256': hashlib.sha256((donor/'config.json').read_bytes()).hexdigest(),
               'donor_shards': {name: len(keys) for name, keys in groups.items()}}
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.is_dir() and (out/'draft-provenance.json').is_file() and load(out/'draft-provenance.json') == receipt:
        return
    if out.exists():
        raise ValueError(f'output already exists with different provenance: {out}')
    with tempfile.TemporaryDirectory(dir=out.parent) as work:
        stage = Path(work)/'view'
        stage.mkdir()
        for src in target.iterdir():
            if src.is_file() and not src.name.startswith('.') and src.name not in ('config.json', 'model.safetensors.index.json'):
                os.link(src.resolve(), stage/src.name)
        for shard, keys in groups.items():
            dest = 'draft-' + shard
            index['metadata']['total_size'] += extract(donor/shard, stage/dest, keys)
            index['weight_map'].update({key: dest for key in keys})
        target_text['num_nextn_predict_layers'] = 1
        (stage/'config.json').write_text(json.dumps(target_config, indent=2))
        (stage/'model.safetensors.index.json').write_text(json.dumps(index))
        (stage/'draft-provenance.json').write_text(json.dumps(receipt, indent=2))
        try:
            stage.rename(out)
        except OSError:
            if not (out/'draft-provenance.json').is_file() or load(out/'draft-provenance.json') != receipt:
                raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('target', 'donor', 'output'):
        parser.add_argument(name, type=Path)
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    pin = load(Path(__file__).with_name('checkpoint.json'))['spark']
    if args.donor.name != pin['revision']:
        parser.error('donor directory must use the pinned Ling A16 revision')
    if args.verify and not args.output.is_dir():
        parser.error('missing prepared draft directory')
    from check_files import verify
    donor_files = ('config.json', 'model.safetensors.index.json', 'experts-layer42.safetensors', 'rest-001.safetensors')
    if not (args.donor/'.sparkling-verified').is_file():
        verify(args.donor, {name: pin['files'][name] for name in donor_files})
    assemble(args.target, args.donor, args.output)
    proof = load(Path(__file__).with_name('checkpoint-sante-draft.json'))
    if proof['source_revision'] != pin['revision']:
        parser.error('donor revision differs from draft manifest')
    if args.verify or not (args.output/'.sparkling-draft-verified').exists():
        verify(args.output, proof['files'])
        expected = load(Path(__file__).with_name('checkpoint-sante-nvfp4.json'))['spark']['files']
        for name in expected.keys() - {'config.json', 'model.safetensors.index.json'}:
            if not (args.output/name).samefile(args.target/name):
                raise ValueError(f'draft view no longer shares the verified target file {name}')
        (args.output/'.sparkling-draft-verified').touch()
