#!/usr/bin/env python3
"""
Install SME2 profiling CMake presets into ExecuTorch's CMakeUserPresets.json.

The project CMakePresets.json stays untouched so the ExecuTorch checkout does
not acquire tracked local patches just to build this profiling kit.
"""

import json
import os
import sys
from pathlib import Path


MANAGED_PRESET_NAMES = {
    "xnnpack-base",
    "android-arm64-v9a",
    "android-arm64-v9a-xnnlog",
    "android-arm64-v9a-sme2-off",
    "android-arm64-v9a-sme2-off-xnnlog",
    "mac-arm64",
    "mac-arm64-xnnlog",
    "mac-arm64-sme2-off",
    "mac-arm64-sme2-off-xnnlog",
    "build-android-arm64-v9a",
    "build-android-arm64-v9a-xnnlog",
    "build-android-arm64-v9a-sme2-off",
    "build-android-arm64-v9a-sme2-off-xnnlog",
    "build-mac-arm64",
    "build-mac-arm64-xnnlog",
    "build-mac-arm64-sme2-off",
    "build-mac-arm64-sme2-off-xnnlog",
}


def select_profiling_presets(base_presets: list, our_presets: list, preset_type: str) -> list:
    base_names = {preset["name"] for preset in base_presets}
    selected = []
    for preset in our_presets:
        name = preset["name"]
        if name not in MANAGED_PRESET_NAMES:
            continue
        if name in base_names:
            print(f"  [merge] Keeping existing {preset_type} preset from ExecuTorch: {name}", file=sys.stderr)
            continue
        print(f"  [merge] Adding {preset_type} preset: {name}", file=sys.stderr)
        selected.append(preset)
    return selected


def merge_user_presets(existing_presets: list, profiling_presets: list) -> list:
    profiling_names = {preset["name"] for preset in profiling_presets}
    merged = [preset for preset in existing_presets if preset.get("name") not in profiling_names]
    merged.extend(profiling_presets)
    return merged


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    root_dir = script_dir.parent.parent
    executorch_dir = Path(os.environ.get("EXECUTORCH_DIR", root_dir / "executorch")).expanduser()
    assets_dir = root_dir / "model_profiling" / "assets"

    executorch_presets_file = executorch_dir / "CMakePresets.json"
    executorch_user_presets_file = executorch_dir / "CMakeUserPresets.json"
    our_presets_file = assets_dir / "cmake_presets.json"

    if not executorch_presets_file.exists():
        print(f"ERROR: ExecuTorch CMakePresets.json not found: {executorch_presets_file}", file=sys.stderr)
        print("  Run setup_repo.sh first to clone or link ExecuTorch.", file=sys.stderr)
        sys.exit(1)

    if not our_presets_file.exists():
        print(f"ERROR: SME2 presets not found: {our_presets_file}", file=sys.stderr)
        sys.exit(1)

    print(f"[merge] Reading base presets from: {executorch_presets_file}", file=sys.stderr)
    with open(executorch_presets_file, "r", encoding="utf-8") as f:
        base_data = json.load(f)

    print(f"[merge] Reading SME2 presets from: {our_presets_file}", file=sys.stderr)
    with open(our_presets_file, "r", encoding="utf-8") as f:
        our_data = json.load(f)

    if executorch_user_presets_file.exists():
        print(f"[merge] Reading existing user presets from: {executorch_user_presets_file}", file=sys.stderr)
        with open(executorch_user_presets_file, "r", encoding="utf-8") as f:
            user_data = json.load(f)
    else:
        user_data = {"version": max(4, int(base_data.get("version", 6)))}

    includes = user_data.setdefault("include", [])
    if "CMakePresets.json" not in includes:
        includes.insert(0, "CMakePresets.json")

    configure_presets = select_profiling_presets(
        base_data.get("configurePresets", []),
        our_data.get("configurePresets", []),
        "configurePresets",
    )
    build_presets = select_profiling_presets(
        base_data.get("buildPresets", []),
        our_data.get("buildPresets", []),
        "buildPresets",
    )

    user_data["configurePresets"] = merge_user_presets(user_data.get("configurePresets", []), configure_presets)
    user_data["buildPresets"] = merge_user_presets(user_data.get("buildPresets", []), build_presets)

    print(f"[merge] Writing profiling presets to: {executorch_user_presets_file}", file=sys.stderr)
    with open(executorch_user_presets_file, "w", encoding="utf-8") as f:
        json.dump(user_data, f, indent=2)
        f.write("\n")

    print("[merge] Successfully installed CMake user presets", file=sys.stderr)


if __name__ == "__main__":
    main()
