# SME2 ExecuTorch Profiling Kit

A complete, self-contained profiling framework for analyzing ExecuTorch model performance with SME2 acceleration. This kit enables operator-level performance analysis to identify bottlenecks, measure SME2 acceleration impact, and make data-driven optimization decisions.

## What This Repository Includes

This repository provides a **complete, runnable profiling framework** with:

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
- **Report Generation**: Comprehensive markdown reports with actionable insights
- **Agent Skills**: Structured, verifiable automation skills for AI coding assistants
  - 8 complete skills covering setup, build, export, profiling, analysis, and reporting
  - Self-contained workflows that can be automated or run manually
- **Model Onboarding Scaffolding**: Framework for adding new models to the profiling workflow
- **Example Models**: Reference implementations (toy_cnn, mobilenet_v3_small, EdgeTAM)

## What It Does

This profiling kit helps you:

1. **Export Models**: Convert PyTorch models to ExecuTorch `.pte` format with proper backend delegation
2. **Measure Performance**: Run models with SME2 acceleration on and off to measure speedup
3. **Analyze Bottlenecks**: Break down inference time by operator categories to identify where time is spent
4. **Identify Optimization Opportunities**: Discover which operators benefit from SME2 and which become new bottlenecks (often data movement operations)
5. **Generate Reports**: Create comprehensive reports with actionable insights for optimization

**Key Insight**: After SME2 accelerates CONV and GEMM operations (3-15× faster), data movement operations (transpose, reshape, layout conversions) often become the dominant bottleneck. This profiling kit makes this bottleneck shift visible, showing you exactly where to focus optimization efforts next.

## Learning Path (Optional)

