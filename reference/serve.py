#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Run the pinned Ling vLLM reference on exactly one GPU.

Both modes use the requested checkpoint. The publisher's original FP8 recipe
uses four GPUs. Its TP=1 invocation lets operators measure the memory boundary
on their own hardware.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import platform as host_platform
import re
import shlex
import subprocess
import sys
from typing import Any


HERE = Path(__file__).resolve().parent
MANIFEST_PATH = HERE / "manifest.json"
PLATFORMS = ("linux/amd64", "linux/arm64")
MODEL_MODES = ("a16", "strict")
MODEL_TYPE = "bailing_moe_v3_vl"
ARCHITECTURE = "BailingMoeV3VLForConditionalGeneration"
SHA256_IMAGE = re.compile(r"@sha256:[0-9a-f]{64}$")
MODEL_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,127}$")


def load_manifest() -> dict[str, Any]:
    with MANIFEST_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def default_platform() -> str:
    machine = host_platform.machine().lower()
    if machine in {"aarch64", "arm64"}:
        return "linux/arm64"
    if machine in {"x86_64", "amd64"}:
        return "linux/amd64"
    raise ValueError(
        f"cannot map host architecture {machine!r}; pass --platform linux/arm64 or linux/amd64"
    )


def positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an integer") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return parsed


def port_number(value: str) -> int:
    parsed = positive_int(value)
    if parsed > 65535:
        raise argparse.ArgumentTypeError("must be between 1 and 65535")
    return parsed


def memory_utilization(value: str) -> float:
    try:
        parsed = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a decimal fraction") from exc
    if not 0.50 <= parsed <= 0.99:
        raise argparse.ArgumentTypeError("must be between 0.50 and 0.99")
    return parsed


def gpu_index(value: str) -> str:
    if not re.fullmatch(r"[0-9]+", value):
        raise argparse.ArgumentTypeError("must be one GPU index, such as 0")
    return value


def resolve_model_dir(value: str) -> Path:
    if any(char in value for char in "\r\n\0"):
        raise ValueError("--model-dir contains a control character")
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    return path.resolve()


def validate_model_dir(model_dir: Path, expected: dict[str, Any]) -> None:
    if not model_dir.is_dir():
        raise ValueError(f"model directory does not exist: {model_dir}")

    config_path = model_dir / "config.json"
    if not config_path.is_file():
        raise ValueError(f"missing {config_path}")
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in {config_path}: {exc}") from exc

    if config.get("model_type") != expected["model_type"]:
        raise ValueError(
            f"expected model_type={expected['model_type']!r}, got {config.get('model_type')!r}"
        )
    if expected["architecture"] not in config.get("architectures", []):
        raise ValueError(
            f"{config_path} does not declare {expected['architecture']}"
        )

    quantization = config.get("quantization_config") or {}
    for key in ("quant_method", "format", "fmt", "weight_block_size"):
        if key in expected and quantization.get(key) != expected[key]:
            raise ValueError(
                f"expected quantization_config.{key}={expected[key]!r}, "
                f"got {quantization.get(key)!r}"
            )

    index_path = model_dir / "model.safetensors.index.json"
    if not index_path.is_file():
        raise ValueError(f"missing {index_path}")
    try:
        index = json.loads(index_path.read_text(encoding="utf-8"))
        weight_map = index.get("weight_map", {})
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in {index_path}: {exc}") from exc
    if not weight_map:
        raise ValueError(f"{index_path} has no weight_map")
    missing = sorted({str(model_dir / filename) for filename in weight_map.values()
                      if not (model_dir / filename).is_file()})
    if missing:
        preview = ", ".join(missing[:3])
        suffix = " ..." if len(missing) > 3 else ""
        raise ValueError(f"missing indexed weight shard(s): {preview}{suffix}")


def image_reference(
    manifest: dict[str, Any], selected_platform: str, override: str | None,
    allow_unpinned: bool,
) -> str:
    if override:
        if not allow_unpinned and not SHA256_IMAGE.search(override):
            raise ValueError(
                "--image must include an @sha256: digest; pass --allow-unpinned-image "
                "only for a local diagnostic"
            )
        return override

    container = manifest["container"]
    digest = container["platform_digests"].get(selected_platform)
    if not digest:
        raise ValueError(f"manifest has no image digest for {selected_platform}")
    return f"{container['repository']}:{container['tag']}@{digest}"


