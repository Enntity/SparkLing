# SPDX-License-Identifier: AGPL-3.0-only
"""Compare routed expert outputs read from three Air-VL checkpoints, on the CPU."""
import argparse
import json
from pathlib import Path
import random
import struct

from safetensors import safe_open
import torch


class Checkpoint:
    def __init__(self, root):
        self.root = root
        self.files = json.loads((root / 'model.safetensors.index.json').read_text())['weight_map']

    def read(self, name, raw=False):
        path = self.root / self.files[name]
        if raw:
            # Some safetensors versions cannot decode E8M0. Read the stored bytes.
            with path.open('rb') as stream:
                length, = struct.unpack('<Q', stream.read(8))
                tensor = json.loads(stream.read(length))[name]
                begin, end = tensor['data_offsets']
                stream.seek(8 + length + begin)
                data = bytearray(stream.read(end - begin))
            return torch.frombuffer(data, dtype=torch.uint8).reshape(tensor['shape'])
        with safe_open(path, framework='pt') as handle:
            return handle.get_tensor(name)


def unpack(packed, scales, group_size):
    pair = torch.stack((packed & 15, packed >> 4), dim=-1).flatten(1)
    codebook = torch.tensor([0., .5, 1., 1.5, 2., 3., 4., 6.])
    values = torch.where(pair < 8, 1., -1.) * codebook[(pair & 7).long()]
    return (values.reshape(*scales.shape, group_size) * scales[:, :, None]).flatten(1)


def weight(cp, name, kind):
    if kind == 'bf16':
        return cp.read(name + '.weight').float()
    if kind == 'mxfp4':
        scales = torch.exp2(cp.read(name + '.weight_scale_inv', raw=True).float() - 127)
        return unpack(cp.read(name + '.weight', raw=True), scales, 32)
    scales = cp.read(name + '.weight_scale').float() / cp.read(name + '.weight_global_scale').float()
    return unpack(cp.read(name + '.weight_packed'), scales, 16)


def compare(original, candidate):
    original = original.flatten().double()
    candidate = candidate.flatten().double()
    return dict(error=(original - candidate).square().sum().item(),
                energy=original.square().sum().item(),
                cosine=torch.nn.functional.cosine_similarity(original, candidate, dim=0).item())


def forward(matrices, x, layer):
    gate, up, down = matrices
    activated = torch.nn.functional.silu(x @ gate.T)
    branch = x @ up.T
    if layer >= 35:
        activated = activated.clamp(max=4.)
        branch = branch.clamp(-4., 4.)
    return (activated * branch) @ down.T


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('bf16', 'mxfp4', 'nvfp4'):
        parser.add_argument(key, type=Path)
    args = parser.parse_args()
    checkpoints = {kind: Checkpoint(root) for kind, root in vars(args).items()}
    rng = random.Random(12031)
    torch.manual_seed(12031)
    torch.set_num_threads(4)
    samples = []
    for layer in (2, 10, 21, 34, 41):
        for expert in rng.sample(range(512), 3):
            prefix = f'model.layers.{layer}.mlp.experts.{expert}.'
            matrices = {kind: [weight(cp, prefix + proj, kind) for proj in ('gate_proj', 'up_proj', 'down_proj')]
                        for kind, cp in checkpoints.items()}
            inputs = torch.randn(32, 2560)
            gold = forward(matrices['bf16'], inputs, layer)
            candidates = ('nvfp4', 'mxfp4')
            samples.append(dict(
                layer=layer, expert=expert,
                weight={kind: [compare(a, b) for a, b in zip(matrices['bf16'], matrices[kind])]
                        for kind in candidates},
                output={kind: compare(gold, forward(matrices[kind], inputs, layer)) for kind in candidates}))
    print(json.dumps(dict(inputs='32 seeded synthetic Gaussian hidden states per expert', samples=samples)))


if __name__ == '__main__':
    main()