This code repository accompanies the [**Revealing latent ExecuTorch latency after SME2 acceleration**](https://learn.arm.com/learning-paths/embedded-and-microcontrollers/sme-executorch-profiling/) learning path, which provides comprehensive documentation, step-by-step instructions, and detailed explanations of the performance analysis workflow.

## Quick Start

1. **Clone this repository:**
   ```bash
   git clone https://github.com/ArmDeveloperEcosystem/sme-executorch-profiling.git executorch_sme2_kit
   cd executorch_sme2_kit
   ```

2. **Set up ExecuTorch:**
   ```bash
   bash model_profiling/scripts/setup_repo.sh
   ```

3. **Build runners:**
   ```bash
   bash model_profiling/scripts/build_runners.sh
   ```

4. **Activate venv and export a model:**
   ```bash
   source .venv/bin/activate
   python model_profiling/export/export_model.py \
     --model <model_name> \
     --dtype fp16 \
     --outdir out_<model>/artifacts/
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
   
   # Generate comprehensive markdown report (base report)
   python model_profiling/scripts/generate_report.py \
     --run-dir out_<model>/runs/mac
   
   # For actionable insights: Operator-specific bottleneck analysis
   python model_profiling/tools/analyze_etdump_csv.py \
     --timeline-csv out_<model>/runs/mac/<experiment>/*_all_runs_timeline.csv \
     --compare out_<model>/runs/mac/<experiment_off>/*_all_runs_timeline.csv \
     --name1 "SME2-Off" \
     --name2 "SME2-On" \
     --output-dir out_<model>/runs/mac/ \
     --verbose
   ```
   
   **Note**: The base report shows category-level breakdown. For **actionable insights** (operator-level bottlenecks, portable vs delegated analysis), use `analyze_etdump_csv.py`. See agent skill `07_report_generation.md` for complete workflow.

## Agent Skills for Automation

This repository includes **structured, verifiable agent skills** in `agent_skill_ml_profiling/` that enable AI coding assistants (Claude, Cursor, Copilot, etc.) and CI pipelines to automate the profiling workflow.

**What are agent skills?** These are self-contained automation playbooks with:
- Clear prerequisites and verification steps
- Ordered, executable commands
- Expected outputs and success criteria
- Failure handling and troubleshooting guidance

**Available Skills**:
1. `01_setup_workspace.md` - Initialize profiling environment (~30 min)
2. `02_build_runners.md` - Build SME2-on/off runner binaries (~20 min)
3. `03_export_model.md` - Export PyTorch model to ExecuTorch .pte (~5 min)
4. `04_run_profiling.md` - Execute profiling pipeline (~10 min)
5. `05_analyze_results.md` - Generate operator-category breakdown (~2 min)
6. `06_validate_workflow.md` - End-to-end smoke test (~15 min)
7. `07_report_generation.md` - Generate comprehensive markdown report (~1 min)
8. `08_onboard_edgetam.md` - Onboard EdgeTAM image encoder model (~5 min)

**Quick Start with Agent Skills**:
- **For AI assistants**: Reference skills by name when automating profiling tasks
- **For developers**: Use skills as step-by-step playbooks (run commands sequentially, verify each step)
- **For CI/CD**: Chain skills together for automated regression testing

See [`agent_skill_ml_profiling/readme.md`](agent_skill_ml_profiling/readme.md) for the complete skill catalog and usage patterns.

## Repository Structure

- `model_profiling/export/` - Model export script (with registry patching)
- `model_profiling/models/` - Model registry and onboarding scaffolding
- `model_profiling/scripts/` - Pipeline scripts (mac, android, analysis, setup, build)
- `model_profiling/configs/` - Configuration templates and examples
- `model_profiling/tools/` - Analysis tools (ETDump to CSV, bottleneck analysis)
- `model_profiling/pipeline/` - Core pipeline orchestration code
- `agent_skill_ml_profiling/` - Agent skills for automation (8 complete skills)
- `out_<model>/artifacts/` - Exported `.pte` files (created during export)
- `out_<model>/runs/` - Profiling results (created during pipeline runs)

**Note**: Replace `<model>` with your actual model name. The `out_<model>/` directories are created automatically when you export and run profiling.

## Adding Your Own Model

The profiling pipeline is **model-agnostic** - once you export a `.pte` file, the same commands work for any model. Only the model export step is model-specific.

### Onboarding Options

You have two options for detailed onboarding instructions:

1. **Agent Skill** (recommended for step-by-step automation): See `agent_skill_ml_profiling/08_onboard_edgetam.md` for a complete EdgeTAM onboarding example that demonstrates:
   - Wrapper classes for input/output normalization
   - Operator replacement strategies
   - Shape constraint handling
   - Export-friendly refactoring patterns
   
   **Note**: EdgeTAM is a third-party open source project. When cloning EdgeTAM, you must maintain all copyright notices and comply with EdgeTAM's license terms. See the onboarding skill for details.

2. **Learning Path** (for comprehensive context): See the [learning path documentation](https://learn.arm.com/learning-paths/embedded-and-microcontrollers/sme-executorch-profiling/) for detailed onboarding instructions, tutorials, and best practices.

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

- **Agent Skills**: [`agent_skill_ml_profiling/readme.md`](agent_skill_ml_profiling/readme.md) - Complete catalog of automation skills
- **Command Reference**: [`model_profiling/pipeline_commands.md`](model_profiling/pipeline_commands.md) - Detailed workflow commands
- **Scripts Overview**: [`model_profiling/scripts/readme.md`](model_profiling/scripts/readme.md) - Script documentation
- **Report Generation**: [`agent_skill_ml_profiling/07_report_generation.md`](agent_skill_ml_profiling/07_report_generation.md) - Complete workflow for generating comprehensive reports with operator-specific bottleneck analysis, portable vs delegated operator identification, and kernel-level insights
- **Model Onboarding**: [`agent_skill_ml_profiling/08_onboard_edgetam.md`](agent_skill_ml_profiling/08_onboard_edgetam.md) - Step-by-step EdgeTAM onboarding example

### External Resources

- **Learning Path**: [Revealing latent ExecuTorch latency after SME2 acceleration](https://learn.arm.com/learning-paths/embedded-and-microcontrollers/sme-executorch-profiling/) - Comprehensive documentation, tutorials, and best practices (optional - this repository is self-contained)

## License

This project is licensed under the Apache License, Version 2.0. See the [LICENSE](LICENSE) file for details.

**Third-party licenses**: This repository includes instructions to use third-party open source projects (e.g., EdgeTAM). When using such projects, you must comply with their respective licenses. See the EdgeTAM onboarding documentation for license compliance requirements.
