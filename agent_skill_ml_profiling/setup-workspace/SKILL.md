---
name: setup-workspace
description: Set up or repair the SME2 ExecuTorch profiling workspace. Use when Codex needs to create the repo-local Python virtual environment, clone or refresh the required executorch checkout, install ExecuTorch for profiling, handle setup failures, or validate that the workspace is ready before building runners, exporting models, or profiling.
---

# Setup Workspace

## Operating Rules

- Run from the `sme-executorch-profiling` repository root.
- Use the repository scripts first; only fall back to manual commands when a script fails and the failure points to a specific missing prerequisite.
- Prefer an existing ExecuTorch checkout by exporting `EXECUTORCH_DIR` before setup/build/profiling commands.
- Do not rename the repo-local `executorch/` link. Setup creates it when `EXECUTORCH_DIR` points to an existing checkout so existing configs continue to work.
- Treat `.venv/`, `.pip-cache/`, `.tmp_pip_downloads/`, `executorch/`, and `out_<model>/` as generated local artifacts.
- Preserve the pinned public ExecuTorch base. By default `setup_repo.sh` checks out `model_profiling/assets/executorch_commit.txt`; an existing checkout may be at that commit or a clean descendant. Use `EXECUTORCH_REF=<sha-or-ref>` only when the user intentionally wants a different ExecuTorch base.
- No ExecuTorch or XNNPACK patches are required for the public toy/demo workflow. Treat tracked changes or mismatched submodules in `executorch/` as a compatibility problem unless the user explicitly opts into a local-development exception.
- Stop before downstream work if setup validation fails for setup-owned checks. Use `--skip-runners` before the build stage; runner checks belong to `build-runners`.

## Required Inputs

- Python 3.9 or newer, Git, CMake, and enough disk space for ExecuTorch and build outputs.
- For later runner builds: Ninja and, on macOS, Xcode Command Line Tools.
- Network access to GitHub and Python package indexes.
- Optional: `PYTHON=/path/to/python3` when the user needs a specific interpreter.
- Optional: `EXECUTORCH_REF=<sha-or-ref>` to override the checked-in ExecuTorch pin.
- Optional: `EXECUTORCH_REPO_URL=<url>` to clone a fork instead of public PyTorch ExecuTorch.
- Optional: `EXECUTORCH_DIR=/path/to/executorch` to link an existing ExecuTorch checkout into this repo as `./executorch`. `EXECUTORCH_DIR_OVERRIDE` and `EXECUTORCH_PATH` are supported compatibility aliases.
- Optional Android build prerequisite: `ANDROID_NDK` or `ANDROID_NDK_HOME` pointing to an Android NDK with `build/cmake/android.toolchain.cmake`. This is not needed for macOS-only smoke validation.
- Optional Android run prerequisite: Android platform-tools so `adb` is available, plus an Armv9 Android device with SME2 support for device-side SME2 deltas.
- Optional local-development exceptions: `SME2_EXECUTORCH_ALLOW_DIRTY=1`, `SME2_EXECUTORCH_ALLOW_REF_MISMATCH=1`, or `SME2_EXECUTORCH_ALLOW_SUBMODULE_MISMATCH=1`. Do not use these for public validation unless the user accepts that results are from a custom setup.
- Optional: `SME2_EXECUTORCH_INSTALL_EXAMPLES=0` to skip ExecuTorch example dependencies when the task only needs local toy-model validation. Leave it unset for public demo/model workflows that use ExecuTorch example models.
- Optional: `SME2_EXECUTORCH_ENABLE_OPTIONAL_APPLE_BACKENDS=1` to let ExecuTorch build optional Apple backends during editable install. The profiling workflow leaves these off by default because XNNPACK/SME2 validation does not need MLX or CoreML.
- Optional: `SME2_EXECUTORCH_INSTALL_CMAKE_ARGS="..."` to replace the setup script's default editable-install CMake flags.
- Optional: `SME2_PIP_INSECURE=1` only as a last resort for known TLS/proxy breakage.