def build_command(
    manifest: dict[str, Any], mode: str, model_dir: Path, selected_platform: str,
    image: str, gpu: str, port: int, model_name: str, max_model_len: int,
    gpu_memory_utilization: float, max_num_seqs: int = 8,
) -> list[str]:
    spec = manifest["models"][mode]
    command = [
        "docker",
        "run",
        "--rm",
        "--platform",
        selected_platform,
        "--gpus",
        f"device={gpu}",
        "--label", "io.enntity.owner=SparkLing",
        "--label", "io.enntity.job=reference",
        "--ipc=host",
        "--shm-size=32g",
        "--publish",
        f"127.0.0.1:{port}:{manifest['server']['container_port']}",
        "--volume",
        f"{model_dir}:/models/model:ro",
        "--env",
        "HF_HUB_OFFLINE=1",
        "--env",
        "TRANSFORMERS_OFFLINE=1",
        image,
        "--model",
        "/models/model",
        "--trust-remote-code",
        "--tensor-parallel-size",
        str(manifest["server"]["tensor_parallel_size"]),
        "--host",
        "0.0.0.0",
        "--port",
        str(manifest["server"]["container_port"]),
        "--served-model-name",
        model_name,
        "--max-model-len",
        str(max_model_len),
        "--max-num-seqs", str(max_num_seqs),
        "--gpu-memory-utilization",
        f"{gpu_memory_utilization:.2f}",
        "--reasoning-parser",
        "ling3",
        "--enable-auto-tool-choice",
        "--tool-call-parser",
        "ling3",
    ]
    if mode == "strict":
        command.extend([
            "--enable-prefix-caching",
            "--mamba-cache-mode",
            "align",
            "--speculative-config",
            '{"method":"mtp","num_speculative_tokens":3}',
        ])
    return command


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Serve the pinned Ling-3.2-air vLLM reference with TP=1."
    )
    parser.add_argument("--mode", choices=MODEL_MODES, default="a16",
                        help="a16 is the one-Spark reference; strict is the original FP8 diagnostic")
    parser.add_argument("--model-dir", required=True,
                        help="local checkpoint directory downloaded at the manifest revision")
    parser.add_argument("--platform", choices=PLATFORMS,
                        help="Docker target; defaults to the host architecture")
    parser.add_argument("--gpu-device", default="0", type=gpu_index,
                        help="single GPU index passed to Docker (default: 0)")
    parser.add_argument("--port", type=port_number, default=8897,
                        help="host port (default: 8897)")
    parser.add_argument("--served-model-name",
                        help="OpenAI model name (defaults to the pinned mode name)")
    parser.add_argument("--max-num-seqs", type=positive_int, default=8,
                        help="maximum concurrent sequences (default: 8)")
    parser.add_argument("--max-model-len", type=positive_int,
                        help="vLLM context limit (defaults to the pinned mode value)")
    parser.add_argument("--gpu-memory-utilization", type=memory_utilization,
                        help="vLLM GPU memory fraction (defaults to the pinned mode value)")
    parser.add_argument("--image",
                        help="override the pinned image; digest is required unless explicitly allowed")
    parser.add_argument("--allow-unpinned-image", action="store_true",
                        help="allow an image override without @sha256 (diagnostic only)")
    parser.add_argument("--allow-strict-tp1", action="store_true",
                        help=argparse.SUPPRESS)
    parser.add_argument("--skip-model-check", action="store_true",
                        help="only for printing/testing the Docker command")
    parser.add_argument("--pull", action="store_true",
                        help="pull the exact platform image before starting it")
    parser.add_argument("--print-command", "--dry-run", action="store_true", dest="print_command",
                        help="print the exact Docker command and exit")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    manifest = load_manifest()
    spec = manifest["models"][args.mode]

    try:
        selected_platform = args.platform or default_platform()
        model_dir = resolve_model_dir(args.model_dir)
        model_name = args.served_model_name or spec["served_model_name"]
        if not MODEL_NAME.fullmatch(model_name):
            raise ValueError("--served-model-name contains unsupported characters")
        if args.max_model_len is not None:
            max_model_len = args.max_model_len
        else:
            max_model_len = int(spec["defaults"]["max_model_len"])
        if args.gpu_memory_utilization is not None:
            utilization = args.gpu_memory_utilization
        else:
            utilization = float(spec["defaults"]["gpu_memory_utilization"])
        image = image_reference(
            manifest, selected_platform, args.image, args.allow_unpinned_image
        )
        if not args.skip_model_check:
            validate_model_dir(model_dir, spec["expected_config"])
        command = build_command(
            manifest,
            args.mode,
            model_dir,
            selected_platform,
            image,
            args.gpu_device,
            args.port,
            model_name,
            max_model_len,
            utilization,
            args.max_num_seqs,
        )
    except (OSError, KeyError, TypeError, ValueError) as exc:
        parser.error(str(exc))

    if args.pull:
        pull = ["docker", "pull", "--platform", selected_platform, image]
        if args.print_command:
            print(shlex.join(pull))
        else:
            subprocess.run(pull, check=True)

    if args.print_command:
        print(shlex.join(command))
        return 0

    os.execvp(command[0], command)
    return 0


if __name__ == "__main__":
    sys.exit(main())
