#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

from model_profiling.pipeline.config import PipelineConfig
from model_profiling.pipeline.orchestrator import PipelineOrchestrator


ROOT = Path(__file__).resolve().parents[1]


class FakeRunner:
    def resolve_output_dir(self, model: Path, output_root: Path | None) -> Path:
        if output_root is None:
            raise AssertionError("test requires output_root")
        return output_root


def test_pipeline_summary_writes_validator_inputs() -> None:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        run_dir = tmp / "runs" / "mac"
        run_dir.mkdir(parents=True)
        model = tmp / "artifacts" / "toy.pte"
        model.parent.mkdir()
        model.write_bytes(b"pte")

        etdump = run_dir / "toy_mac_sme2_on_t1.etdump"
        etdump.write_text("dummy", encoding="utf-8")
        log = run_dir / "toy_mac_sme2_on_t1_latency.log"
        log.write_text("latency", encoding="utf-8")
        timeline = run_dir / "toy_mac_sme2_on_t1_exec_all_runs_timeline.csv"
        timeline.write_text("run_index,name,duration_ms\n0,Method::execute,1.0\n", encoding="utf-8")
        robust = run_dir / "toy_mac_sme2_on_t1_exec_all_runs_timeline_robust_stats.json"
        robust.write_text(
            json.dumps(
                {
                    "latencies_ms": [1.0, 1.2, 1.1],
                    "median_ms": 1.1,
                    "mean_ms": 1.1,
                    "min_ms": 1.0,
                    "max_ms": 1.2,
                    "cv_percent": 8.0,
                }
            )
            + "\n",
            encoding="utf-8",
        )

        config = PipelineConfig(
            model=model,
            output_root=run_dir,
            experiments=[],
            config_path=tmp / "config.json",
        )
        orchestrator = PipelineOrchestrator(config, FakeRunner())
        orchestrator.results = [
            {
                "experiment": "mac_sme2_on",
                "threads": 1,
                "mode": "timing",
                "status": "ok",
                "runs": 3,
                "warmup": 1,
                "paths": {
                    "etdump": str(etdump),
                    "latency_log": str(log),
                    "timeline_all": str(timeline),
                },
                "metrics": {
                    "robust_stats_path": str(robust),
                },
            }
        ]

        orchestrator._write_summary()

        assert (run_dir / "manifest.json").exists()
        assert (run_dir / "metrics.json").exists()
        manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
        metrics = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))
        assert manifest["model"] == str(model)
        assert manifest["results"][0]["artifacts"]["etdump"]["relative_path"] == etdump.name
        assert manifest["results"][0]["artifacts"]["robust_stats"]["relative_path"] == robust.name
        assert metrics["results"][0]["metrics"]["median_ms"] == 1.1
        assert metrics["results"][0]["metrics"]["latency_ms"] == [1.0, 1.2, 1.1]
        assert metrics["results"][0]["artifact_refs"]["etdump"]["relative_path"] == etdump.name

        p = subprocess.run(
            [
                "python",
                "model_profiling/scripts/validate_results.py",
                "--results",
                str(run_dir),
                "--allow-executorch-mismatch",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        assert p.returncode == 0, p.stdout + "\n" + p.stderr
