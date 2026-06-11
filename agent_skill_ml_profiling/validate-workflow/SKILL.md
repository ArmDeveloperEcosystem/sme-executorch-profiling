---
name: validate-workflow
description: Run or audit the end-to-end SME2 ExecuTorch profiling smoke test. Use when Codex needs to prove a fresh workspace works, validate setup/build/export/pipeline wiring with toy_cnn, check generated artifacts before a PR or demo, or diagnose which workflow stage is broken.
---

# Validate Workflow

## Operating Rules

- Use the smoke test to validate wiring, not benchmark quality. The toy model is for functional confidence.
- Run from the repository root.
- For public validation, use a clean pinned ExecuTorch checkout with no ET/XNNPACK patches. If local-development exceptions are used, report them explicitly.
- Keep generated `out_toy_cnn/` artifacts unless the user asks for cleanup; they are useful evidence for later diagnosis.
- If the full smoke test is too expensive for the environment, run the staged validation and report the last completed gate.

## Procedure

1. For a full validation on macOS:

   ```bash
   export EXECUTORCH_DIR=/path/to/executorch
   bash model_profiling/scripts/setup_repo.sh
   bash model_profiling/scripts/build_runners.sh
   source .venv/bin/activate
   python model_profiling/scripts/validate_setup.py --require-xnntrace-runners
   python model_profiling/scripts/run_quick_test.py
   python model_profiling/scripts/mac_pipeline.py \
     --config model_profiling/configs/toy_cnn_trace_run.json
   python model_profiling/scripts/validate_results.py \
     --results model_profiling/out_toy_cnn/runs/mac_trace \
     --require-sme2-kernels
   ```

2. For staged validation after setup already exists:

   ```bash
   export EXECUTORCH_DIR=/path/to/executorch
   source .venv/bin/activate
   python model_profiling/scripts/validate_setup.py --skip-runners
   bash model_profiling/scripts/build_runners.sh
   python model_profiling/scripts/validate_setup.py --require-xnntrace-runners
   python model_profiling/export/export_model.py \
     --model toy_cnn \
     --dtype fp16 \
     --outdir model_profiling/out_toy_cnn/artifacts
   python model_profiling/scripts/mac_pipeline.py \
     --config model_profiling/configs/toy_cnn_run.json
   python model_profiling/scripts/validate_results.py \
     --results model_profiling/out_toy_cnn/runs/mac
   python model_profiling/scripts/mac_pipeline.py \
     --config model_profiling/configs/toy_cnn_trace_run.json
   python model_profiling/scripts/validate_results.py \
     --results model_profiling/out_toy_cnn/runs/mac_trace \
     --require-sme2-kernels
   ```

3. Re-run analysis only if execution completed but analysis outputs are missing:

   ```bash
   python model_profiling/scripts/analyze_results.py \
     --run-dir model_profiling/out_toy_cnn/runs/mac
   ```

## Success Criteria

- `model_profiling/out_toy_cnn/artifacts/toy_cnn_xnnpack_fp16.pte` exists and is non-empty.
- Timing runners `executorch/cmake-out/mac-arm64/executor_runner` and `executorch/cmake-out/mac-arm64-sme2-off/executor_runner` exist.
- Trace runners `executorch/cmake-out/mac-arm64-xnnlog/executor_runner` and `executorch/cmake-out/mac-arm64-sme2-off-xnnlog/executor_runner` exist.
- `model_profiling/out_toy_cnn/runs/mac/manifest.json` and `metrics.json` exist.
- At least one `.etdump`, one `*_all_runs_timeline.csv`, and `analysis_summary.json` exist under `model_profiling/out_toy_cnn/runs/mac`.
- `model_profiling/out_toy_cnn/runs/mac_trace/*_kernels.csv` exists.
- `validate_results.py` exits 0 for timing and `validate_results.py --require-sme2-kernels` exits 0 for trace.

## Failure Triage

- Setup failure: use `setup-workspace` and stop before build/export.
- Build failure: use `build-runners` and preserve CMake logs.
- Export failure: use `export-model` and inspect model registry/import errors.
- Pipeline failure: use `run-profiling`; validate config paths and runner paths.
- Analysis failure: use `analyze-results`; inspect ETDump conversion and `.etrecord` availability.

## Reporting Template

When validation completes, report:

```text
Validation result: pass|fail
Last completed stage: setup|build|export|pipeline|analysis|results-validation
Key artifacts:
- <path to .pte>
- <path to run dir>
- <path to trace run dir>
- <path to analysis_summary.json>
Notes:
- <warnings about local ExecuTorch patches, missing optional etrecord, trace logs, or platform limits>
```
