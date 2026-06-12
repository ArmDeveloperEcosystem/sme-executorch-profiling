# SME2 ExecuTorch Profiling Kit

A profiling framework for analyzing ExecuTorch model performance with SME2 acceleration. Provides operator-level performance analysis to identify bottlenecks and measure SME2 acceleration impact.

## What This Repository Includes

This repository provides a profiling framework with:

- **Model Export Tools**: Export PyTorch models to ExecuTorch `.pte` format with XNNPACK backend delegation
- **Profiling Pipeline**: Automated performance measurement pipeline for macOS and Android platforms
  - SME2-on and SME2-off comparison runs
  - Timing-only runs for accurate latency measurements
  - Trace-enabled runs for kernel-level analysis
  - Automatic ETDump analysis and CSV generation
- **Analysis Tools**: Operator-level performance analysis and bottleneck identification
  - Operator-category breakdown (CONV, GEMM, Data Movement, Elementwise, Other)
  - Operator-specific bottleneck analysis
  - Portable vs delegated operator identification
  - Kernel-level insights (SME2 vs standard kernels)
- **Report Generation**: Markdown reports with performance analysis
- **Agent Skills**: Automation skills for AI coding assistants
  - 8 skills covering setup, build, export, profiling, analysis, and reporting
  - Workflows that can be automated or run manually
- **Model Onboarding Scaffolding**: Framework for adding new models to the profiling workflow
- **Example Models**: Reference implementations (toy_cnn, mobilenet_v3_small, EdgeTAM)

## What It Does

This framework provides:

1. **Export Models**: Convert PyTorch models to ExecuTorch `.pte` format with proper backend delegation
2. **Measure Performance**: Run models with SME2 acceleration on and off to measure speedup
3. **Analyze Bottlenecks**: Break down inference time by operator categories to identify where time is spent
4. **Identify Optimization Opportunities**: Discover which operators benefit from SME2 and which become new bottlenecks (often data movement operations)
5. **Generate Reports**: Create reports with performance analysis for optimization

**Key Insight**: After SME2 accelerates CONV and GEMM operations (3-15× faster), data movement operations (transpose, reshape, layout conversions) often become the dominant bottleneck. This framework makes the bottleneck shift visible, showing where to focus optimization efforts.

## Learning Path (Optional)

