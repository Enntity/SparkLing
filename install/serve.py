#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Translate the container contract (start.sh) into the Atlas launch of
Ling-3.2-air on one DGX Spark. Adapted from SparkQwen's single-Spark path."""
import json
import os
from pathlib import Path
import re
import sys

KERNEL_TARGET = 'ling-3.2-air'
PORT = 8897
SERVED_MODEL_NAME = 'ling-3.2-air-atlas'
MODES = ('strict', 'spark')
DEFAULT_MODE = 'spark'
SPECULATION_FLAGS = ('--speculative', '--dflash', '--draft-model', '--draft-model-alt', '--dflash-gamma',
                     '--num-drafts', '--self-speculative', '--ngram-speculative')
MULTI_RANK_FLAGS = ('--world-size', '--tp-size', '--ep-size', '--rank', '--master-addr', '--master-port')


def tool_guard_args(environ, profile_args):
    """Operator policy is explicit and independent of model/performance profiles."""
    if any(arg.split('=', 1)[0].startswith('--tool-guard') for arg in profile_args):
        raise ValueError('Configure the tool guard with SPARKLING_TOOL_GUARD variables, not profile arguments')
    mode = environ.get('SPARKLING_TOOL_GUARD', 'stream')
    if mode not in ('stream', 'on', 'off'):
        raise ValueError('SPARKLING_TOOL_GUARD must be stream, on or off')
    limit = environ.get('SPARKLING_TOOL_GUARD_MAX_BYTES', '1048576')
    if not re.fullmatch(r'[1-9][0-9]{0,7}', limit) or int(limit) > 67108864:
        raise ValueError('SPARKLING_TOOL_GUARD_MAX_BYTES must be 1 to 67108864')
    result = [f'--tool-guard={mode}', f'--tool-guard-max-bytes={limit}']
    for action in ('ALLOW', 'DENY'):
        value = environ.get(f'SPARKLING_TOOL_GUARD_{action}_HOSTS', '')
        for host in value.split(',') if value else []:
            if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9.-]*|\[[A-Fa-f0-9:.]+\]', host):
                raise ValueError(f'SPARKLING_TOOL_GUARD_{action}_HOSTS requires comma-separated exact hosts, without schemes, ports or wildcards')
            result.append(f'--tool-guard-{action.lower()}-host={host}')
    return result


def _flag_values(args, flag):
    return [a.split('=', 1)[1] if '=' in a else None for a in args if a.split('=', 1)[0] == flag]


def _engine_env(environ, profile):
    # Profile values win over ambient optimization flags; only the reviewed
    # logging knobs and the loop-recovery escape hatch pass through.
    env = {key: value for key, value in environ.items()
           if not key.startswith('ATLAS_') or key.startswith('ATLAS_LOG_')
           or key == 'ATLAS_LOOP_NO_SUPPRESS'}
    env.update(profile['environment'])
    return env


def _memory_share(environ, args):
    """The SPARKLING_GPU_MEMORY_UTILIZATION override, 0.50 to 0.90."""
    util = environ.get('SPARKLING_GPU_MEMORY_UTILIZATION')
    if not util:
        return args
    if not re.fullmatch(r'0\.([5-8][0-9]|90)', util):
        raise ValueError('SPARKLING_GPU_MEMORY_UTILIZATION must be 0.50 to 0.90')
    return [f'--gpu-memory-utilization={util}' if a.startswith('--gpu-memory-utilization=') else a for a in args]


def default_precision(mode, model_id):
    """Spark mode on Ling-3.2-air runs the NVFP4 prompt and decode paths that
    the RigMark table measured. Strict and Air-VL follow their checkpoints."""
    return 'nvfp4' if mode == 'spark' and model_id == 'ling-3.2-air' else 'checkpoint'


