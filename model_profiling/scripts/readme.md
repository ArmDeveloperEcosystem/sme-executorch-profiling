# Profiling kit scripts (SME2 + ExecuTorch)

These scripts are a profiling kit that lives alongside the learning path.

## Expected directory layout

Run everything from the `executorch_sme2_kit/` directory:

```bash
cd executorch_sme2_kit/
```

The scripts will create (or reuse):
- `.venv/` Python virtual environment
- `executorch/` ExecuTorch checkout (defaults to the pinned public ref in `model_profiling/assets/executorch_commit.txt`)
- `executorch/cmake-out/` built `executor_runner` binaries (runners stay with their ExecuTorch version for traceability)
- `out_<model>/artifacts/` exported `.pte` and `.etrecord` files
- `model_profiling/configs/` JSON pipeline configs
- `out_<model>/runs/` results, logs, traces, and manifests

**Note**: Replace `<model>` with your actual model name (e.g., `out_mobilenet/`, `out_edgetam/`).

## Requirements

- Python 3.9+, Git, CMake, Ninja, and, on macOS, Xcode Command Line Tools.
- Network access to GitHub and Python package indexes for first-time setup.
- Arm macOS host for the local smoke workflow. SME2 kernel-selection proof on macOS requires SME2-capable Apple Silicon, such as Apple M4.
- Android runner build: set `ANDROID_NDK` or `ANDROID_NDK_HOME` to an Android NDK with `build/cmake/android.toolchain.cmake`. If neither variable is set, `build_runners.sh` exits successfully after building macOS runners and prints that Android was skipped.
- Android device run: install Android platform-tools so `adb` is available, and use an Armv9 Android device with SME2 support when you need to observe SME2 kernel deltas on device.

## Time budget (clean machine)

- Setup: ~20–30 min  
- Build: ~15–25 min  
- Export + pipeline + analyze: ~10 min  
- **Total first success: ~60–75 min**

## Fast smoke test (recommended for first-time users)

After setup + build, validate the end-to-end flow with a tiny model:

```bash
source .venv/bin/activate
python model_profiling/scripts/run_quick_test.py
```

This runs the full workflow (validate → build → export toy model → pipeline → validate results) in **~10–15 minutes** and confirms your setup works.

## ExecuTorch setup choices

Fresh setup, only when `EXECUTORCH_REPO_URL` points at a repository containing the checked-in pin:

```bash
bash model_profiling/scripts/setup_repo.sh
```

Reuse an existing ExecuTorch checkout:

```bash
export EXECUTORCH_DIR=/path/to/executorch
bash model_profiling/scripts/setup_repo.sh
```

By default, setup and validation expect the pinned public ExecuTorch commit in `model_profiling/assets/executorch_commit.txt` or a clean descendant checkout, no tracked local ExecuTorch/XNNPACK patches, and matching submodules. The setup script initializes submodules for an existing checkout. The public toy/demo workflow does not require ET or XNNPACK patches. If you intentionally use a local patched checkout, record that in your report and opt in with the relevant `SME2_EXECUTORCH_ALLOW_*` environment variable or `validate_setup.py --allow-*` option.

The editable ExecuTorch install disables optional MLX/CoreML/LLM/training CMake targets by default, and the runner presets keep unrelated LLM/training targets off. The profiling workflow builds dedicated XNNPACK runners later, so those optional backends are not required for setup or SME2 kernel-selection validation.

Pre-check an existing checkout before setup:

```bash
python model_profiling/scripts/validate_setup.py \
  --executorch-dir /path/to/executorch \
  --skip-venv \
  --skip-submodules \
  --skip-runners
```

## Quick flow (manual, step-by-step)

