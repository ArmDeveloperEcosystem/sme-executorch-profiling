---
name: analyze-results
description: Analyze existing SME2 ExecuTorch profiling outputs. Use when Codex needs to regenerate ETDump CSV files, compute robust latency statistics, compare SME2-on versus SME2-off timeline CSVs, identify operator-category bottlenecks, inspect portable versus delegated behavior, or derive XNNPACK kernel evidence from xnntrace logs.
---

# Analyze Results

## Operating Rules

- Analyze existing artifacts; do not rerun model execution unless the requested artifact is missing and the user agrees to rerun profiling.
- Prefer `*_all_runs_timeline.csv` for latency and category analysis. Use `*_run0_timeline.csv` only as a fallback or for quick inspection.
- Separate latency evidence from kernel-selection evidence. `xnntrace` logs show kernel choices but are not timing evidence.
- State whether findings are based on ETDump timeline CSV, ops stats CSV, metrics JSON, or xnntrace logs.

## Required Inputs

- A run directory such as `model_profiling/out_<model>/runs/mac`.
- Optional pair of timeline CSVs for SME2-on and SME2-off comparison.
- Optional xnntrace logs or `*_kernels.csv` files for kernel-level evidence.

## Procedure

1. Activate the environment:

   ```bash
   source .venv/bin/activate
   ```

2. Regenerate ETDump-derived CSV files and `analysis_summary.json`:

   ```bash
   python model_profiling/scripts/analyze_results.py \
     --run-dir model_profiling/out_<model>/runs/<platform>
   ```

3. Validate required analysis artifacts:

   ```bash
   find model_profiling/out_<model>/runs/<platform> -name '*_all_runs_timeline.csv' -print
   find model_profiling/out_<model>/runs/<platform> -name '*_ops_stats.csv' -print
   test -s model_profiling/out_<model>/runs/<platform>/analysis_summary.json
   ```

4. Run robust latency analysis on one timeline:

   ```bash
   RUN_DIR="model_profiling/out_<model>/runs/<platform>"
   ON_CSV="$(find "${RUN_DIR}" -name '*sme2_on*_all_runs_timeline.csv' -print | head -1)"

   python model_profiling/tools/robust_latency_analysis.py \
     --timeline-csv "${ON_CSV}" \
     --output-dir "${RUN_DIR}" \
     --name "SME2-On" \
     --verbose
   ```

5. Compare SME2-on and SME2-off timelines:

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

6. Convert xnntrace logs to kernel CSVs when trace runs exist. Use the trace run directory, not the timing run directory, when profiling kept them separate:

   ```bash
   RUN_DIR="model_profiling/out_<model>/runs/<platform>_trace"
   ON_TRACE="$(find "${RUN_DIR}" -name '*sme2_on*_xnntrace.log' -print | head -1)"
   OFF_TRACE="$(find "${RUN_DIR}" -name '*sme2_off*_xnntrace.log' -print | head -1)"

   python model_profiling/tools/xnntrace_to_kernels.py \
     --xnntrace "${ON_TRACE}" \
     --out "${RUN_DIR}/sme2_on_kernels.csv"

   python model_profiling/tools/xnntrace_to_kernels.py \
     --xnntrace "${OFF_TRACE}" \
     --out "${RUN_DIR}/sme2_off_kernels.csv"

   python model_profiling/tools/generate_kernel_view.py \
     --sme2-on "${RUN_DIR}/sme2_on_kernels.csv" \
     --sme2-off "${RUN_DIR}/sme2_off_kernels.csv" \
     --out "${RUN_DIR}/kernel_view.md"

   python model_profiling/scripts/validate_results.py \
     --results "${RUN_DIR}" \
     --require-sme2-kernels
   ```

## Success Criteria

- ETDump conversion emits `*_all_runs_timeline.csv` and `*_ops_stats.csv`.
- Latency analysis uses `Method::execute` rows when available.
- Comparisons name the baseline and candidate consistently.
- Kernel view shows whether selected kernels include SME2 or NEON/other fallback paths.

## Interpretation Guidance

- If GEMM or convolution shrinks but data movement grows as a percentage, describe a bottleneck shift rather than a failure of SME2 acceleration.
- If SME2-on is slower, check runner paths, platform support, thread count, warmup, thermal behavior, and whether the delegated ops actually used SME2 kernels.
- If `OTHER` dominates, inspect top operator names before recommending backend work.
- If xnntrace shows no SME2 kernels, verify device support, runner variant, model delegation, and XNNPACK/KleidiAI build state.

## Handoff

Use `generate-report` when the user needs a Markdown report or stakeholder-ready summary.
