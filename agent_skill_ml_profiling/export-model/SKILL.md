---
name: export-model
description: Export a registered PyTorch model to an ExecuTorch .pte artifact for SME2 profiling. Use when Codex needs to convert toy_cnn, EfficientSAM, EdgeTAM image encoder, or another registered model to portable ExecuTorch format with XNNPACK or portable backend, choose dtype or quantization settings, save graph metadata, or prepare artifacts for profiling.
---

# Export Model

## Operating Rules

- Run from the repository root with `.venv` activated.
- Export to `model_profiling/out_<model>/artifacts/` for the Learning Path examples unless the user requests another output root.
- Prefer `--backend xnnpack` for SME2 profiling because the runner comparison is intended to show delegated backend behavior.
- Do not assume `.etrecord` exists. Check for it and use it when present, but do not fail the export solely because it was not produced.
- If exporting a custom model, verify it is registered in `model_profiling/models/__init__.py` before running the exporter.

## Required Inputs

- Completed `setup-workspace`.
- Model name, dtype, backend, and output directory.
- For custom models: an implementation of `EagerModelBase` with stable `get_eager_model()` and `get_example_inputs()`.

## Procedure

1. Activate the environment:

   ```bash
   source .venv/bin/activate
   ```

2. For the built-in smoke model, export with:

   ```bash
   python model_profiling/export/export_model.py \
     --model toy_cnn \
     --backend xnnpack \
     --dtype fp16 \
     --outdir model_profiling/out_toy_cnn/artifacts
   ```

3. For a named model, use the same shape:

   ```bash
   MODEL_NAME="<model_name>"
   DTYPE="fp16"
   OUTDIR="model_profiling/out_${MODEL_NAME}/artifacts"

   python model_profiling/export/export_model.py \
     --model "${MODEL_NAME}" \
     --backend xnnpack \
     --dtype "${DTYPE}" \
     --outdir "${OUTDIR}" \
     --save-graph
   ```

4. For quantized exports, add `--quantize` only after confirming the ExecuTorch checkout supports the model's quantization path:

   ```bash
   python model_profiling/export/export_model.py \
     --model "${MODEL_NAME}" \
     --backend xnnpack \
     --dtype fp32 \
     --quantize \
     --outdir "${OUTDIR}"
   ```

5. Validate the output:

   ```bash
   find "${OUTDIR}" -maxdepth 1 -name '*.pte' -type f -size +0 -print
   find "${OUTDIR}" -maxdepth 1 -name '*.etrecord' -type f -print
   PTE_FILE="$(find "${OUTDIR}" -maxdepth 1 -name '*.pte' -type f -size +0 | head -1)"
   test -n "${PTE_FILE}"
   ```

## Success Criteria

- A non-empty `.pte` exists in the selected artifact directory.
- Optional `graph.json` exists when `--save-graph` was requested.
- Optional `.etrecord` is recorded for later analysis if the export flow produced one.

## Failure Triage

- `Unknown model`: register the model under `model_profiling/models/` or use an ExecuTorch example model name that exists in the current checkout.
- `ImportError` from model code: install the model dependency into `.venv` or adjust the model wrapper.
- Torch export failure: inspect unsupported ops, dynamic control flow, input signatures, dtype casts, and shape constraints.
- XNNPACK partitioning failure: retry with `--backend portable` to isolate export validity from delegation, then return to XNNPACK after fixing unsupported delegated ops.
- Quantization failure: remove `--quantize` unless the model appears in the current ExecuTorch quantization options.

## Handoff

After export succeeds, use `run-profiling` with the `.pte` path and the runner paths for the target platform.
