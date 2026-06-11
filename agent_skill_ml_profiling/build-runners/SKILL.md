---
name: build-runners
description: Build SME2-on and SME2-off ExecuTorch runner binaries for the profiling kit. Use when Codex needs macOS or Android executor_runner binaries, when executorch was refreshed, when CMake presets changed, when runners are missing, or before running SME2-on versus SME2-off profiling experiments.
---

# Build Runners

## Operating Rules

- Run from the repository root after `setup-workspace` has created `.venv/` and linked or cloned `executorch/`.
- If using an external checkout, keep `EXECUTORCH_DIR=/path/to/executorch` exported for build and validation commands.
- Use `model_profiling/scripts/build_runners.sh`; it merges the repository CMake presets into the ExecuTorch checkout and keeps outputs under `executorch/cmake-out/` for version traceability.
- Build timing-capable runners first. Treat XNNPACK trace collection as a profiling mode, not as latency evidence.
- By default the build script also builds XNNPACK logging runners (`*-xnnlog`) so kernel-selection validation can prove whether SME2 kernels were selected. Use `BUILD_XNNTRACE_RUNNERS=0` only when the task explicitly does not need trace validation.
- Do not copy runners out of `executorch/cmake-out/` unless the user explicitly needs a deployment bundle.

## Required Inputs

- `.venv/` and `executorch/` from `setup-workspace`.
- CMake and Ninja on the host.
- Optional Android build: `ANDROID_NDK` or `ANDROID_NDK_HOME` pointing to an Android NDK with `build/cmake/android.toolchain.cmake`.

## Procedure

1. Confirm setup artifacts:

   ```bash
   test -f .venv/bin/activate
   test -d executorch
   ```

2. Build runners:

   ```bash
   export EXECUTORCH_DIR=/path/to/executorch
   bash model_profiling/scripts/build_runners.sh
   ```

   Timing-only local iteration:

   ```bash
   BUILD_XNNTRACE_RUNNERS=0 bash model_profiling/scripts/build_runners.sh
   ```

3. Validate macOS runner paths when on an Arm macOS host:

   ```bash
   test -x executorch/cmake-out/mac-arm64/executor_runner
   test -x executorch/cmake-out/mac-arm64-sme2-off/executor_runner
   test -x executorch/cmake-out/mac-arm64-xnnlog/executor_runner
   test -x executorch/cmake-out/mac-arm64-sme2-off-xnnlog/executor_runner
   ```

4. Validate Android runner paths when Android builds were requested:

   ```bash
   test -x executorch/cmake-out/android-arm64-v9a/executor_runner
   test -x executorch/cmake-out/android-arm64-v9a-sme2-off/executor_runner
   test -x executorch/cmake-out/android-arm64-v9a-xnnlog/executor_runner
   test -x executorch/cmake-out/android-arm64-v9a-sme2-off-xnnlog/executor_runner
   ```

5. Run setup validation again:

   ```bash
   export EXECUTORCH_DIR=/path/to/executorch
   source .venv/bin/activate
   python model_profiling/scripts/validate_setup.py --require-xnntrace-runners
   ```

## Success Criteria

- SME2-on and SME2-off timing and XNNPACK trace runner binaries exist for the requested platform unless `BUILD_XNNTRACE_RUNNERS=0` was intentionally used.
- The build script exits 0.
- `validate_setup.py --require-xnntrace-runners` passes for the full public validation path.

## Failure Triage

- `.venv` missing: run `setup-workspace`.
- CMake preset or configure failure: inspect `executorch/CMakePresets.json`, rerun `python model_profiling/scripts/merge_cmake_presets.py`, then rerun the build.
- Ninja missing: install Ninja and rerun.
- Android NDK missing: either set `ANDROID_NDK`/`ANDROID_NDK_HOME` or skip Android runner validation.
- Repeated unexplained CMake failures: remove only the affected generated build directory, for example `executorch/cmake-out/mac-arm64`, then rerun the build.

## Handoff

After runner validation succeeds, use `export-model` to create a `.pte` artifact or `run-profiling` if the `.pte` already exists.
