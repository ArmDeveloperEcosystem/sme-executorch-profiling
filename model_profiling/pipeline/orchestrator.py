# Copyright 2025 Arm Limited (or its affiliates)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

import csv
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from .analysis import (
    convert_etdump_to_csv,
    extract_kernels_from_xnntrace,
    generate_kernel_view,
    run_operator_analysis,
    run_robust_latency_analysis,
)
from .config import ComparisonConfig, ExperimentConfig, PipelineConfig
from .util import ensure_path, find_python_executable


class PipelineOrchestrator:
    def __init__(self, config: PipelineConfig, runner, *, verbose: bool = False):
        self.config = config
        self.runner = runner
        self.verbose = verbose
        self.python = find_python_executable()
        self.results: List[Dict] = []

    def execute(self, only: Optional[Iterable[str]] = None, analysis_only: bool = False) -> None:
        ensure_path(self.output_root)
        only_set = set(only or [])
        for exp in self.config.experiments:
            if only_set and exp.name not in only_set:
                continue
            for threads in exp.threads:
                self._run_single(exp, threads, analysis_only=analysis_only)
        self._run_comparisons()
        self._generate_kernel_views()
        self._write_summary()

    @property
    def output_root(self) -> Path:
        return self.runner.resolve_output_dir(self.config.model, self.config.output_root)

    def _run_single(self, exp: ExperimentConfig, threads: int, *, analysis_only: bool) -> None:
        result = {
            "experiment": exp.name,
            "threads": threads,
            "mode": exp.mode,
            "status": "analysis-only" if analysis_only else "pending",
            "paths": {},
            "metrics": {},
            "runs": exp.runs,
            "warmup": exp.warmup,
        }
        if not analysis_only:
            artifact = self.runner.run_experiment(
                model=self.config.model,
                output_root=self.output_root,
                experiment=exp,
                threads=threads,
                python=self.python,
                verbose=self.verbose,
            )
            result["status"] = "ok"
        else:
            artifact = self.runner.derive_artifact_paths(
                model=self.config.model,
                output_root=self.output_root,
                experiment=exp,
                threads=threads,
            )
        result["paths"] = {k: str(v) for k, v in artifact.items()}
        if exp.mode == "timing":
            self._post_process(exp.name, threads, artifact, result)
        elif exp.mode == "xnntrace":
            self._post_process_xnntrace(exp.name, threads, artifact, result)
        self.results.append(result)

    def _post_process(self, exp_name: str, threads: int, artifact: Dict[str, Path], result: Dict) -> None:
        etdump = artifact.get("etdump")
        if not etdump or not etdump.exists():
            return
        out_dir = etdump.parent
        timeline = convert_etdump_to_csv(etdump, out_dir, self.python)
        if timeline:
            result["paths"]["timeline_all"] = str(timeline)
            primary_name = f"{exp_name}_t{threads}"
            stats = run_robust_latency_analysis(timeline, out_dir, primary_name, self.python)
            if stats:
                result["metrics"]["median_ms"] = stats.get("median_ms")
                result["metrics"]["mean_ms"] = stats.get("mean_ms")
                result["metrics"]["cv_percent"] = stats.get("cv_percent")
                result["metrics"]["robust_stats_path"] = str(out_dir / f"{timeline.stem}_robust_stats.json")
            run0 = out_dir / f"{etdump.stem}_run0_timeline.csv"
            if run0.exists():
                result["paths"]["timeline_run0"] = str(run0)
                run_operator_analysis(run0, out_dir, self.python)

    def _post_process_xnntrace(
        self, exp_name: str, threads: int, artifact: Dict[str, Path], result: Dict
    ) -> None:
        """Extract kernels from xnntrace log."""
        xnntrace_log = artifact.get("xnntrace_log")
        if not xnntrace_log or not xnntrace_log.exists():
            return
        out_dir = xnntrace_log.parent
        model_id = f"{self.config.model.stem}_{exp_name}_t{threads}"
        kernel_csv = extract_kernels_from_xnntrace(xnntrace_log, out_dir, model_id, self.python)
        if kernel_csv:
            result["paths"]["kernel_csv"] = str(kernel_csv)

    def _run_comparisons(self) -> None:
        for comp in self.config.comparisons:
            baseline = self._find_result(comp.baseline_experiment, comp.baseline_threads)
            candidate = self._find_result(comp.candidate_experiment, comp.candidate_threads)
            if not baseline or not candidate:
                continue
            base_path = baseline["paths"].get("timeline_all")
            cand_path = candidate["paths"].get("timeline_all")
            if not base_path or not cand_path:
                if self.verbose:
                    print(
                        f"Skipping comparison '{comp.baseline_experiment}' vs "
                        f"'{comp.candidate_experiment}': missing timeline paths."
                    )
                continue
            base_timeline = Path(base_path)
            cand_timeline = Path(cand_path)
            if not base_timeline.exists() or not cand_timeline.exists():
                if self.verbose:
                    print(
                        f"Skipping comparison '{comp.baseline_experiment}' vs "
                        f"'{comp.candidate_experiment}': timeline files not found."
                    )
                continue
            cmd = [
                str(self.python),
                "model_profiling/tools/robust_latency_analysis.py",
                "--timeline-csv",
                str(base_timeline),
                "--compare",
                str(cand_timeline),
                "--name1",
                comp.baseline_experiment,
                "--name2",
                comp.candidate_experiment,
                "--output-dir",
                str(self.output_root),
            ]
            try:
                self.runner.run_command(cmd)
            except Exception:
                continue

    def _find_result(self, experiment: str, threads: int) -> Optional[Dict]:
        for res in self.results:
            if res["experiment"] == experiment and res["threads"] == threads:
                return res
        return None

    def _write_summary(self) -> None:
        generated_at = datetime.now(timezone.utc).isoformat()
        manifest_results = [self._manifest_result(row) for row in self.results]
        metrics_results = [self._metrics_result(row) for row in self.results]
        executorch_info = self._executorch_info()
        summary = {
            "schema_version": 1,
            "model": str(self.config.model),
            "generated_at": generated_at,
            "output_root": str(self.output_root),
            "config": str(self.config.config_path) if self.config.config_path else None,
            "executorch": executorch_info,
            "runs": self.results,
        }
        json_path = self.output_root / f"{self.config.model.stem}_pipeline_summary.json"
        json_path.write_text(json.dumps(summary, indent=2))

        manifest = {
            "schema_version": 1,
            "generated_at": generated_at,
            "config": str(self.config.config_path) if self.config.config_path else None,
            "model": str(self.config.model),
            "output_root": str(self.output_root),
            "executorch": executorch_info,
            "results": manifest_results,
        }
        (self.output_root / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        (self.output_root / "metrics.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "generated_at": generated_at,
                    "model": str(self.config.model),
                    "results": metrics_results,
                },
                indent=2,
            )
            + "\n"
        )

        lines = [
            f"# Pipeline Summary – {self.config.model.stem}",
            "",
            f"- Generated: {summary['generated_at']}",
            f"- Output root: `{self.output_root}`",
            "",
        ]
        timing = [r for r in self.results if r["mode"] == "timing"]
        if timing:
            lines.append("## Timing Results")
            lines.append("| Experiment | Threads | Runs | Warmup | Median (ms) | Mean (ms) | CV (%) | Robust Stats |")
            lines.append("|-----------|---------|------|--------|-------------|-----------|--------|---------------|")
            for row in timing:
                metrics = row.get("metrics", {})
                lines.append(
                    "| {exp} | {thr} | {runs} | {warmup} | {median:.2f} | {mean:.2f} | {cv:.2f} | `{stats}` |".format(
                        exp=row["experiment"],
                        thr=row["threads"],
                        runs=row["runs"],
                        warmup=row["warmup"],
                        median=metrics.get("median_ms", float("nan")),
                        mean=metrics.get("mean_ms", float("nan")),
                        cv=metrics.get("cv_percent", float("nan")),
                        stats=metrics.get("robust_stats_path", "n/a"),
                    )
                )
            lines.append("")
        trace = [r for r in self.results if r["mode"] == "xnntrace"]
        if trace:
            lines.append("## XNNTrace Results")
            lines.append("| Experiment | Threads | Log Path |")
            lines.append("|-----------|---------|----------|")
            for row in trace:
                log_path = row["paths"].get("xnntrace_log", "n/a")
                lines.append(f"| {row['experiment']} | {row['threads']} | `{log_path}` |")
            lines.append("")
        md_path = self.output_root / f"{self.config.model.stem}_pipeline_summary.md"
        md_path.write_text("\n".join(lines))

    def _manifest_result(self, row: Dict) -> Dict:
        return {
            "experiment": row.get("experiment"),
            "mode": row.get("mode"),
            "status": row.get("status"),
            "threads": row.get("threads"),
            "runs": row.get("runs"),
            "warmup": row.get("warmup"),
            "artifacts": self._artifact_paths(row),
        }

    def _metrics_result(self, row: Dict) -> Dict:
        return {
            "experiment": row.get("experiment"),
            "mode": row.get("mode"),
            "threads": row.get("threads"),
            "runs": row.get("runs"),
            "warmup": row.get("warmup"),
            "metrics": self._metric_values(row),
            "artifact_refs": self._artifact_paths(row),
        }

    def _metric_values(self, row: Dict) -> Dict:
        metrics = {
            "runs": row.get("runs"),
            "threads": row.get("threads"),
        }
        row_metrics = row.get("metrics", {})
        robust_stats_path = row_metrics.get("robust_stats_path")
        if robust_stats_path:
            path = Path(robust_stats_path)
            if path.exists():
                try:
                    robust = json.loads(path.read_text())
                    metrics["latency_ms"] = robust.get("latencies_ms", [])
                    for key in ("median_ms", "mean_ms", "min_ms", "max_ms", "cv_percent"):
                        if key in robust:
                            metrics[key] = robust[key]
                except Exception:
                    pass
        for key in ("median_ms", "mean_ms", "cv_percent"):
            if key in row_metrics:
                metrics.setdefault(key, row_metrics[key])

        kernel_csv = row.get("paths", {}).get("kernel_csv")
        if kernel_csv:
            path = Path(kernel_csv)
            if path.exists():
                try:
                    with path.open(newline="", encoding="utf-8") as f:
                        rows = list(csv.DictReader(f))
                    metrics["kernel_rows"] = len(rows)
                    metrics["sme_kernel_rows"] = sum(1 for item in rows if item.get("has_sme") == "1")
                    metrics["sme2_kernel_rows"] = sum(1 for item in rows if item.get("has_sme2") == "1")
                    metrics["sme2_kernel_calls"] = sum(
                        int(item.get("count") or 0) for item in rows if item.get("has_sme2") == "1"
                    )
                except Exception:
                    pass
        return metrics

    def _artifact_paths(self, row: Dict) -> Dict:
        artifacts = {}
        paths = row.get("paths", {})
        path_keys = {
            "etdump": "etdump",
            "latency_log": "log",
            "timeline_all": "timeline_all",
            "timeline_run0": "timeline_run0",
            "xnntrace_log": "xnntrace_log",
            "kernel_csv": "kernel_csv",
        }
        for source_key, output_key in path_keys.items():
            value = paths.get(source_key)
            if not value:
                continue
            path = Path(value)
            if not path.exists():
                continue
            artifacts[output_key] = self._artifact_ref(path)

        robust_stats_path = row.get("metrics", {}).get("robust_stats_path")
        if robust_stats_path:
            path = Path(robust_stats_path)
            if path.exists():
                artifacts["robust_stats"] = self._artifact_ref(path)
        return artifacts

    def _artifact_ref(self, path: Path) -> Dict:
        ref = {
            "path": str(path),
            "exists": path.exists(),
        }
        try:
            ref["relative_path"] = str(path.resolve().relative_to(self.output_root.resolve()))
        except ValueError:
            ref["relative_path"] = str(path)
        return ref

    def _expected_executorch_sha(self) -> Optional[str]:
        pin_file = Path.cwd() / "model_profiling" / "assets" / "executorch_commit.txt"
        if not pin_file.exists():
            return None
        value = pin_file.read_text(encoding="utf-8").strip()
        return value or None

    def _executorch_info(self) -> Dict:
        executorch_dir = Path(os.environ.get("EXECUTORCH_DIR", Path.cwd() / "executorch")).expanduser()
        expected_sha = self._expected_executorch_sha()
        info = {
            "present": executorch_dir.exists(),
            "expected_sha": expected_sha,
            "actual_sha": None,
            "compatible": None,
            "dirty": None,
            "patches_required": False,
        }
        if not executorch_dir.exists():
            return info
        try:
            info["actual_sha"] = subprocess.check_output(
                ["git", "-C", str(executorch_dir), "rev-parse", "HEAD"],
                text=True,
                stderr=subprocess.DEVNULL,
            ).strip()
            info["compatible"] = expected_sha is None or info["actual_sha"] == expected_sha
        except Exception:
            pass
        dirty = False
        for cmd in (
            ["git", "-C", str(executorch_dir), "diff", "--quiet"],
            ["git", "-C", str(executorch_dir), "diff", "--cached", "--quiet"],
        ):
            try:
                subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except subprocess.CalledProcessError:
                dirty = True
            except Exception:
                info["dirty"] = None
                return info
        info["dirty"] = dirty
        return info

    def _generate_kernel_views(self) -> None:
        """Generate kernel view tables comparing SME2-On vs SME2-Off."""
        # Find SME2-On and SME2-Off xnntrace experiments
        sme2_on_trace = None
        sme2_off_trace = None

        for result in self.results:
            if result["mode"] != "xnntrace":
                continue
            exp_name = result["experiment"]
            kernel_csv = result["paths"].get("kernel_csv")
            if not kernel_csv:
                continue
            if "sme2_off" in exp_name.lower() or "sme2-off" in exp_name.lower():
                sme2_off_trace = Path(kernel_csv)
            elif "sme2" in exp_name.lower() or "f16igemm" in exp_name.lower():
                # Assume this is SME2-On if it's not explicitly SME2-Off
                if sme2_on_trace is None:
                    sme2_on_trace = Path(kernel_csv)

        if sme2_on_trace and sme2_off_trace:
            kernel_view_path = self.output_root / "kernel_view_gemm.md"
            generate_kernel_view(
                sme2_on_trace,
                sme2_off_trace,
                kernel_view_path,
                f"{self.config.model.stem}: GEMM/IGEMM Kernel view (XNNPACK Delegated):",
                filter_op="gemm",
                python=self.python,
            )
