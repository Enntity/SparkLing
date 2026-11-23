# SPDX-License-Identifier: AGPL-3.0-only
"""Compare two RigMark receipts from sequential runs on one Spark.

The comparison is strict about the benchmark protocol, checkpoint, appliance
identity and isolation. A result with missing or invalid metrics is unusable.
Ratios and winners are printed as separate facts.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any


REQUIRED_APPLIANCE_FIELDS = (
    "hardware",
    "topology",
    "context_limit",
    "kv_cache_dtype",
    "competing_traffic",
    "model",
    "model_revision",
    "physical_device_id",
)
MATCHED_APPLIANCE_FIELDS = (
    "hardware",
    "topology",
    "context_limit",
    "kv_cache_dtype",
    "competing_traffic",
    "model",
    "model_revision",
    "physical_device_id",
)
REQUIRED_PROTOCOL_FIELDS = (
    "prompts_sha256",
    "prompts_version",
    "repository_revision",
    "repository_source_sha256",
    "version",
)
REQUIRED_SETTING_FIELDS = (
    "concurrency",
    "concurrency_runs",
    "concurrency_tokens",
    "concurrency_workload",
    "decode_tokens",
    "extra_body",
    "prefill_depths",
    "prefill_runs",
    "runs",
    "seed",
    "temperature",
    "top_p",
)


def load(path: str) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"cannot read {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise SystemExit(f"{path}: receipt must be a JSON object")
    return value


def nested(value: Any, *keys: str) -> Any:
    current = value
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            raise KeyError(".".join(keys))
        current = current[key]
    return current


def nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def metadata_present(value: Any) -> bool:
    return nonempty(value) or finite_positive(value)


def finite_positive(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
        and value > 0
    )


def isolated(value: Any) -> bool:
    return nonempty(value) and value.strip().lower().startswith("none")


def check_mapping(
    candidate: dict[str, Any],
    reference: dict[str, Any],
    fields: tuple[str, ...],
    label: str,
) -> list[str]:
    errors = []
    for field in fields:
        if field not in candidate or field not in reference:
            errors.append(f"{label}: missing {field}")
        elif candidate[field] != reference[field]:
            errors.append(f"{label}: {field} differs")
    return errors


def appliance(
    receipt: dict[str, Any], label: str
) -> tuple[dict[str, Any] | None, list[str]]:
    try:
        value = nested(receipt, "run", "appliance")
    except KeyError:
        return None, [f"{label}: missing run.appliance metadata"]
    if not isinstance(value, dict):
        return None, [f"{label}: run.appliance must be an object"]
    errors = []
    for field in REQUIRED_APPLIANCE_FIELDS:
        if field not in value or not metadata_present(value[field]):
            errors.append(f"{label}: missing appliance.{field}")
    return value, errors


def validate_pair(
    candidate: dict[str, Any], reference: dict[str, Any], workload: str
) -> list[str]:
    errors: list[str] = []
    candidate_appliance, candidate_errors = appliance(
        candidate, f"{workload}/candidate"
    )
    reference_appliance, reference_errors = appliance(
        reference, f"{workload}/reference"
    )
    errors.extend(candidate_errors)
    errors.extend(reference_errors)
    if candidate_appliance is not None and reference_appliance is not None:
        errors.extend(
            f"{workload}: {error}"
            for error in check_mapping(
                candidate_appliance,
                reference_appliance,
                MATCHED_APPLIANCE_FIELDS,
                "appliance",
            )
        )

    for label, receipt in (("candidate", candidate), ("reference", reference)):
        try:
            protocol = nested(receipt, "protocol")
            settings = nested(receipt, "settings")
            run = nested(receipt, "run")
        except KeyError as exc:
            errors.append(f"{workload}/{label}: missing {exc.args[0]}")
            continue
        if (
            not isinstance(protocol, dict)
            or not isinstance(settings, dict)
            or not isinstance(run, dict)
        ):
            errors.append(
                f"{workload}/{label}: protocol, settings and run must be objects"
            )
            continue
        for field in REQUIRED_PROTOCOL_FIELDS:
            if field not in protocol or not nonempty(protocol[field]):
                errors.append(f"{workload}/{label}: missing protocol.{field}")
        for field in REQUIRED_SETTING_FIELDS:
            if field not in settings:
                errors.append(f"{workload}/{label}: missing settings.{field}")
        if settings.get("concurrency_workload") != workload:
            errors.append(
                f"{workload}/{label}: settings.concurrency_workload must be {workload!r}"
            )
        if settings.get("extra_body") != {
            "chat_template_kwargs": {"enable_thinking": True}
        }:
            errors.append(
                f"{workload}/{label}: settings.extra_body must enable thinking explicitly"
            )
        for field in ("comparison_id", "model"):
            if not nonempty(run.get(field)):
                errors.append(f"{workload}/{label}: missing run.{field}")
        if not nonempty(run.get("label")) or not run["label"].endswith(
            f"-{workload}"
        ):
            errors.append(f"{workload}/{label}: run.label must end with -{workload}")
        run_appliance = run.get("appliance")
        if not isinstance(run_appliance, dict) or not isolated(
            run_appliance.get("competing_traffic")
        ):
            errors.append(
                f"{workload}/{label}: workload isolation must declare no competing traffic"
            )

    try:
        errors.extend(
            f"{workload}: {error}"
            for error in check_mapping(
                nested(candidate, "run"), nested(reference, "run"),
                ("comparison_id", "model"), "run",
            )
        )
        errors.extend(
            f"{workload}: {error}"
            for error in check_mapping(
                nested(candidate, "protocol"),
                nested(reference, "protocol"),
                REQUIRED_PROTOCOL_FIELDS,
                "protocol",
            )
        )
        errors.extend(
            f"{workload}: {error}"
            for error in check_mapping(
                nested(candidate, "settings"),
                nested(reference, "settings"),
                REQUIRED_SETTING_FIELDS,
                "settings",
            )
        )
    except KeyError:
        pass
    return errors


def gate(receipt: dict[str, Any], workload: str, label: str) -> tuple[str, list[str]]:
    try:
        value = nested(receipt, "decode", workload, "completion_gate")
        passed, total = value["passed"], value["total"]
    except (KeyError, TypeError):
        return "missing", [f"{workload}/{label}: missing completion gate"]
    if (
        not isinstance(passed, int)
        or isinstance(passed, bool)
        or not isinstance(total, int)
        or isinstance(total, bool)
        or total <= 0
        or passed < 0
        or passed > total
    ):
        return "invalid", [
            f"{workload}/{label}: invalid completion gate {passed!r}/{total!r}"
        ]
    errors = [] if passed == total else [f"{workload}/{label}: only {passed}/{total} completions passed"]
    return f"{passed}/{total}", errors


def required_paths(
    receipt: dict[str, Any], workload: str
) -> list[tuple[str, tuple[str, ...]]]:
    try:
        settings = nested(receipt, "settings")
    except KeyError:
        return []
    paths = [
        (
            f"{workload} decode/{section}",
            ("decode", section, "decode_tokens_per_second", "median"),
        )
        for section in ("code", "prose", "structured")
    ]
    concurrency = settings.get("concurrency")
    if not isinstance(concurrency, list) or not concurrency:
        return paths
    for count in concurrency:
        if isinstance(count, bool) or not isinstance(count, int) or count <= 0:
            continue
        key = str(count)
        for name in (
            "aggregate_end_to_end_tokens_per_second",
            "per_stream_decode_tokens_per_second",
        ):
            paths.append(
                (f"{workload} C{key}/{name}", ("concurrency", key, name, "median"))
            )
    if workload == "code":
        depths = settings.get("prefill_depths")
        if isinstance(depths, list):
            for depth in depths:
                if isinstance(depth, bool) or not isinstance(depth, int) or depth <= 0:
                    continue
                for replay in ("cold", "warm_replay"):
                    paths.append(
                        (
                            f"{workload} {replay} prefill/{depth}",
                            (
                                "prefill",
                                str(depth),
                                replay,
                                "effective_prefill_tokens_per_second",
                                "median",
                            ),
                        )
                    )
    return paths


def metric_rows(
    candidate: dict[str, Any], reference: dict[str, Any], workload: str
) -> tuple[list[tuple[str, float, float]], list[str]]:
    candidate_paths = required_paths(candidate, workload)
    reference_paths = required_paths(reference, workload)
    candidate_names = {name for name, _ in candidate_paths}
    reference_names = {name for name, _ in reference_paths}
    errors: list[str] = []
    for name in sorted(candidate_names - reference_names):
        errors.append(f"{workload}: metric shape differs for {name}")
    for name in sorted(reference_names - candidate_names):
        errors.append(f"{workload}: metric shape differs for {name}")

    rows: list[tuple[str, float, float]] = []
    reference_by_name = dict(reference_paths)
    for name, path in candidate_paths:
        if name not in reference_by_name:
            continue
        values: dict[str, Any] = {}
        for label, receipt in (("candidate", candidate), ("reference", reference)):
            try:
                value = nested(receipt, *(path if label == "candidate" else reference_by_name[name]))
            except KeyError:
                errors.append(f"{workload}/{label}: missing metric {name}")
                continue
            if not finite_positive(value):
                errors.append(f"{workload}/{label}: invalid metric {name}={value!r}")
            values[label] = value
        if "candidate" in values and "reference" in values and not errors_for_metric(errors, workload, name):
            rows.append((name, float(values["candidate"]), float(values["reference"])))
    return rows, errors


def errors_for_metric(errors: list[str], workload: str, name: str) -> bool:
    prefix = f"{workload}/"
    return any(error.startswith(prefix) and f"metric {name}" in error for error in errors)


def report_pair(
    candidate: dict[str, Any], reference: dict[str, Any], workload: str
) -> tuple[bool, list[str]]:
    candidate_gate, candidate_errors = gate(candidate, workload, "candidate")
    reference_gate, reference_errors = gate(reference, workload, "reference")
    candidate_pass = not candidate_errors and candidate_gate.split("/")[0] == candidate_gate.split("/")[1]
    reference_pass = not reference_errors and reference_gate.split("/")[0] == reference_gate.split("/")[1]
    print(
        f"{workload}: candidate gate {candidate_gate} ({'PASS' if candidate_pass else 'FAIL'}), "
        f"reference gate {reference_gate} ({'PASS' if reference_pass else 'FAIL'})"
    )
    rows, metric_errors = metric_rows(candidate, reference, workload)
    errors = candidate_errors + reference_errors + metric_errors
    for name, candidate_value, reference_value in rows:
        ratio = candidate_value / reference_value
        if not math.isfinite(ratio):
            errors.append(f"{workload}: non-finite ratio for {name}")
            continue
        if candidate_value > reference_value:
            winner = "candidate"
        elif candidate_value < reference_value:
            winner = "reference"
        else:
            winner = "tie"
        print(
            f"{name}: ratio={ratio:.3f} candidate={candidate_value:.3f} "
            f"reference={reference_value:.3f} winner={winner}"
        )
    return not errors, errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare candidate and reference RigMark receipts from one Spark"
    )
    parser.add_argument("candidate_code")
    parser.add_argument("reference_code")
    parser.add_argument("candidate_prose")
    parser.add_argument("reference_prose")
    args = parser.parse_args()

    pairs = (
        ("code", load(args.candidate_code), load(args.reference_code)),
        ("prose", load(args.candidate_prose), load(args.reference_prose)),
    )
    errors: list[str] = []
    for workload, candidate, reference in pairs:
        errors.extend(validate_pair(candidate, reference, workload))
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 2

    all_valid = True
    for workload, candidate, reference in pairs:
        valid, pair_errors = report_pair(candidate, reference, workload)
        all_valid = all_valid and valid
        errors.extend(pair_errors)
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    return 0 if all_valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
