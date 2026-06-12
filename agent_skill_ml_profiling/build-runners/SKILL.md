---
name: build-runners
description: Build SME2-on and SME2-off ExecuTorch runner binaries for the profiling kit. Use when Codex needs macOS or Android executor_runner binaries, when executorch was refreshed, when CMake presets changed, when runners are missing, or before running SME2-on versus SME2-off profiling experiments.
---

# Build Runners

## Operating Rules

- Run from the repository root after `setup-workspace` has created `.venv/` and linked or cloned `executorch/`.
- If using an external checkout, keep `EXECUTORCH_DIR=/path/to/executorch` exported for build and validation commands.
- Use `model_profiling/scripts/build_runners.sh`; it installs profiling presets into ExecuTorch `CMakeUserPresets.json` and keeps outputs under `executorch/cmake-out/` for version traceability.
- Build timing-capable runners first. Treat XNNPACK trace collection as a profiling mode, not as latency evidence.
- By default the build script also builds XNNPACK logging runners (`*-xnnlog`) so kernel-selection validation can prove whether SME2 kernels were selected. Use `BUILD_XNNTRACE_RUNNERS=0` only when the task explicitly does not need trace validation.
- Android runner builds are optional. If `ANDROID_NDK`/`ANDROID_NDK_HOME` is unset, the script exits successfully after macOS runners and prints that Android was skipped. Do not report that as Android validation.
- The profiling presets keep unrelated ExecuTorch LLM/training targets disabled. Do not enable optional targets unless the user is validating those components.
- Do not copy runners out of `executorch/cmake-out/` unless the user explicitly needs a deployment bundle.

## Required Inputs

- `.venv/` and `executorch/` from `setup-workspace`.
- CMake and Ninja on the host.
- Optional Android build: `ANDROID_NDK` or `ANDROID_NDK_HOME` pointing to an Android NDK with `build/cmake/android.toolchain.cmake`.
- Optional Android run: Android platform-tools so `adb` is available, plus an Armv9 Android device with SME2 support when device-side SME2 evidence is required.

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

   For Android runner validation, require the NDK and Android runner outputs:

   ```bash
   python model_profiling/scripts/validate_setup.py \
     --require-xnntrace-runners \
     --require-android-runners
   ```

## Success Criteria

- SME2-on and SME2-off timing and XNNPACK trace runner binaries exist for the requested platform unless `BUILD_XNNTRACE_RUNNERS=0` was intentionally used.
- Android validation is claimed only when `ANDROID_NDK`/`ANDROID_NDK_HOME` was set, Android runner builds completed, and `validate_setup.py --require-xnntrace-runners --require-android-runners` passed.
- The build script exits 0.
- `validate_setup.py --require-xnntrace-runners` passes for macOS smoke validation.

## Failure Triage

- `.venv` missing: run `setup-workspace`.
- CMake preset or configure failure: inspect `executorch/CMakePresets.json` and `executorch/CMakeUserPresets.json`, rerun `python model_profiling/scripts/merge_cmake_presets.py`, then rerun the build.
- Ninja missing: install Ninja and rerun.
- Android NDK missing: either set `ANDROID_NDK`/`ANDROID_NDK_HOME` or explicitly scope the result to macOS-only validation.
- Android runner missing after a build with NDK set: inspect the Android CMake configure/build output; do not fall back to macOS runners for Android claims.
- Repeated unexplained CMake failures: remove only the affected generated build directory, for example `executorch/cmake-out/mac-arm64`, then rerun the build.

## Handoff

After runner validation succeeds, use `export-model` to create a `.pte` artifact or `run-profiling` if the `.pte` already exists.
