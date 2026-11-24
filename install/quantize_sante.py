# SPDX-License-Identifier: AGPL-3.0-only
"""Pack Air-VL's original BF16 routed experts as weight-only NVFP4 on one Spark."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import re
import shutil
import struct

from safetensors import safe_open
from safetensors.torch import save_file
import torch
import triton
import triton.language as tl


ROUTED = re.compile(r'model\.layers\.\d+\.mlp\.experts\.\d+\.(gate|up|down)_proj\.weight')


@triton.jit
def _pack(weights, reciprocal_global, packed, scales, count: tl.constexpr, block: tl.constexpr):
    positions = tl.program_id(0) * block + tl.arange(0, block)
    values = tl.load(weights + positions, mask=positions < count, other=0.).to(tl.float32)
    groups = tl.reshape(values, (block // 16, 16))
    reciprocal = tl.load(reciprocal_global)
    scale = tl.minimum(tl.max(tl.abs(groups), 1) * (reciprocal / 6.), 448.).to(tl.float8e4nv)
    scale_pos = tl.program_id(0) * (block // 16) + tl.arange(0, block // 16)
    tl.store(scales + scale_pos, scale, mask=scale_pos < count // 16)
    dequant = scale.to(tl.float32) / reciprocal
    magnitude = tl.abs(groups) / tl.where(dequant[:, None] > 0, dequant[:, None], 1.)
    # The seven E2M1 midpoints alternate which code is even.
    code = ((magnitude > .25).to(tl.int32) + (magnitude >= .75).to(tl.int32)
            + (magnitude > 1.25).to(tl.int32) + (magnitude >= 1.75).to(tl.int32)
            + (magnitude > 2.5).to(tl.int32) + (magnitude >= 3.5).to(tl.int32)
            + (magnitude > 5.).to(tl.int32))
    code |= (groups < 0).to(tl.int32) << 3
    lo, hi = tl.split(tl.reshape(code, (block // 2, 2)))
    output_pos = tl.program_id(0) * (block // 2) + tl.arange(0, block // 2)
    tl.store(packed + output_pos, lo | (hi << 4), mask=output_pos < count // 2)


def quantize(weight):
    if weight.dtype != torch.bfloat16 or weight.ndim != 2 or weight.shape[1] % 16:
        raise ValueError(f'unexpected routed projection: {weight.dtype}, {weight.shape}')
    weight = weight.cuda()
    rows, cols = weight.shape
    peak = weight.abs().amax().float().reshape(1)
    reciprocal = torch.where(peak > 0, 2688. / peak, torch.ones_like(peak))
    packed = torch.empty((rows, cols // 2), device=weight.device, dtype=torch.uint8)
    scales = torch.empty((rows, cols // 16), device=weight.device, dtype=torch.float8_e4m3fn)
    _pack[(triton.cdiv(weight.numel(), 1024),)](weight, reciprocal, packed, scales, weight.numel(), 1024)
    return {'weight_packed': packed.cpu(), 'weight_scale': scales.cpu(), 'weight_global_scale': reciprocal.cpu()}


def pack_shard(source, output):
    tensors = {}
    with safe_open(source, framework='pt') as original:
        for name in original.keys():
            tensor = original.get_tensor(name)
            if ROUTED.fullmatch(name):
                base = name.rsplit('.', 1)[0]
                tensors.update({base + '.' + key: value for key, value in quantize(tensor).items()})
            else:
                tensors[name] = tensor
        temporary = str(output) + '.partial'
        save_file(tensors, temporary, metadata={'format': 'pt'})
        os.replace(temporary, output)


def convert(source, destination):
    config = json.loads((source / 'config.json').read_text())
    if (config['model_type'] != 'bailing_moe_v3_vl' or config.get('quantization_config')
            or config['text_config']['num_hidden_layers'] != 42):
        raise ValueError('expected original BF16 Air-VL')
    source_index = json.loads((source / 'model.safetensors.index.json').read_text())['weight_map']
    index = {}
    total = 0
    for shard in sorted(set(source_index.values())):
        output = destination / shard
        if not output.exists():
            pack_shard(source / shard, output)
        with safe_open(output, framework='pt') as packed:
            index.update({name: shard for name in packed.keys()})
        with output.open('rb') as stream:
            header_bytes, = struct.unpack('<Q', stream.read(8))
        total += output.stat().st_size - 8 - header_bytes
        print(shard, flush=True)

    config['quantization_config'] = {
        'quant_method': 'compressed-tensors', 'format': 'nvfp4-pack-quantized',
        'quantization_status': 'compressed', 'kv_cache_scheme': None,
        'config_groups': {'group_0': {
            'targets': [r're:.*\.mlp\.experts\.\d+\.(gate_proj|up_proj|down_proj)$'],
            'weights': {'num_bits': 4, 'type': 'float', 'strategy': 'tensor_group',
                        'group_size': 16, 'symmetric': True, 'dynamic': False, 'observer': 'minmax'},
            'input_activations': None, 'output_activations': None}},
        'ignore': [r're:^(?!.*\.mlp\.experts(\.|$)).*$', 'lm_head']}
    for name in source_index:
        if name not in index and name.replace('.weight', '.weight_packed') not in index:
            raise ValueError(f'missing {name}')
    for file in source.iterdir():
        if file.is_file() and file.suffix in {'.py', '.jinja', '.json', '.txt'} and file.name not in {
                'config.json', 'model.safetensors.index.json'}:
            shutil.copyfile(file, destination / file.name)
    (destination / 'config.json').write_text(json.dumps(config, indent=2))
    (destination / 'model.safetensors.index.json').write_text(json.dumps({
        'metadata': {'total_size': total}, 'weight_map': index}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    if args.source.resolve() == args.destination.resolve():
        parser.error('source and destination must differ')
    args.destination.mkdir(parents=True, exist_ok=True)
    with (args.destination / '.convert.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        convert(args.source, args.destination)
