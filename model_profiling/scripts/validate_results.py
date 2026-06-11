#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def check(cond: bool, ok: str, fail: str) -> bool:
    if cond:
        print(f"✅ {ok}")
        return True
    print(f"❌ {fail}")
    return False


def check_or_warn(cond: bool, allowed: bool, ok: str, fail: str, warning: str) -> bool:
    if cond:
        print(f"✅ {ok}")
        return True
    if allowed:
        print(f"⚠️  {warning}")
        return True
    print(f"❌ {fail}")
    return False


def load_json(path: Path) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except Exception as exc:
        return None, str(exc)


def resolve_artifact_path(run_dir: Path, artifact: Dict[str, Any]) -> Optional[Path]:
    raw_path = artifact.get("path")
    if raw_path:
        path = Path(raw_path)
        if path.is_absolute() and path.exists():
            return path
        if not path.is_absolute():
            candidate = run_dir / path
            if candidate.exists():
                return candidate

    relative_path = artifact.get("relative_path")
    if relative_path:
        candidate = run_dir / relative_path
        if candidate.exists():
            return candidate
    return None


def validate_artifact(
    run_dir: Path, artifacts: Dict[str, Any], key: str, label: str
) -> Tuple[bool, Optional[Path]]:
    artifact = artifacts.get(key)
    if not isinstance(artifact, dict):
        return check(False, f"{label} artifact recorded", f"{label} artifact missing from manifest"), None
    resolved = resolve_artifact_path(run_dir, artifact)
    return check(resolved is not None, f"{label} artifact exists", f"{label} artifact path does not resolve"), resolved


def validate_manifest(run_dir: Path, data: Dict[str, Any], *, allow_executorch_mismatch: bool) -> bool:
    ok = True
    ok &= check("model" in data, "manifest contains model", "manifest missing model field")
    ok &= check("output_root" in data, "manifest contains output_root", "manifest missing output_root field")
    ok &= check("executorch" in data, "manifest contains executorch provenance", "manifest missing executorch provenance")

    executorch = data.get("executorch", {})
    if isinstance(executorch, dict):
        if executorch.get("compatible") is False:
            ok &= check_or_warn(
                False,
                allow_executorch_mismatch,
                "ExecuTorch SHA is compatible",
                "ExecuTorch SHA is incompatible with the checked-in pin",
                "ExecuTorch SHA is incompatible with the checked-in pin; continuing because --allow-executorch-mismatch was set",
            )
        if executorch.get("patches_required") is not None:
            ok &= check(
                executorch.get("patches_required") is False,
                "manifest records no required ExecuTorch/XNNPACK patches",
                "manifest says ExecuTorch/XNNPACK patches are required",
            )

    results = data.get("results")
    ok &= check(isinstance(results, list) and bool(results), "manifest contains result entries", "manifest results[] missing or empty")
    if not isinstance(results, list):
        return ok

    for result in results:
        if not isinstance(result, dict):
            ok &= check(False, "manifest result is an object", "manifest result entry is not an object")
            continue
        experiment = result.get("experiment", "<unknown>")
        mode = result.get("mode")
        artifacts = result.get("artifacts")
        ok &= check(isinstance(artifacts, dict) and bool(artifacts), f"{experiment} records artifacts", f"{experiment} has no artifact map")
        if not isinstance(artifacts, dict):
            continue

        if mode == "timing":
            ok &= validate_artifact(run_dir, artifacts, "etdump", f"{experiment} ETDump")[0]
            ok &= validate_artifact(run_dir, artifacts, "timeline_all", f"{experiment} all-runs timeline")[0]
            ok &= validate_artifact(run_dir, artifacts, "robust_stats", f"{experiment} robust stats")[0]
        elif mode == "xnntrace":
            ok &= validate_artifact(run_dir, artifacts, "xnntrace_log", f"{experiment} XNNPACK trace log")[0]
            ok &= validate_artifact(run_dir, artifacts, "kernel_csv", f"{experiment} kernel CSV")[0]
    return ok