def precision_cache_namespace(mode, prefill, decode, model_id='ling-3.2-air', quant='publisher'):
    derived = quant == 'nvfp4' and model_id == 'sante-air-vl' and mode == 'spark'
    if quant != 'publisher' and not derived:
        raise ValueError('NVFP4 quantization requires Air-VL Spark mode')
    if model_id == 'sante-air-vl' and not derived:
        if prefill != 'checkpoint' or decode != 'checkpoint':
            raise ValueError('Air-VL uses checkpoint precision for both phases')
        return f'sante-air-vl-{mode}-kv2'
    if model_id != 'ling-3.2-air' and not derived:
        raise ValueError(f'Unknown SparkLing model {model_id}')
    namespace = 'sante-air-vl-nvfp4-rne-v1-kv2' if derived else mode + '-kv2'
    for phase, precision in [('prefill', prefill), ('decode', decode)]:
        if precision == 'checkpoint':
            continue
        options = ('nvfp4', 'nvfp4-head') if phase == 'decode' else ('nvfp4',)
        if derived and phase == 'decode':
            options += ('nvfp4-mlp-head', 'nvfp4-mlp-fp8-head')
        if precision not in options or mode != 'spark':
            raise ValueError(f"{phase.upper()}_PRECISION accepts checkpoint in either mode or {' / '.join(options)} in spark mode")
        namespace += f'-{phase}-{precision}'
    if decode == 'nvfp4':
        namespace += '-tensor-v2'
    return namespace


def disk_prefix_cache(gb, mode):
    """Engine settings that keep the KV blocks the prefix cache evicts on the
    Spark's disk, in the directory start.sh mounts at /prefix-cache, one
    subdirectory per mode. Recurrent-state snapshots stay in host memory.
    Empty or 0 leaves the tier off."""
    if gb in ('', '0'):
        return {}
    if not re.fullmatch(r'[1-9][0-9]{1,2}', gb) or not 16 <= int(gb) <= 100:
        raise ValueError('SPARKLING_PREFIX_CACHE_GB must be a whole number from 16 to 100')
    return {'ATLAS_KV_NVME_DIR': f'/prefix-cache/{mode}/kv', 'ATLAS_KV_NVME_GB': gb, 'ATLAS_GLM_NVME_FAST': '1'}


def check_prefix_cache_dir(env):
    """The disk tier's directory must be a mount (start.sh makes it): without
    one the engine would fill the container's own filesystem."""
    path = env.get('ATLAS_KV_NVME_DIR', '')
    if path and not os.path.isdir(path):
        raise ValueError(f'{path} is missing: mount a directory on a disk at /prefix-cache '
                         'with <mode>/kv inside (start.sh does), or leave SPARKLING_PREFIX_CACHE_GB unset')


