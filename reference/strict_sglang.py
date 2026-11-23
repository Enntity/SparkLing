# SPDX-License-Identifier: AGPL-3.0-only
"""Diagnostic TP=1 SGLang file-backed expert placement for GB10. Run in the pinned reference image."""
import ctypes
import math
import mmap
import os
import sys
import tempfile
from unittest.mock import patch

import torch
from triton.backends.nvidia.driver import CudaLauncher
from sglang.srt.layers.quantization.fp8 import Fp8MoEMethod

OWNERS = []
MAPPED_BASES = set()


def allocate(shape, dtype, device):
    driver = ctypes.CDLL('libcuda.so.1')
    device = torch.device(device)
    idx = device.index if device.index is not None else torch.cuda.current_device()
    capability = ctypes.c_int()
    for attribute in (88, 100):
        if driver.cuDeviceGetAttribute(ctypes.byref(capability), attribute, idx) or not capability.value:
            raise RuntimeError('strict disk-backed reference needs coherent pageable GPU access via host page tables')
    size = math.prod(shape)  # only E4M3 tensors
    with tempfile.TemporaryFile(dir=os.environ['LING_EXPERT_DISK']) as f:
        os.posix_fallocate(f.fileno(), 0, size)
        mapping = mmap.mmap(f.fileno(), size, access=mmap.ACCESS_WRITE)
    cpu = torch.frombuffer(mapping, dtype=torch.uint8)
    device = torch.device('cuda', idx)
    storage = torch._C._construct_storage_from_data_pointer(cpu.data_ptr(), device, size)
    stride = []
    width = 1
    for dim in reversed(shape):
        stride.insert(0, width)
        width *= dim
    result = torch.empty(0, device=device, dtype=dtype).set_(storage, 0, shape, stride)
    OWNERS.append((cpu, mapping))
    MAPPED_BASES.add(cpu.data_ptr())
    return result


original = Fp8MoEMethod.create_fp8_moe_weight_


def create_weights(*args, **kwargs):
    empty = torch.empty
    maps_before = len(OWNERS)

    def expert_empty(*size, **kw):
        shape = tuple(size[0]) if len(size) == 1 and isinstance(size[0], (list, tuple)) else size
        if kw.get('dtype') == torch.float8_e4m3fn and len(shape) == 3 and shape[0] in (512, 513):
            if shape[1:] not in ((1536, 2560), (2560, 768)):
                raise ValueError(f'unexpected Ling expert dimensions {shape}')
            return allocate(shape, kw['dtype'], kw.get('device', 'cuda'))
        return empty(*size, **kw)

    with patch.object(torch, 'empty', expert_empty):
        result = original(*args, **kwargs)
    if len(OWNERS) - maps_before != 2:
        raise RuntimeError('strict FP8 expert hook could not identify the two expected allocations')
    return result


Fp8MoEMethod.create_fp8_moe_weight_ = staticmethod(create_weights)
# Triton accepts raw device addresses for coherent GB10 system allocations.
# Hand it only pointers into storage we own, after tensor specialization so
# the published kernel retains the original FP8 signature, strides and shape.
launch = CudaLauncher.__call__

def launch_coherent(self, grid_x, grid_y, grid_z, stream, function, metadata,
                    launch_metadata, enter, leave, *args):
    args = tuple(
        value.data_ptr() if isinstance(value, torch.Tensor)
        and value.untyped_storage().data_ptr() in MAPPED_BASES else value
        for value in args
    )
    return launch(self, grid_x, grid_y, grid_z, stream, function, metadata,
                  launch_metadata, enter, leave, *args)

CudaLauncher.__call__ = launch_coherent

if __name__ == '__main__':
    from sglang.launch_server import load_plugins, prepare_server_args, run_server, kill_process_tree
    load_plugins()
    args = prepare_server_args(sys.argv[1:])
    try:
        run_server(args)
    finally:
        kill_process_tree(os.getpid(), include_parent=False)