This code repository accompanies the [**Profiling ExecuTorch Models with SME2 on Arm**](https://learn.arm.com/learning-paths/cross-platform/sme-executorch-profiling/) learning path, which provides additional documentation and step-by-step instructions.

## Requirements

- Arm macOS host for the local smoke workflow. SME2 kernel-selection proof on macOS requires SME2-capable Apple Silicon, such as Apple M4.
- Python 3.9+, Git, CMake, Ninja, and Xcode Command Line Tools on macOS.
- Network access to GitHub and Python package indexes for fresh setup.
- Optional Android build: set `ANDROID_NDK` or `ANDROID_NDK_HOME` to an Android NDK containing `build/cmake/android.toolchain.cmake`. If neither variable is set, `build_runners.sh` builds macOS runners and skips Android.
- Optional Android run: install Android platform-tools so `adb` is available, and use an Armv9 Android device with SME2 support to observe SME2 kernel deltas.

## Quick Start

1. **Clone this repository:**
   ```bash
   git clone https://github.com/ArmDeveloperEcosystem/sme-executorch-profiling.git executorch_sme2_kit
   cd executorch_sme2_kit
   ```

2. **Set up ExecuTorch:**

   Fresh setup, where the script clones the pinned public ExecuTorch ref:
   ```bash
   bash model_profiling/scripts/setup_repo.sh
   ```

   Or reuse an existing ExecuTorch checkout:
   ```bash
   export EXECUTORCH_DIR=/path/to/executorch
   bash model_profiling/scripts/setup_repo.sh
   ```

   Setup uses the pinned public ExecuTorch commit recorded in `model_profiling/assets/executorch_commit.txt`. When `EXECUTORCH_DIR` points to an existing checkout, setup links it into this repo as `./executorch`, initializes submodules, and installs it only if the checkout is at that commit or a clean descendant. Validation expects no local ET/XNNPACK patches for the public demo workflow.
   The editable install disables optional MLX/CoreML/LLM/training CMake targets by default, and the runner presets keep unrelated LLM/training targets off, because this profiling flow validates XNNPACK execution and SME2 kernel selection.

3. **Build runners:**
   ```bash
   bash model_profiling/scripts/build_runners.sh
   ```
   If you reused an external ExecuTorch checkout, keep `EXECUTORCH_DIR` exported for build and profiling commands.
   This builds timing runners and XNNPACK logging runners used for SME2 kernel-selection validation. Android runners are built only when `ANDROID_NDK` or `ANDROID_NDK_HOME` is set.

4. **Activate venv and export a model:**
   ```bash
   source .venv/bin/activate
   python model_profiling/scripts/validate_setup.py --require-xnntrace-runners
   python model_profiling/export/export_model.py \
     --model <model_name> \
     --dtype fp16 \
     --outdir out_<model>/artifacts/
   ```
   For Android runner validation, use:
   ```bash
   python model_profiling/scripts/validate_setup.py \
     --require-xnntrace-runners \
     --require-android-runners
   ```

5. **Create config and run profiling pipeline:**
   ```bash
   # Copy template
   cp model_profiling/configs/templates/mac_template.json \
      model_profiling/configs/my_experiment.json
   # Edit config: set "model" to your .pte path
   # Edit config: set "output_root" to "out_<model>/runs/mac"
   
   python model_profiling/scripts/mac_pipeline.py \
     --config model_profiling/configs/my_experiment.json
   # Pipeline automatically runs analysis and generates CSV files
   ```

6. **View results:**
   ```bash
   # Analysis runs automatically during pipeline execution
   # Results include CSV files, pipeline_summary.json/md, and analysis_summary.json
   # Optional: Re-run analysis if needed
   python model_profiling/scripts/analyze_results.py \
     --run-dir out_<model>/runs/mac
   
   # Generate markdown report (base report)
   python model_profiling/scripts/generate_report.py \
     --run-dir out_<model>/runs/mac
   
   # Operator-specific bottleneck analysis
   python model_profiling/tools/analyze_etdump_csv.py \
     --timeline-csv out_<model>/runs/mac/<experiment>/*_all_runs_timeline.csv \
     --compare out_<model>/runs/mac/<experiment_off>/*_all_runs_timeline.csv \
     --name1 "SME2-Off" \
     --name2 "SME2-On" \
     --output-dir out_<model>/runs/mac/ \
     --verbose
   ```

   Validate timing output with `python model_profiling/scripts/validate_results.py --results out_<model>/runs/mac`. For the toy smoke workflow, validate XNNPACK SME2 kernel evidence separately with:
   ```bash
   python model_profiling/scripts/mac_pipeline.py \
     --config model_profiling/configs/toy_cnn_trace_run.json
   python model_profiling/scripts/validate_results.py \
     --results model_profiling/out_toy_cnn/runs/mac_trace \
     --require-sme2-kernels
   ```
   
   **Note**: The base report shows category-level breakdown. For operator-level bottlenecks and portable vs delegated analysis, use `analyze_etdump_csv.py`. See the `generate-report` agent skill for the workflow.

## Agent Skills for Automation

This repository includes agent skills in `agent_skill_ml_profiling/` for AI coding assistants (Codex, Claude, Cursor, Copilot, etc.) and CI pipelines to automate the profiling workflow.

**What are agent skills?** These are self-contained skill packages with:
- Clear prerequisites and verification steps
- Ordered, executable commands
- Expected outputs and success criteria
- Failure handling and troubleshooting guidance
- `SKILL.md` frontmatter for agent discovery

**Available Skills**:
1. `setup-workspace` - Initialize profiling environment (~30 min)
2. `build-runners` - Build SME2-on/off runner binaries (~20 min)
3. `export-model` - Export PyTorch model to ExecuTorch .pte (~5 min)
4. `run-profiling` - Execute profiling pipeline (~10 min)
5. `analyze-results` - Generate operator-category breakdown (~2 min)
6. `validate-workflow` - End-to-end smoke test (~15 min)
7. `generate-report` - Generate Markdown report (~1 min)
8. `onboard-edgetam-image-encoder` - Onboard EdgeTAM image encoder model (~5 min)

**Quick Start with Agent Skills**:
- **For AI assistants**: Load the canonical `agent_skill_ml_profiling/<skill-name>/SKILL.md` file
- **For developers**: Use skills as step-by-step playbooks (run commands sequentially, verify each step)
- **For CI/CD**: Chain skills together for automated regression testing

The historical numbered files, such as `01_setup_workspace.md`, remain in place as public compatibility entry points for Learning Path links. See [`agent_skill_ml_profiling/readme.md`](agent_skill_ml_profiling/readme.md) for the catalog.

## Repository Structure

- `model_profiling/export/` - Model export script (with registry patching)
- `model_profiling/models/` - Model registry and onboarding scaffolding
- `model_profiling/scripts/` - Pipeline scripts (mac, android, analysis, setup, build)
- `model_profiling/configs/` - Configuration templates and examples
- `model_profiling/tools/` - Analysis tools (ETDump to CSV, bottleneck analysis)
- `model_profiling/pipeline/` - Core pipeline orchestration code
- `agent_skill_ml_profiling/` - Agent skills for automation (8 skills)
- `out_<model>/artifacts/` - Exported `.pte` files (created during export)
- `out_<model>/runs/` - Profiling results (created during pipeline runs)

**Note**: Replace `<model>` with your actual model name. The `out_<model>/` directories are created automatically when you export and run profiling.

## Adding Your Own Model

The profiling pipeline is **model-agnostic** - once you export a `.pte` file, the same commands work for any model. Only the model export step is model-specific.

### Onboarding Options

You have two options for detailed onboarding instructions:

1. **Agent Skill** (recommended for step-by-step automation): See `agent_skill_ml_profiling/onboard-edgetam-image-encoder/SKILL.md` for an EdgeTAM onboarding workflow that demonstrates:
   - Local model registry integration
   - Third-party source and license handling
   - Checkpoint and config validation
   - Export-friendly wrapper shape and signature control
   
   **Note**: EdgeTAM is a third-party open source project. When cloning EdgeTAM, you must maintain all copyright notices and comply with EdgeTAM's license terms. See the onboarding skill for details.

2. **Learning Path**: See the [learning path documentation](https://learn.arm.com/learning-paths/cross-platform/sme-executorch-profiling/) for onboarding instructions and tutorials.

### Quick Onboarding Steps

1. Create `model_profiling/models/<your_model>/` with:
   - `__init__.py` - Registers the model
   - `model.py` - Implements `EagerModelBase` interface
   - `vendor/` - (optional) vendored upstream code

2. Export using the same `export_model.py` script:
   ```bash
   python model_profiling/export/export_model.py \
     --model <your_model> \
     --dtype fp16 \
     --outdir out_<your_model>/artifacts/
   ```

3. Run the same pipeline scripts with your exported `.pte`:
   ```bash
   python model_profiling/scripts/mac_pipeline.py \
     --config model_profiling/configs/my_experiment.json
   ```

The pipeline automatically handles analysis and report generation - no model-specific changes needed after export.

## Reference Documentation

### In This Repository

- **Agent Skills**: [`agent_skill_ml_profiling/readme.md`](agent_skill_ml_profiling/readme.md) - Catalog of automation skills
- **Command Reference**: [`model_profiling/pipeline_commands.md`](model_profiling/pipeline_commands.md) - Detailed workflow commands
- **Scripts Overview**: [`model_profiling/scripts/readme.md`](model_profiling/scripts/readme.md) - Script documentation
- **Report Generation**: [`agent_skill_ml_profiling/generate-report/SKILL.md`](agent_skill_ml_profiling/generate-report/SKILL.md) - Workflow for generating reports with operator-specific bottleneck analysis, portable vs delegated operator identification, and kernel-level insights
- **Model Onboarding**: [`agent_skill_ml_profiling/onboard-edgetam-image-encoder/SKILL.md`](agent_skill_ml_profiling/onboard-edgetam-image-encoder/SKILL.md) - Step-by-step EdgeTAM image encoder onboarding workflow

### External Resources

- **Learning Path**: [Profiling ExecuTorch Models with SME2 on Arm](https://learn.arm.com/learning-paths/cross-platform/sme-executorch-profiling/) - Additional documentation and tutorials (optional - this repository is self-contained)

## License

This project is licensed under the Apache License, Version 2.0. See the [LICENSE](LICENSE) file for details.

**Third-party licenses**: This repository includes instructions to use third-party open source projects (e.g., EdgeTAM). When using such projects, you must comply with their respective licenses. See the EdgeTAM onboarding documentation for license compliance requirements.