def launch(environ, profile):
    """One engine process on one Spark: no ranks, no fabric."""
    args = list(profile['server_argv'])
    if _flag_values(args, '--kernel-target') != [KERNEL_TARGET]:
        raise ValueError(f'the profile requires --kernel-target={KERNEL_TARGET} exactly once')
    if _flag_values(args, '--kv-cache-dtype') != ['bf16']:
        raise ValueError('the profile requires --kv-cache-dtype=bf16 exactly once')
    if _flag_values(args, '--model-from-path') != ['${model}']:
        raise ValueError('the profile requires --model-from-path=${model} exactly once')
    for flag in MULTI_RANK_FLAGS:
        if _flag_values(args, flag):
            raise ValueError(f'SparkLing runs on one Spark; {flag} is not allowed')
    for flag in SPECULATION_FLAGS:
        if _flag_values(args, flag):
            raise ValueError(f'{flag}: speculation is selected with SPARKLING_DRAFTER, not the profile')
    mode = environ.get('SPARKLING_MODE', DEFAULT_MODE)
    if mode not in MODES:
        raise ValueError('SPARKLING_MODE must be strict or spark')
    model = environ.get('MODEL_PATH', '')
    if not Path(model).is_absolute() or any(c in model for c in '\r\n\0'):
        raise ValueError('MODEL_PATH must be an absolute path')
    env = _engine_env(environ, profile)
    seq_len = int(_flag_values(args, '--max-seq-len')[0])
    if seq_len >= 262144 and mode == 'spark' and environ.get('SPARKLING_MODEL', 'ling-3.2-air') == 'ling-3.2-air':
        env['ATLAS_LING_LONG_KV'] = '1'
        env['ATLAS_KV_MAX_BLOCKS'] = str((seq_len + 15) // 16 + 1)
    if environ.get('SPARKLING_MODEL') == 'sante-air-vl':
        # This checkpoint declares 128K natively. Its 256K recipe uses YaRN.
        env['ATLAS_KV_MAX_BLOCKS'] = str((min(131072, seq_len) + 15) // 16 + 1)
        args = [f'--max-seq-len={min(131072, seq_len)}' if a.startswith('--max-seq-len=')
                else a for a in args]
    if mode == 'strict':
        env.update(profile.get('strict_environment', {}))
        if environ.get('SPARKLING_MODEL') == 'sante-air-vl' and 'ATLAS_KV_MAX_BLOCKS' in env:
            env['ATLAS_KV_MAX_BLOCKS'] = str(min(8193, int(env['ATLAS_KV_MAX_BLOCKS'])))
        # Use the checkpoint's own generation settings and template. Atlas's
        # chat defaults otherwise add min-p, top-n-sigma and tool constraints.
        if '--reference-mode' not in args:
            args.append('--reference-mode')
    precision = environ.get('SPARKLING_PREFILL_PRECISION', 'checkpoint')
    decode_precision = environ.get('SPARKLING_DECODE_PRECISION', 'checkpoint')
    namespace = precision_cache_namespace(mode, precision, decode_precision,
                                          environ.get('SPARKLING_MODEL', 'ling-3.2-air'),
                                          environ.get('SPARKLING_QUANT', 'publisher'))
    drafter = environ.get('SPARKLING_DRAFTER', 'none')
    model_id = environ.get('SPARKLING_MODEL', 'ling-3.2-air')
    if drafter != 'none':
        if drafter == 'ling-mtp' and model_id == 'sante-air-vl' and environ.get('SPARKLING_QUANT') == 'nvfp4' and mode == 'spark':
            namespace += '-ling-mtp1'
        elif drafter == 'mtp' and model_id == 'ling-3.2-air':
            namespace += '-mtp1'
        else:
            raise ValueError('mtp requires the embedded Ling predictor; ling-mtp requires BF16-derived Air-VL NVFP4')
        args += ['--speculative', '--num-drafts=1', '--mtp-quantization=bf16']
        env.update(ATLAS_MTP_DRAFTER_PREFILL='1', ATLAS_MTP_CATCHUP='1')
        if mode == 'spark':
            env['ATLAS_LING_MTP_QUANT_HEAD'] = '1'
    if decode_precision != 'checkpoint':
        # Ling reads historical K/V through the paged MLA kernel. Exact hits
        # restore both the recurrent state and final hidden row.
        env.update(ATLAS_LING_NVFP4_DECODE='1', ATLAS_LING_EXPERT_UNION='tensor', ATLAS_SKINNY_MMA='1',
                   ATLAS_MLA_PREFIX_SKIP='1', ATLAS_MARCONI_EXACT='1', ATLAS_EXACT_DIRECT='1')
    if decode_precision in ('nvfp4-mlp-head', 'nvfp4-mlp-fp8-head'):
        env['ATLAS_LING_NVFP4_MLP_DECODE'] = '1'
    if decode_precision == 'nvfp4-mlp-fp8-head':
        args.append('--lm-head-dtype=fp8')
    if decode_precision in ('nvfp4-head', 'nvfp4-mlp-head'):
        args.append('--lm-head-dtype=nvfp4')
    if precision == 'nvfp4':
        env.update(ATLAS_LING_W4A4_PREFILL='1', ATLAS_BF16_GEMM_CUTLASS='1')
        args = ['--max-prefill-tokens=8192' if a == '--max-prefill-tokens=2048' else a for a in args]
    env.update(SPARKLING_MODE=mode)
    env.update(disk_prefix_cache(environ.get('SPARKLING_PREFIX_CACHE_GB', ''), namespace))
    args = _memory_share(environ, [str(a).replace('${model}', model) for a in args])
    name = environ.get('SERVED_MODEL_NAME', SERVED_MODEL_NAME)
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._/-]{0,127}', name):
        raise ValueError('Invalid SERVED_MODEL_NAME')
    args += ['--bind=127.0.0.1', f'--port={PORT}', f'--model-name={name}']
    args += tool_guard_args(environ, args)
    return ['/usr/local/bin/spark', *args], env


def check_model_dir(model, mode, model_id='ling-3.2-air', selection='publisher', drafter='none'):
    root = Path(model)
    config = json.loads((root/'config.json').read_text())
    if config.get('model_type') != 'bailing_moe_v3_vl':
        raise ValueError('expected bailing_moe_v3_vl')
    quant = config.get('quantization_config', {})
    medical = model_id == 'sante-air-vl'
    if drafter == 'ling-mtp' and (config.get('text_config', {}).get('num_nextn_predict_layers') != 1
                                  or not (root/'draft-provenance.json').is_file()):
        raise ValueError('missing transferred Ling predictor in Air-VL model directory')
    if medical and mode == 'strict' and (quant or config.get('torch_dtype') != 'bfloat16'):
        raise ValueError('Air-VL strict requires the original BF16 checkpoint')
    if selection == 'nvfp4' and (not medical or mode != 'spark' or
                                 quant.get('format') != 'nvfp4-pack-quantized'):
        raise ValueError('Air-VL NVFP4 requires the BF16-derived checkpoint')
    if medical and mode == 'spark' and selection == 'publisher' and (quant.get('routed_experts_quant_method') != 'mxfp4' or
                                       quant.get('routed_experts_group_size') != 32):
        raise ValueError('Air-VL spark requires the publisher MXFP4 checkpoint')
    if not medical and mode == 'strict' and (quant.get('quant_method') != 'fp8' or
                             quant.get('weight_block_size') != [128, 128] or
                             quant.get('activation_scheme') != 'dynamic'):
        raise ValueError('strict requires the original dynamic block-FP8 checkpoint')
    if not medical and mode == 'spark' and quant.get('format') != 'nvfp4-pack-quantized':
        raise ValueError('spark requires the pinned NVFP4A16 checkpoint')
    weights = json.loads((root/'model.safetensors.index.json').read_text())['weight_map']
    if not weights or any(not (root/f).is_file() for f in set(weights.values())):
        raise ValueError('missing indexed weight shard')


def profile_path(environ, here):
    """The launch profile named by SPARKLING_PROFILE (default: default)."""
    name = environ.get('SPARKLING_PROFILE', 'default')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,63}', name):
        raise ValueError('Invalid SPARKLING_PROFILE')
    return here/'profiles'/f'{name}.json'


