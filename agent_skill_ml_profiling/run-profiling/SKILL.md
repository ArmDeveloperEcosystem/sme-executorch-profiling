---
name: run-profiling
description: Run SME2-on versus SME2-off profiling experiments for an exported ExecuTorch .pte model on macOS or Android. Use when Codex needs to create or edit pipeline JSON configs, execute timing or XNNPACK trace runs, compare runner variants, collect ETDump artifacts, rerun analysis-only mode, or validate profiling output directories.
---

# Run Profiling

## Operating Rules

- Use timing mode for latency claims. Use `xnntrace` mode only to identify selected XNNPACK kernels because logging changes timing.
- Keep SME2-on and SME2-off experiments in the same config so artifacts share model, runs, warmup, threads, and output root.
- Use `model_profiling/out_<model>/runs/<platform>/` as the output root unless the user requests another layout.
- Use a separate trace output root such as `model_profiling/out_<model>/runs/<platform>_trace/` when collecting XNNPACK kernel evidence.
- Validate the `.pte` and runner paths before running long experiments.
- If runners were built in an external checkout, keep `EXECUTORCH_DIR=/path/to/executorch` exported so `executorch/cmake-out/...` config paths resolve correctly.
- If a runner crashes but ETDump exists, report the crash separately from timing analysis; do not claim model correctness from timing alone.

## Required Inputs

- Exported `.pte` path.
- Built runner paths for the target platform.
- Target platform: `mac` or `android`.
- Experiment count, warmup count, thread counts, and optional Android `cpu_affinity`.

## Procedure

1. Activate the environment:

   ```bash
   export EXECUTORCH_DIR=/path/to/executorch
   source .venv/bin/activate
   ```

2. Start from the closest template:

   ```bash
   cp model_profiling/configs/templates/mac_template.json model_profiling/configs/my_experiment.json
   # or
   cp model_profiling/configs/templates/android_template.json model_profiling/configs/my_android_experiment.json
   ```

3. Edit the config so `model`, `output_root`, `experiments[].runner_path`, `mode`, `runs`, `warmup`, and `threads` match the task. A minimal macOS pair is:

   ```json
   {
     "model": "model_profiling/out_toy_cnn/artifacts/toy_cnn_xnnpack_fp16.pte",
     "output_root": "model_profiling/out_toy_cnn/runs/mac",
     "experiments": [
       {
         "name": "mac_sme2_on",
         "runner_path": "executorch/cmake-out/mac-arm64/executor_runner",
         "mode": "timing",
         "runs": 10,
         "warmup": 1,
         "threads": [1]
       },
       {
         "name": "mac_sme2_off",
         "runner_path": "executorch/cmake-out/mac-arm64-sme2-off/executor_runner",
         "mode": "timing",
         "runs": 10,
         "warmup": 1,
         "threads": [1]
       }
     ],
     "analysis": { "compare_pairs": [] }
   }
   ```

4. Validate JSON before execution:

   ```bash
   python -m json.tool model_profiling/configs/my_experiment.json >/dev/null
   ```

5. Run the pipeline:

   ```bash
   python model_profiling/scripts/mac_pipeline.py \
     --config model_profiling/configs/my_experiment.json
   ```

   Run XNNPACK trace separately when kernel-selection evidence is required. The toy smoke config is:

   ```bash
   python model_profiling/scripts/mac_pipeline.py \
     --config model_profiling/configs/toy_cnn_trace_run.json
   ```

   For Android:

   ```bash
   python model_profiling/scripts/android_pipeline.py \
     --config model_profiling/configs/my_android_experiment.json
   ```

   For a remote Android device:

   ```bash
   python model_profiling/scripts/android_pipeline.py \
     --config model_profiling/configs/my_android_experiment.json \
     --remote-device 192.168.1.100:5555
   ```

6. Re-run analysis without re-executing the model when needed:

   ```bash
   python model_profiling/scripts/mac_pipeline.py \
     --config model_profiling/configs/my_experiment.json \
     --analysis-only
   ```

7. Validate the run directory:

   ```bash
   python model_profiling/scripts/validate_results.py \
     --results model_profiling/out_toy_cnn/runs/mac
   ```

   Validate XNNPACK trace evidence:

   ```bash
   python model_profiling/scripts/validate_results.py \
     --results model_profiling/out_toy_cnn/runs/mac_trace \
     --require-sme2-kernels
   ```

## Success Criteria

- `manifest.json` and `metrics.json` exist under the run directory. `manifest.json` is the provenance/artifact index; `metrics.json` is measurement data with artifact references.
- Each timing experiment produced `.etdump`, latency log, and generated CSV files.
- `validate_results.py` exits 0 for timing outputs.
- When trace validation is requested, kernel CSVs exist and `validate_results.py --require-sme2-kernels` confirms SME2-on selected at least one SME2 kernel while SME2-off did not.
- Analysis outputs include `analysis_summary.json` when ETDump conversion succeeded.

## Failure Triage

- Missing runner: use `build-runners`.
- Missing `.pte`: use `export-model`.
- Android device unavailable: run `adb devices`, authorize the device, or use `--remote-device`.
- No CSV files after ETDump: rerun `analyze-results` and capture the converter error.
- Trace logs requested for latency: split into separate timing and `xnntrace` experiments before drawing conclusions.

## Handoff

After profiling succeeds, use `analyze-results` for deeper operator/kernel views or `generate-report` for a shareable Markdown report.
