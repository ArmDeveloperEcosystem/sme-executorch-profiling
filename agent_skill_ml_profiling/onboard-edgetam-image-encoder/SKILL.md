---
name: onboard-edgetam-image-encoder
description: Onboard the EdgeTAM image encoder as a model_profiling registry entry for ExecuTorch export and SME2 profiling. Use when Codex needs to clone or wire the EdgeTAM source, preserve third-party license notices, create an EagerModelBase wrapper, register edgetam_image_encoder, download or verify checkpoints, or prepare the image encoder for export.
---

# Onboard EdgeTAM Image Encoder

## Operating Rules

- Onboard only the EdgeTAM image encoder unless the user explicitly asks for memory encoder, decoder, or full video pipeline support.
- Preserve third-party license files and copyright notices from the EdgeTAM repository.
- Keep third-party source under `model_profiling/models/edgetam/edgetam_core/` and local wrapper code in `model_profiling/models/edgetam/`.
- Do not commit downloaded checkpoints unless the repository policy explicitly allows it.
- Make the wrapper export-friendly before profiling: deterministic `eval()` mode, stable example inputs, and no training-time side effects.

## Required Inputs

- Completed `setup-workspace`.
- Network access to clone EdgeTAM and obtain its checkpoint.
- User confirmation or project policy for third-party source and checkpoint handling when committing changes.

## Procedure

1. Create the model directory:

   ```bash
   mkdir -p model_profiling/models/edgetam
   ```

2. Clone EdgeTAM source if it is not already present:

   ```bash
   EDGETAM_CORE="model_profiling/models/edgetam/edgetam_core"
   test -d "${EDGETAM_CORE}" || git clone https://github.com/facebookresearch/EdgeTAM.git "${EDGETAM_CORE}"
   test -f "${EDGETAM_CORE}/LICENSE"
   ```

3. Install or document required Python dependencies in `.venv`. Common EdgeTAM wrapper dependencies include `hydra-core` and `omegaconf`; inspect the cloned repository before adding more.

4. Add `model_profiling/models/edgetam/model.py` with an `EagerModelBase` implementation that:

   - loads the full EdgeTAM model lazily;
   - loads the checkpoint from `edgetam_core/checkpoints/`;
   - extracts `full_model.image_encoder`;
   - returns `image_encoder.eval()` from `get_eager_model()`;
   - returns a representative image tensor from `get_example_inputs()`, typically `(torch.randn(1, 3, 1024, 1024),)`.

5. Add `model_profiling/models/edgetam/__init__.py` that registers the model:

   ```python
   from .model import EdgeTAMImageEncoderModel
   from .. import register_model

   register_model("edgetam_image_encoder", EdgeTAMImageEncoderModel)
   ```

6. Confirm `model_profiling/models/__init__.py` imports optional EdgeTAM without breaking environments where the source has not been cloned.

7. Export the model:

   ```bash
   source .venv/bin/activate
   python model_profiling/export/export_model.py \
     --model edgetam_image_encoder \
     --backend xnnpack \
     --dtype fp32 \
     --outdir model_profiling/out_edgetam_image_encoder/artifacts \
     --save-graph
   ```

8. Validate artifacts:

   ```bash
   test -s model_profiling/out_edgetam_image_encoder/artifacts/edgetam_image_encoder_xnnpack_fp32.pte
   test -s model_profiling/out_edgetam_image_encoder/artifacts/graph.json
   ```

## Success Criteria

- `edgetam_image_encoder` is registered without breaking `toy_cnn`.
- The wrapper imports cleanly inside `.venv`.
- The `.pte` export completes and produces a non-empty artifact.
- Third-party license files remain present in the cloned source tree.

## Failure Triage

- Checkpoint missing: report the expected path and do not fake a successful export.
- Hydra/config failure: inspect EdgeTAM config paths and clear any already-initialized Hydra global state before composing configs.
- Unsupported export op: isolate the failing submodule, add export-friendly wrapper logic, or document the unsupported op before profiling.
- Memory pressure during export: reduce concurrent workload, use CPU export, and avoid running profiling in parallel.
- License uncertainty: stop before committing third-party code or checkpoint artifacts and ask for policy confirmation.

## Handoff

After export succeeds, use `run-profiling` with `model_profiling/configs/edgetam_image_encoder_run.json` or the Android variant config.