def release_info(here):
    release = json.loads((here/'release.json').read_text())
    source_path = here/'source-manifest.json'
    if not source_path.is_file():
        source_path = here/'atlas-source.json'
    source = json.loads(source_path.read_text())
    return {'product': release['product'], 'version': release['version'],
            'engine_commit': source['commit'], 'engine_tree': source['tree']}


def print_version(here):
    info = release_info(here)
    print(f"{info['product']} {info['version']}")
    print(f"Atlas {info['engine_commit']}")
    print(f"Engine tree {info['engine_tree']}")


def main():
    here = Path(__file__).resolve().parent
    if sys.argv[1:] == ['--version']:
        print_version(here)
        return
    profile = profile_path(os.environ, here)
    argv, env = launch(os.environ, json.loads(profile.read_text()))
    check_model_dir(env['MODEL_PATH'], env['SPARKLING_MODE'], env.get('SPARKLING_MODEL', 'ling-3.2-air'),
                    env.get('SPARKLING_QUANT', 'publisher'), env.get('SPARKLING_DRAFTER', 'none'))
    check_prefix_cache_dir(env)
    source = json.loads((here/'source-manifest.json').read_text())
    print(json.dumps({'event': 'atlas-recipe-start', **release_info(here), 'profile': profile.stem,
                      'mode': env['SPARKLING_MODE'], 'drafter': env.get('SPARKLING_DRAFTER', 'none'),
                      'source': f"{source['repository']}@{source['commit']}"}), flush=True)
    os.execve(argv[0], argv, env)


if __name__ == '__main__':
    main()