## Procedure

1. Check that the caller is in the repository root:

   ```bash
   test -f model_profiling/scripts/setup_repo.sh
   ```

2. Choose the setup path.

   Fresh machine or no local ExecuTorch checkout. Use this only when `EXECUTORCH_REPO_URL` points at a repository containing the checked-in pin:

   ```bash
   bash model_profiling/scripts/setup_repo.sh
   ```

   Existing ExecuTorch checkout:

   ```bash
   export EXECUTORCH_DIR=/path/to/executorch
   bash model_profiling/scripts/setup_repo.sh
   ```

   The fresh path creates `.venv/`, clones or refreshes `executorch/`, checks out the pinned public ExecuTorch ref, initializes submodules, verifies package downloads, and installs ExecuTorch in editable mode. The existing-checkout path creates `./executorch` as a symlink to the supplied checkout, verifies that the checkout is at the pinned commit or a clean descendant, initializes submodules, verifies package downloads, and installs it. Setup disables optional MLX/CoreML/LLM/training CMake targets by default because the public profiling flow validates XNNPACK runners and does not require those backends; runner presets also keep LLM/training targets off.

3. Activate the environment for any follow-up Python commands:

   ```bash
   source .venv/bin/activate
   ```

4. Validate the workspace:

   ```bash
   python model_profiling/scripts/validate_setup.py --skip-runners
   python -c "import executorch; print(executorch.__file__)"
   ```

   To check a checkout before linking or installing it:

   ```bash
   python model_profiling/scripts/validate_setup.py \
     --executorch-dir /path/to/executorch \
     --skip-venv \
     --skip-submodules \
     --skip-runners
   ```

   Treat Python, `.venv`, `executorch/`, version compatibility, local patch, submodule, or import failures as setup failures.

## Success Criteria

- `.venv/bin/python` exists.
- `executorch/.git` exists.
- `git -C executorch rev-parse HEAD` is the commit in `model_profiling/assets/executorch_commit.txt` or a descendant unless `EXECUTORCH_REF` was intentionally overridden.
- `git -C executorch status --porcelain --untracked-files=no --ignore-submodules=none` and `git -C executorch submodule status --recursive` show no tracked local patches, dirty submodules, or submodule mismatches for public validation.
- `python -c "import executorch"` succeeds inside `.venv`.
- Imports for `executorch.exir`, XNNPACK partitioning, `executorch.devtools`, and export utilities succeed inside `.venv`.
- `model_profiling/scripts/validate_setup.py --skip-runners` passes before runner builds.

## Failure Triage

- Missing Python, Git, CMake, or Ninja: install the tool, then rerun the setup script.
- Missing Xcode Command Line Tools on macOS: run `xcode-select --install`, then rerun setup/build.
- Missing Android NDK: continue with macOS-only validation, or set `ANDROID_NDK`/`ANDROID_NDK_HOME` before building Android runners.
- Python version mismatch: rerun with `PYTHON=/path/to/python3.9+`.
- TLS, proxy, or wheel download failure: fix the certificate/proxy setup first; use `SME2_PIP_INSECURE=1` only when the user accepts the security tradeoff.
- ExecuTorch install or import failure: reactivate `.venv`, rerun setup, and include the final install/import error in the report. If the failure mentions optional Apple backend tooling such as Metal, confirm the setup default CMake args are active and `SME2_EXECUTORCH_ENABLE_OPTIONAL_APPLE_BACKENDS` is not set.
- Dirty, customized, or version-mismatched `executorch/`: do not overwrite user changes silently. Report the actual SHA, expected base SHA, tracked diff/submodule state, and whether any local-development exception was used.

## Handoff

After setup succeeds, use `build-runners` to produce `executor_runner` binaries or `export-model` if valid runners already exist.
