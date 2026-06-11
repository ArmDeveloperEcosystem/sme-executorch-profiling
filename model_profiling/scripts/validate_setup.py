#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional


ROOT = Path(__file__).resolve().parents[2]  # executorch_sme2_kit/model_profiling/scripts/ -> executorch_sme2_kit/
PIN_FILE = ROOT / "model_profiling" / "assets" / "executorch_commit.txt"


def check(condition: bool, ok: str, fail: str) -> bool:
    if condition:
        print(f"✅ {ok}")
        return True
    print(f"❌ {fail}")
    return False


def check_or_warn(condition: bool, allowed: bool, ok: str, fail: str, warning: str) -> bool:
    if condition:
        print(f"✅ {ok}")
        return True
    if allowed:
        print(f"⚠️  {warning}")
        return True
    print(f"❌ {fail}")
    return False


def _read_pin() -> Optional[str]:
    if not PIN_FILE.exists():
        return None
    value = PIN_FILE.read_text(encoding="utf-8").strip()
    return value or None


def _git_output(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args]).decode("utf-8").strip()


def _has_tracked_changes(repo: Path) -> bool:
    try:
        subprocess.check_call(["git", "-C", str(repo), "diff", "--quiet"])
        subprocess.check_call(["git", "-C", str(repo), "diff", "--cached", "--quiet"])
        return False
    except subprocess.CalledProcessError:
        return True


def _submodules_ok(repo: Path) -> bool:
    try:
        output = _git_output(repo, "submodule", "status", "--recursive")
    except Exception:
        return True
    for line in output.splitlines():
        if line.startswith("-") or line.startswith("+") or line.startswith("U"):
            return False
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate SME2 profiling kit setup.")
    ap.add_argument("--model", type=Path, default=None, help="Optional: validate a .pte model path exists")
    ap.add_argument(
        "--executorch-dir",
        type=Path,
        default=Path(os.environ.get("EXECUTORCH_DIR", ROOT / "executorch")),
        help="ExecuTorch checkout to validate. Defaults to $EXECUTORCH_DIR when set, otherwise ./executorch.",
    )
    ap.add_argument(
        "--allow-version-mismatch",
        action="store_true",
        help="Warn instead of failing when ExecuTorch HEAD differs from the checked-in pin.",
    )
    ap.add_argument(
        "--allow-dirty",
        action="store_true",
        help="Warn instead of failing when the ExecuTorch checkout has tracked local changes.",
    )
    ap.add_argument(
        "--allow-submodule-mismatch",
        action="store_true",
        help="Warn instead of failing when ExecuTorch submodules are missing or at unexpected commits.",
    )
    ap.add_argument("--skip-runners", action="store_true", help="Do not require built runner binaries.")
    ap.add_argument("--skip-venv", action="store_true", help="Do not require the repo-local .venv.")
    ap.add_argument("--skip-submodules", action="store_true", help="Do not require initialized ExecuTorch submodules.")
    ap.add_argument(
        "--require-xnntrace-runners",
        action="store_true",
        help="Require XNNPACK logging runner variants in addition to timing runners.",
    )
    args = ap.parse_args()

    all_ok = True
    expected_sha = _read_pin()

    all_ok &= check(sys.version_info >= (3, 9), "Python >= 3.9", f"Python too old: {sys.version.split()[0]}")

    all_ok &= check(shutil.which("git") is not None, "git available", "git not found")
    all_ok &= check(shutil.which("cmake") is not None, "cmake available", "cmake not found (install CMake 3.29+)")

    is_arm64 = platform.machine() in ("arm64", "aarch64")
    all_ok &= check(is_arm64, f"host arch: {platform.machine()}", "expected arm64 host for best experience")

    if args.skip_venv:
        print("⚠️  Skipping .venv check")
    else:
        venv_ok = (ROOT / ".venv").exists()
        all_ok &= check(venv_ok, ".venv exists", "missing .venv (run model_profiling/scripts/setup_repo.sh)")

    executorch_dir = args.executorch_dir.expanduser().resolve()
    all_ok &= check(executorch_dir.exists(), "executorch checkout exists", "missing executorch/ (run model_profiling/scripts/setup_repo.sh)")

    if executorch_dir.exists():
        try:
            sha = _git_output(executorch_dir, "rev-parse", "HEAD")
            dirty = _has_tracked_changes(executorch_dir)
            print(f"ℹ️  ExecuTorch SHA: {sha}{' (dirty)' if dirty else ''}")
            if expected_sha:
                version_ok = sha == expected_sha
                message = f"ExecuTorch matches pinned SHA: {expected_sha}"
                mismatch = f"ExecuTorch SHA mismatch: expected {expected_sha}, got {sha}"
                all_ok &= check_or_warn(
                    version_ok,
                    args.allow_version_mismatch,
                    message,
                    mismatch,
                    f"{mismatch}; continuing because --allow-version-mismatch was set",
                )
            all_ok &= check_or_warn(
                not dirty,
                args.allow_dirty,
                "ExecuTorch has no tracked local patches",
                "ExecuTorch has tracked local patches",
                "ExecuTorch has tracked local patches; continuing because --allow-dirty was set",
            )
            if args.skip_submodules:
                print("⚠️  Skipping ExecuTorch submodule check")
            else:
                all_ok &= check_or_warn(
                    _submodules_ok(executorch_dir),
                    args.allow_submodule_mismatch,
                    "ExecuTorch submodules match recorded commits",
                    "ExecuTorch submodules are missing or at unexpected commits",
                    "ExecuTorch submodules are missing or mismatched; continuing because --allow-submodule-mismatch was set",
                )
        except Exception as exc:
            all_ok &= check(False, "ExecuTorch git metadata readable", f"Could not read ExecuTorch git metadata: {exc}")

    try:
        import executorch  # noqa: F401

        all_ok &= check(True, "ExecuTorch import ok", "ExecuTorch import failed")
    except Exception as exc:
        all_ok &= check(False, "ExecuTorch import ok", f"ExecuTorch import failed: {exc}")

    if args.model is not None:
        all_ok &= check(args.model.exists(), f"model exists: {args.model}", f"model not found: {args.model}")

        etrecord = Path(str(args.model) + ".etrecord")
        all_ok &= check(etrecord.exists(), f"etrecord exists: {etrecord}", f"etrecord not found: {etrecord}")

    if not args.skip_runners:
        required_runners = [
            executorch_dir / "cmake-out" / "mac-arm64" / "executor_runner",
            executorch_dir / "cmake-out" / "mac-arm64-sme2-off" / "executor_runner",
        ]
        if args.require_xnntrace_runners:
            required_runners.extend(
                [
                    executorch_dir / "cmake-out" / "mac-arm64-xnnlog" / "executor_runner",
                    executorch_dir / "cmake-out" / "mac-arm64-sme2-off-xnnlog" / "executor_runner",
                ]
            )
        for runner in required_runners:
            all_ok &= check(runner.exists(), f"runner exists: {runner}", f"runner missing: {runner}")

    build_script = ROOT / "model_profiling" / "scripts" / "build_runners.sh"
    all_ok &= check(build_script.exists(), "model_profiling/scripts/build_runners.sh exists", "missing model_profiling/scripts/build_runners.sh")

    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
