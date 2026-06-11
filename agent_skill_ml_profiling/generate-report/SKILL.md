---
name: generate-report
description: Generate Markdown reports from SME2 ExecuTorch profiling outputs. Use when Codex needs a shareable performance report, macOS and Android combined report, latency and operator-category summary, SME2-on versus SME2-off speedup write-up, or report validation before publishing results.
---

# Generate Report

## Operating Rules

- Generate reports from existing CSV and metrics artifacts; do not rerun profiling unless required inputs are missing.
- Run `analyze-results` first if the run directory has `.etdump` files but no CSV files.
- Treat report text as evidence-backed: cite artifact paths for latency, category breakdown, and kernel claims.
- Separate timing conclusions from xnntrace kernel-selection conclusions.
- Interpret `manifest.json` as provenance and artifact references. Interpret `metrics.json` as measurements; do not treat artifact paths as metrics.

## Required Inputs

- A run directory such as `model_profiling/out_<model>/runs/mac`.
- Optional Android run directory for a combined report.
- Optional trace run directory such as `model_profiling/out_<model>/runs/mac_trace` for kernel-selection claims.
- Optional report title or model name.

## Procedure

1. Activate the environment:

   ```bash
   source .venv/bin/activate
   ```

2. Ensure CSV inputs exist:

   ```bash
   python model_profiling/scripts/analyze_results.py \
     --run-dir model_profiling/out_<model>/runs/<platform>
   ```

3. Generate a single-platform report:

   ```bash
   python model_profiling/scripts/generate_report.py \
     --run-dir model_profiling/out_<model>/runs/<platform> \
     --out model_profiling/out_<model>/runs/<platform>/report.md \
     --title "Profiling Report: <model>"
   ```

4. Generate a combined macOS and Android report when both run directories exist:

   ```bash
   python model_profiling/scripts/generate_combined_report.py \
     --mac-dir model_profiling/out_<model>/runs/mac \
     --android-dir model_profiling/out_<model>/runs/android \
     --out model_profiling/out_<model>/runs/combined_report.md \
     --model-name "<model>"
   ```

5. Add optional deeper evidence files before finalizing the report:

   ```bash
   RUN_DIR="model_profiling/out_<model>/runs/<platform>"
   ON_CSV="$(find "${RUN_DIR}" -name '*sme2_on*_all_runs_timeline.csv' -print | head -1)"
   OFF_CSV="$(find "${RUN_DIR}" -name '*sme2_off*_all_runs_timeline.csv' -print | head -1)"

   python model_profiling/tools/analyze_etdump_csv.py \
     --timeline-csv "${ON_CSV}" \
     --compare "${OFF_CSV}" \
     --name1 "SME2-On" \
     --name2 "SME2-Off" \
     --output-dir "${RUN_DIR}" \
     --verbose
   ```

   For kernel-selection claims, validate the separate trace run:

   ```bash
   python model_profiling/scripts/validate_results.py \
     --results model_profiling/out_<model>/runs/<platform>_trace \
     --require-sme2-kernels
   ```

6. Validate report completeness:

   ```bash
   test -s model_profiling/out_<model>/runs/<platform>/report.md
   grep -q "Latency" model_profiling/out_<model>/runs/<platform>/report.md
   grep -q "Operator" model_profiling/out_<model>/runs/<platform>/report.md
   ```

## Success Criteria

- `report.md` or `combined_report.md` exists and is non-empty.
- The report includes model/config metadata, latency statistics, SME2-on/off comparison when both experiments exist, category breakdown, and generated artifact references.
- Any kernel-level claims are backed by xnntrace-derived artifacts such as `kernel_view.md` or kernel CSVs.

## Review Checklist

- Confirm baseline direction: speedup should be `SME2-off median / SME2-on median`.
- Use median latency for headline claims unless the user asks for another statistic.
- Mention run count, warmup count, platform, runner paths, and model path when available.
- Flag missing optional `.etrecord` or xnntrace data instead of hiding it.
- Avoid claiming model correctness unless the workflow included correctness validation beyond runner completion.

## Handoff

Use the report path as the main deliverable and include the supporting run directory in the final response.