def validate_metrics(data: Dict[str, Any]) -> bool:
    ok = True
    results = data.get("results")
    ok &= check(isinstance(results, list) and bool(results), "metrics contains result entries", "metrics results[] missing or empty")
    if not isinstance(results, list):
        return ok

    for result in results:
        if not isinstance(result, dict):
            ok &= check(False, "metrics result is an object", "metrics result entry is not an object")
            continue
        experiment = result.get("experiment", "<unknown>")
        mode = result.get("mode")
        metrics = result.get("metrics")
        ok &= check(isinstance(metrics, dict), f"{experiment} metrics object exists", f"{experiment} metrics missing")
        if not isinstance(metrics, dict):
            continue

        if mode == "timing":
            latencies = metrics.get("latency_ms")
            ok &= check(isinstance(latencies, list) and bool(latencies), f"{experiment} latency samples recorded", f"{experiment} latency_ms missing or empty")
            ok &= check(isinstance(metrics.get("median_ms"), (int, float)), f"{experiment} median latency recorded", f"{experiment} median_ms missing")
        elif mode == "xnntrace":
            ok &= check(isinstance(metrics.get("kernel_rows"), int), f"{experiment} kernel row count recorded", f"{experiment} kernel_rows missing")
    return ok


def load_kernel_rows(path: Path) -> List[Dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def validate_sme2_kernels(run_dir: Path) -> bool:
    ok = True
    kernel_csvs = list(run_dir.glob("**/*_kernels.csv"))
    ok &= check(bool(kernel_csvs), f"found {len(kernel_csvs)} kernel CSV file(s)", "no XNNPACK kernel CSV files found")
    if not kernel_csvs:
        return ok

    sme2_on_hits = 0
    sme2_off_hits = 0
    for path in kernel_csvs:
        rows = load_kernel_rows(path)
        has_sme2 = sum(1 for row in rows if row.get("has_sme2") == "1")
        name = str(path).lower()
        if "sme2_off" in name or "sme2-off" in name:
            sme2_off_hits += has_sme2
        elif "sme2_on" in name or "sme2-on" in name or "sme2" in name:
            sme2_on_hits += has_sme2

    ok &= check(sme2_on_hits > 0, f"SME2-on trace records {sme2_on_hits} SME2 kernel row(s)", "SME2-on trace did not record any SME2 kernels")
    ok &= check(sme2_off_hits == 0, "SME2-off trace records no SME2 kernels", f"SME2-off trace recorded {sme2_off_hits} SME2 kernel row(s)")
    return ok


def manifest_requires_etdump(data: Optional[Dict[str, Any]]) -> bool:
    if not data:
        return True
    results = data.get("results")
    if not isinstance(results, list) or not results:
        return True
    return any(isinstance(result, dict) and result.get("mode") == "timing" for result in results)


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate outputs of a profiling run directory.")
    ap.add_argument("--results", type=Path, required=True, help="Run directory (e.g., out_<model>/runs/mac)")
    ap.add_argument(
        "--require-sme2-kernels",
        action="store_true",
        help="Require XNNPACK kernel CSV evidence that SME2-on selected at least one SME2 kernel and SME2-off did not.",
    )
    ap.add_argument(
        "--allow-executorch-mismatch",
        action="store_true",
        help="Warn instead of failing when manifest ExecuTorch provenance does not match the checked-in pin.",
    )
    args = ap.parse_args()

    run_dir = args.results.resolve()
    ok = True

    ok &= check(run_dir.exists(), f"run dir exists: {run_dir}", f"missing run dir: {run_dir}")

    manifest = run_dir / "manifest.json"
    metrics = run_dir / "metrics.json"
    ok &= check(manifest.exists(), "manifest.json exists", "manifest.json missing")
    ok &= check(metrics.exists(), "metrics.json exists", "metrics.json missing")

    manifest_data = None

    if manifest.exists():
        manifest_data, error = load_json(manifest)
        ok &= check(manifest_data is not None, "manifest JSON parses", f"manifest JSON parse error: {error}")

    if manifest_requires_etdump(manifest_data):
        etdumps = list(run_dir.glob("**/*.etdump"))
        ok &= check(bool(etdumps), f"found {len(etdumps)} .etdump file(s)", "no .etdump found")
    else:
        print("⚠️  Skipping ETDump check for trace-only run")

    if manifest_data is not None:
        ok &= validate_manifest(run_dir, manifest_data, allow_executorch_mismatch=args.allow_executorch_mismatch)

    if metrics.exists():
        data, error = load_json(metrics)
        ok &= check(data is not None, "metrics JSON parses", f"metrics JSON parse error: {error}")
        if data is not None:
            ok &= validate_metrics(data)

    if args.require_sme2_kernels:
        ok &= validate_sme2_kernels(run_dir)

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
