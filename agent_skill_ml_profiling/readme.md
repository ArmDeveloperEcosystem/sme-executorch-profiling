---
title: Agent Skills for ML Profiling (SME2 ExecuTorch)
draft: false
---

# Agent Skills for ML Profiling

This directory contains real Codex-style agent skill packages for the SME2 ExecuTorch profiling workflow.

Each canonical skill lives in a folder with:

- `SKILL.md` containing YAML `name` and `description` metadata plus executable agent instructions.
- `agents/openai.yaml` containing UI metadata for agents that consume it.

The historical numbered Markdown files are retained as compatibility entry points for public Arm Learning Path links. They point to the canonical skill package and should not be treated as the source of the workflow.

## Skill Catalog

| Order | Compatibility path | Canonical skill | Purpose |
|---:|---|---|---|
| 1 | [01_setup_workspace.md](01_setup_workspace.md) | [setup-workspace/SKILL.md](setup-workspace/SKILL.md) | Create and validate `.venv/` and `executorch/`. |
| 2 | [02_build_runners.md](02_build_runners.md) | [build-runners/SKILL.md](build-runners/SKILL.md) | Build SME2-on/off `executor_runner` binaries. |
| 3 | [03_export_model.md](03_export_model.md) | [export-model/SKILL.md](export-model/SKILL.md) | Export registered models to `.pte`. |
| 4 | [04_run_profiling.md](04_run_profiling.md) | [run-profiling/SKILL.md](run-profiling/SKILL.md) | Run macOS or Android profiling pipelines. |
| 5 | [05_analyze_results.md](05_analyze_results.md) | [analyze-results/SKILL.md](analyze-results/SKILL.md) | Reprocess ETDump/CSV artifacts and compare results. |
| 6 | [06_validate_workflow.md](06_validate_workflow.md) | [validate-workflow/SKILL.md](validate-workflow/SKILL.md) | Run or audit the toy model smoke test. |
| 7 | [07_report_generation.md](07_report_generation.md) | [generate-report/SKILL.md](generate-report/SKILL.md) | Generate Markdown reports from profiling outputs. |
| 8 | [08_onboard_edgetam.md](08_onboard_edgetam.md) | [onboard-edgetam-image-encoder/SKILL.md](onboard-edgetam-image-encoder/SKILL.md) | Register and export the EdgeTAM image encoder. |

## Recommended Flow

```text
setup-workspace
  -> build-runners
  -> export-model
  -> run-profiling
  -> analyze-results
  -> generate-report
```

Use `validate-workflow` after setup/build or before a demo to prove the full smoke path still works. Use `onboard-edgetam-image-encoder` before `export-model` when the target model is EdgeTAM.

## Agent Ground Rules

- Work from the repository root.
- Use repository scripts before manual commands.
- Preserve generated artifacts until the user asks for cleanup.
- Use timing runs for latency claims and xnntrace runs only for kernel-selection evidence.
- Keep public validation on the pinned public ExecuTorch base with no ET/XNNPACK patches unless local-development exceptions are explicitly reported.
- Treat Android as a separate validation scope: Android runner validation requires `ANDROID_NDK`/`ANDROID_NDK_HOME`, and Android device profiling requires `adb` plus an SME2-capable Armv9 device.
- Keep public compatibility files in place unless the Arm Learning Path is updated at the same time.
