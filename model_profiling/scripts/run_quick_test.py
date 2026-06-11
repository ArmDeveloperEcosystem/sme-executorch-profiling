#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]  # executorch_sme2_kit/model_profiling/scripts/ -> executorch_sme2_kit/


def run(cmd: list[str]) -> None:
    print("+", " ".join(cmd))
    subprocess.check_call(cmd)


def main() -> None:
    ap = argparse.ArgumentParser(description="Quick smoke test for the SME2 profiling kit.")
    ap.add_argument("--platform", choices=["mac"], default="mac")
    args = ap.parse_args()

    # 1) Validate setup before runner builds
    run(["python", "model_profiling/scripts/validate_setup.py", "--skip-runners"])

    # 2) Build runners (shell orchestration)
    run(["bash", "model_profiling/scripts/build_runners.sh"])
    run(["python", "model_profiling/scripts/validate_setup.py", "--require-xnntrace-runners"])

    # 3) Export a tiny model
    model_name = "toy_cnn"
    artifacts_dir = ROOT / "model_profiling" / f"out_{model_name}" / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    run(["python", "model_profiling/export/export_model.py", "--model", model_name, "--dtype", "fp16", "--outdir", str(artifacts_dir)])

    # 4) Run timing pipeline
    timing_cfg = ROOT / "model_profiling" / "configs" / "toy_cnn_run.json"
    run(["python", "model_profiling/scripts/mac_pipeline.py", "--config", str(timing_cfg)])

    # 5) Validate timing results
    timing_results = ROOT / "model_profiling" / f"out_{model_name}" / "runs" / args.platform
    run(["python", "model_profiling/scripts/validate_results.py", "--results", str(timing_results)])

    # 6) Run trace pipeline and validate SME2 kernel evidence
    trace_cfg = ROOT / "model_profiling" / "configs" / "toy_cnn_trace_run.json"
    trace_results = ROOT / "model_profiling" / f"out_{model_name}" / "runs" / f"{args.platform}_trace"
    run(["python", "model_profiling/scripts/mac_pipeline.py", "--config", str(trace_cfg)])
    run(
        [
            "python",
            "model_profiling/scripts/validate_results.py",
            "--results",
            str(trace_results),
            "--require-sme2-kernels",
        ]
    )

    print("\n✅ Quick test completed.")


if __name__ == "__main__":
    main()