```bash
# 1. Setup (one-time)
# Omit EXECUTORCH_DIR for fresh setup; set it only to reuse an existing checkout.
export EXECUTORCH_DIR=/path/to/executorch
bash model_profiling/scripts/setup_repo.sh

# 2. Build runners (one-time, or when CMake configs change)
bash model_profiling/scripts/build_runners.sh

# 3. Activate venv
source .venv/bin/activate

# 3a. Validate setup, including timing and XNNPACK trace runners
python model_profiling/scripts/validate_setup.py --require-xnntrace-runners

# For Android runner validation, require the NDK and Android runner outputs too:
python model_profiling/scripts/validate_setup.py \
  --require-xnntrace-runners \
  --require-android-runners

# 4. Export model
python model_profiling/export/export_model.py \
  --model mobilenet_v3_small \
  --dtype fp16 \
  --outdir out_mobilenet/artifacts/

# 5. Create config
cp model_profiling/configs/templates/mac_template.json \
   model_profiling/configs/mac_mobilenet.json
# Edit config: set "model" to "out_mobilenet/artifacts/mobilenet_v3_small_xnnpack_fp16.pte"
# Edit config: set "output_root" to "out_mobilenet/runs/mac"

# 6. Run pipeline (automatically runs analysis and generates CSV files)
python3 model_profiling/scripts/mac_pipeline.py \
  --config model_profiling/configs/mac_mobilenet.json

# 7. Generate report (base report with latency + category breakdown)
python3 model_profiling/scripts/generate_report.py \
  --run-dir out_mobilenet/runs/mac

# 7a. Operator-specific bottleneck analysis
#     Identifies top operators by E2E weight, portable vs delegated operators
python3 model_profiling/tools/analyze_etdump_csv.py \
  --timeline-csv out_mobilenet/runs/mac/mac_sme2_on/*_all_runs_timeline.csv \
  --compare out_mobilenet/runs/mac/mac_sme2_off/*_all_runs_timeline.csv \
  --name1 "SME2-Off" \
  --name2 "SME2-On" \
  --output-dir out_mobilenet/runs/mac/ \
  --verbose

# 8. Validate results (optional)
python3 model_profiling/scripts/validate_results.py \
  --results out_mobilenet/runs/mac
```

For kernel-selection evidence, run XNNPACK trace separately from timing:

```bash
python3 model_profiling/scripts/mac_pipeline.py \
  --config model_profiling/configs/toy_cnn_trace_run.json

python3 model_profiling/scripts/validate_results.py \
  --results model_profiling/out_toy_cnn/runs/mac_trace \
  --require-sme2-kernels
```

`manifest.json` is the provenance and artifact index. `metrics.json` contains measurement values plus artifact references.

**See `pipeline_commands.md` for detailed command reference.**

## Notes

- On **macOS Apple Silicon**, you can learn the workflow and get operator-level breakdowns. SME2 acceleration requires Armv9 hardware: Apple M4 Macs and Armv9 Android devices will show SME2 deltas; earlier Apple Silicon will not.

- To observe SME2 deltas and `__neonsme2` kernel paths, use an **SME2-capable Armv9 device** (Android or Apple M4):

```bash
export ANDROID_NDK=/path/to/android-ndk
bash model_profiling/scripts/build_runners.sh

cp model_profiling/configs/templates/android_template.json \
   model_profiling/configs/android.json
# Edit config: set "model" to your .pte path
# Edit config: set "output_root" to "out_<model>/runs/android"
python3 model_profiling/scripts/android_pipeline.py \
  --config model_profiling/configs/android.json

# Pipeline automatically runs analysis - no separate step needed
# Generate base report:
python3 model_profiling/scripts/generate_report.py \
  --run-dir out_<model>/runs/android

# Operator-specific bottleneck analysis
python3 model_profiling/tools/analyze_etdump_csv.py \
  --timeline-csv out_<model>/runs/android/android_sme2_on/*_all_runs_timeline.csv \
  --compare out_<model>/runs/android/android_sme2_off/*_all_runs_timeline.csv \
  --name1 "SME2-Off" \
  --name2 "SME2-On" \
  --output-dir out_<model>/runs/android/ \
  --verbose
```

## Key Principles

1. **Model-agnostic pipeline**: Once you have a `.pte` file, the same pipeline commands work for any model
2. **Config-driven experiments**: JSON configs define what to run, scripts execute them
3. **Output organization**: Results go under `out_<model>/runs/<platform>/` for clear organization
4. **Version traceability**: Runners stay in `executorch/cmake-out/` to track ExecuTorch version

## Reference

- **Command reference**: See `pipeline_commands.md` for detailed workflow
- **Model onboarding**: See learning path documentation for adding new models
- **Report generation**: See agent skill `agent_skill_ml_profiling/generate-report/SKILL.md` for workflow including operator-specific bottleneck analysis, portable vs delegated operator identification, and kernel-level insights
