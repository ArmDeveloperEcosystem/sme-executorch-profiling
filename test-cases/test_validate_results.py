#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=str(ROOT), text=True, capture_output=True)


def artifact(path: str) -> dict[str, object]:
    return {"path": path, "relative_path": path, "exists": True}


def test_validate_results_passes_on_minimal_layout() -> None:
    with tempfile.TemporaryDirectory() as td:
        run_dir = Path(td) / "runs" / "mac"
        run_dir.mkdir(parents=True, exist_ok=True)

        exp_dir = run_dir / "mac_sme2_on"
        exp_dir.mkdir(parents=True, exist_ok=True)
        (exp_dir / "x.etdump").write_text("dummy", encoding="utf-8")
        (exp_dir / "x_exec_all_runs_timeline.csv").write_text(
            "run_index,name,duration_ms\n0,Method::execute,1.0\n", encoding="utf-8"
        )
        (exp_dir / "x_exec_all_runs_timeline_robust_stats.json").write_text(
            json.dumps({"latencies_ms": [1.0], "median_ms": 1.0}) + "\n", encoding="utf-8"
        )

        manifest = {
            "schema_version": 1,
            "model": "models/x.pte",
            "output_root": str(run_dir),
            "executorch": {"patches_required": False, "compatible": True},
            "results": [
                {
                    "experiment": "mac_sme2_on",
                    "mode": "timing",
                    "status": "ok",
                    "threads": 1,
                    "runs": 1,
                    "warmup": 0,
                    "artifacts": {
                        "etdump": artifact("mac_sme2_on/x.etdump"),
                        "timeline_all": artifact("mac_sme2_on/x_exec_all_runs_timeline.csv"),
                        "robust_stats": artifact("mac_sme2_on/x_exec_all_runs_timeline_robust_stats.json"),
                    },
                }
            ],
        }
        metrics = {
            "schema_version": 1,
            "model": "models/x.pte",
            "results": [
                {
                    "experiment": "mac_sme2_on",
                    "mode": "timing",
                    "threads": 1,
                    "runs": 1,
                    "warmup": 0,
                    "metrics": {"latency_ms": [1.0], "median_ms": 1.0},
                    "artifact_refs": {
                        "etdump": artifact("mac_sme2_on/x.etdump"),
                        "timeline_all": artifact("mac_sme2_on/x_exec_all_runs_timeline.csv"),
                        "robust_stats": artifact("mac_sme2_on/x_exec_all_runs_timeline_robust_stats.json"),
                    },
                }
            ],
        }
        (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        (run_dir / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")

        p = run(["python", "model_profiling/scripts/validate_results.py", "--results", str(run_dir)])
        assert p.returncode == 0, p.stdout + "\n" + p.stderr


def test_validate_results_requires_sme2_kernel_evidence() -> None:
    with tempfile.TemporaryDirectory() as td:
        run_dir = Path(td) / "runs" / "mac_trace"
        on_dir = run_dir / "mac_sme2_on_trace"
        off_dir = run_dir / "mac_sme2_off_trace"
        on_dir.mkdir(parents=True, exist_ok=True)
        off_dir.mkdir(parents=True, exist_ok=True)
        (on_dir / "trace.log").write_text("Using convolution microkernel 'xnn_f16_igemm_minmax_ukernel_1x8__aarch64_neonsme2'\n", encoding="utf-8")
        (off_dir / "trace.log").write_text("Using convolution microkernel 'xnn_f16_igemm_minmax_ukernel_1x8__aarch64_neonfp16arith'\n", encoding="utf-8")
        header = "model_id,kernel_name,category,count,dtype,xnn_op,variant,ukernel_shape,arch_chain,has_sme,has_sme2\n"
        (on_dir / "toy_mac_sme2_on_trace_t1_kernels.csv").write_text(
            header + "toy,xnn_f16_igemm_minmax_ukernel_1x8__aarch64_neonsme2,convolution,2,f16,igemm,minmax,1x8,aarch64_neonsme2,1,1\n",
            encoding="utf-8",
        )
        (off_dir / "toy_mac_sme2_off_trace_t1_kernels.csv").write_text(
            header + "toy,xnn_f16_igemm_minmax_ukernel_1x8__aarch64_neonfp16arith,convolution,2,f16,igemm,minmax,1x8,aarch64_neonfp16arith,0,0\n",
            encoding="utf-8",
        )
        manifest = {
            "schema_version": 1,
            "model": "models/x.pte",
            "output_root": str(run_dir),
            "executorch": {"patches_required": False, "compatible": True},
            "results": [
                {
                    "experiment": "mac_sme2_on_trace",
                    "mode": "xnntrace",
                    "status": "ok",
                    "threads": 1,
                    "runs": 1,
                    "warmup": 0,
                    "artifacts": {
                        "xnntrace_log": artifact("mac_sme2_on_trace/trace.log"),
                        "kernel_csv": artifact("mac_sme2_on_trace/toy_mac_sme2_on_trace_t1_kernels.csv"),
                    },
                },
                {
                    "experiment": "mac_sme2_off_trace",
                    "mode": "xnntrace",
                    "status": "ok",
                    "threads": 1,
                    "runs": 1,
                    "warmup": 0,
                    "artifacts": {
                        "xnntrace_log": artifact("mac_sme2_off_trace/trace.log"),
                        "kernel_csv": artifact("mac_sme2_off_trace/toy_mac_sme2_off_trace_t1_kernels.csv"),
                    },
                },
            ],
        }
        metrics = {
            "schema_version": 1,
            "model": "models/x.pte",
            "results": [
                {
                    "experiment": "mac_sme2_on_trace",
                    "mode": "xnntrace",
                    "threads": 1,
                    "runs": 1,
                    "warmup": 0,
                    "metrics": {"kernel_rows": 1, "sme2_kernel_rows": 1, "sme2_kernel_calls": 2},
                    "artifact_refs": {},
                },
                {
                    "experiment": "mac_sme2_off_trace",
                    "mode": "xnntrace",
                    "threads": 1,
                    "runs": 1,
                    "warmup": 0,
                    "metrics": {"kernel_rows": 1, "sme2_kernel_rows": 0, "sme2_kernel_calls": 0},
                    "artifact_refs": {},
                },
            ],
        }
        (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        (run_dir / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")

        p = run(
            [
                "python",
                "model_profiling/scripts/validate_results.py",
                "--results",
                str(run_dir),
                "--require-sme2-kernels",
            ]
        )
        assert p.returncode == 0, p.stdout + "\n" + p.stderr


if __name__ == "__main__":
    test_validate_results_passes_on_minimal_layout()
    test_validate_results_requires_sme2_kernel_evidence()
    print("OK")
