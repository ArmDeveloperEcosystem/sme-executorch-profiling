#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"  # executorch_sme2_kit/model_profiling/scripts/ -> executorch_sme2_kit/
USER_EXECUTORCH_DIR="${EXECUTORCH_DIR:-}"
EXECUTORCH_DIR="${ROOT_DIR}/executorch"
VENV_DIR="${ROOT_DIR}/.venv"
EXECUTORCH_PIN_FILE="${ROOT_DIR}/model_profiling/assets/executorch_commit.txt"
EXECUTORCH_REPO_URL="${EXECUTORCH_REPO_URL:-https://github.com/pytorch/executorch.git}"
EXISTING_EXECUTORCH_DIR="${EXECUTORCH_DIR_OVERRIDE:-${USER_EXECUTORCH_DIR:-${EXECUTORCH_PATH:-}}}"
if [[ -n "${EXECUTORCH_REF:-}" ]]; then
  EXECUTORCH_CHECKOUT_REF="${EXECUTORCH_REF}"
elif [[ -f "${EXECUTORCH_PIN_FILE}" ]]; then
  EXECUTORCH_CHECKOUT_REF="$(tr -d '[:space:]' < "${EXECUTORCH_PIN_FILE}")"
else
  EXECUTORCH_CHECKOUT_REF="main"
fi

# Allow override via PYTHON env var (defaults to python3)
PYTHON="${PYTHON:-python3}"

echo "[sme2-profiling] Working directory: ${ROOT_DIR}"

on_err() {
  echo "❌ setup_repo.sh failed near: ${BASH_COMMAND}" >&2
  echo "   Tip: run 'bash -x scripts/setup_repo.sh' for a full trace." >&2
}
trap on_err ERR

if [[ -x "${ROOT_DIR}/model_profiling/scripts/check_prereqs.sh" ]]; then
  bash "${ROOT_DIR}/model_profiling/scripts/check_prereqs.sh"
fi

if ! command -v "${PYTHON}" >/dev/null 2>&1; then
  echo "ERROR: ${PYTHON} not found. Install Python 3.9+ and retry." >&2
  exit 1
fi

"${PYTHON}" - <<'PY'
import sys
if sys.version_info < (3, 9):
    raise SystemExit("ERROR: Python 3.9+ required")
print("[sme2-profiling] Python OK:", sys.version.split()[0])
PY

if ! command -v git >/dev/null 2>&1; then
  echo "ERROR: git not found. Install git and retry." >&2
  exit 1
fi

echo "[sme2-profiling] Creating venv: ${VENV_DIR}"
"${PYTHON}" -m venv "${VENV_DIR}"

echo "[sme2-profiling] Activating venv"
# shellcheck disable=SC1091
source "${VENV_DIR}/bin/activate"

echo "[sme2-profiling] Ensuring pip tooling is available"
if ! python -m pip --version >/dev/null 2>&1; then
  echo "ERROR: pip is not available in the venv. Recreate the venv and retry." >&2
  exit 1
fi

# Use a repo-local pip cache to avoid permissions issues (and to reuse downloads).
export PIP_CACHE_DIR="${ROOT_DIR}/.pip-cache"
mkdir -p "${PIP_CACHE_DIR}"

# Optional escape hatch for corporate proxies / broken SSL trust stores.
# This is NOT recommended for normal environments.
if [[ "${SME2_PIP_INSECURE:-0}" == "1" ]]; then
  echo "⚠️  SME2_PIP_INSECURE=1 enabled: pip will trust hosts for PyPI. Use only if you understand the risk." >&2
  export PIP_CONFIG_FILE="${VENV_DIR}/pip.conf"
  cat > "${PIP_CONFIG_FILE}" <<'EOF'
[global]
trusted-host =
  pypi.org
  files.pythonhosted.org
EOF
fi

# Best-effort upgrade. If a user has corporate SSL/proxy issues, we still want them to proceed
# (venv already ships with a working pip/setuptools baseline).
if python -m pip install --upgrade pip wheel setuptools >/dev/null 2>&1; then
  echo "[sme2-profiling] pip tooling upgraded"
else
  echo "⚠️  Could not upgrade pip/wheel/setuptools (network/SSL/proxy issue). Continuing with existing versions." >&2
  echo "    If later installs fail, fix Python certificates/proxy settings and re-run this script." >&2
fi

if [[ -n "${EXISTING_EXECUTORCH_DIR}" ]]; then
  EXISTING_EXECUTORCH_DIR="$(cd "${EXISTING_EXECUTORCH_DIR}" && pwd -P)"
  if [[ ! -d "${EXISTING_EXECUTORCH_DIR}/.git" ]]; then
    echo "ERROR: EXECUTORCH_DIR/EXECUTORCH_DIR_OVERRIDE/EXECUTORCH_PATH is not a git checkout: ${EXISTING_EXECUTORCH_DIR}" >&2
    exit 1
  fi
  if [[ ! -e "${EXECUTORCH_DIR}" ]]; then
    echo "[sme2-profiling] Linking existing ExecuTorch checkout: ${EXISTING_EXECUTORCH_DIR}"
    ln -s "${EXISTING_EXECUTORCH_DIR}" "${EXECUTORCH_DIR}"
  elif [[ "$(cd "${EXECUTORCH_DIR}" && pwd -P)" != "${EXISTING_EXECUTORCH_DIR}" ]]; then
    echo "ERROR: ${EXECUTORCH_DIR} already exists and does not point to ${EXISTING_EXECUTORCH_DIR}" >&2
    exit 1
  fi
fi

if [[ ! -d "${EXECUTORCH_DIR}/.git" ]]; then
  echo "[sme2-profiling] Cloning ExecuTorch: ${EXECUTORCH_DIR}"
  git clone --no-checkout "${EXECUTORCH_REPO_URL}" "${EXECUTORCH_DIR}"
fi

if [[ "${SME2_EXECUTORCH_ALLOW_DIRTY:-0}" != "1" ]]; then
  if ! git -C "${EXECUTORCH_DIR}" diff --quiet || ! git -C "${EXECUTORCH_DIR}" diff --cached --quiet; then
    echo "ERROR: ${EXECUTORCH_DIR} has local tracked changes." >&2
    echo "Refusing to change the ExecuTorch checkout. Commit/stash changes or rerun with SME2_EXECUTORCH_ALLOW_DIRTY=1." >&2
    exit 1
  fi
fi

if [[ -n "${EXISTING_EXECUTORCH_DIR}" ]]; then
  ACTUAL_SHA="$(git -C "${EXECUTORCH_DIR}" rev-parse HEAD)"
  EXPECTED_SHA="${EXECUTORCH_CHECKOUT_REF}"
  if git -C "${EXECUTORCH_DIR}" rev-parse --verify "${EXECUTORCH_CHECKOUT_REF}^{commit}" >/dev/null 2>&1; then
    EXPECTED_SHA="$(git -C "${EXECUTORCH_DIR}" rev-parse "${EXECUTORCH_CHECKOUT_REF}^{commit}")"
  fi
  if [[ "${SME2_EXECUTORCH_ALLOW_REF_MISMATCH:-0}" != "1" && "${ACTUAL_SHA}" != "${EXPECTED_SHA}" ]]; then
    echo "ERROR: existing ExecuTorch checkout is not at the expected ref." >&2
    echo "  expected: ${EXPECTED_SHA}" >&2
    echo "  actual:   ${ACTUAL_SHA}" >&2
    echo "Check out the pinned ref or rerun with SME2_EXECUTORCH_ALLOW_REF_MISMATCH=1." >&2
    exit 1
  fi
  git -C "${EXECUTORCH_DIR}" submodule sync --recursive
  git -C "${EXECUTORCH_DIR}" submodule update --init --recursive
else
  echo "[sme2-profiling] Checking out ExecuTorch ref: ${EXECUTORCH_CHECKOUT_REF}"
  if ! git -C "${EXECUTORCH_DIR}" cat-file -e "${EXECUTORCH_CHECKOUT_REF}^{commit}" 2>/dev/null; then
    if ! git -C "${EXECUTORCH_DIR}" fetch origin "${EXECUTORCH_CHECKOUT_REF}" --depth 1; then
      echo "[sme2-profiling] Direct ref fetch failed; fetching main history as fallback"
      git -C "${EXECUTORCH_DIR}" fetch origin main --depth 10000
    fi
  fi
  if ! git -C "${EXECUTORCH_DIR}" cat-file -e "${EXECUTORCH_CHECKOUT_REF}^{commit}" 2>/dev/null; then
    echo "[sme2-profiling] Pinned ref not found in shallow history; fetching full main history"
    git -C "${EXECUTORCH_DIR}" fetch origin main
  fi
  if ! git -C "${EXECUTORCH_DIR}" cat-file -e "${EXECUTORCH_CHECKOUT_REF}^{commit}" 2>/dev/null; then
    echo "ERROR: ExecuTorch ref not found in ${EXECUTORCH_REPO_URL}: ${EXECUTORCH_CHECKOUT_REF}" >&2
    echo "Set EXECUTORCH_DIR=/path/to/executorch for an existing checkout, or set EXECUTORCH_REPO_URL to a repository that contains the pinned ref." >&2
    exit 1
  fi
  git -C "${EXECUTORCH_DIR}" checkout --detach "${EXECUTORCH_CHECKOUT_REF}"
  git -C "${EXECUTORCH_DIR}" submodule sync --recursive
  git -C "${EXECUTORCH_DIR}" submodule update --init --recursive
fi

if [[ "${SME2_EXECUTORCH_ALLOW_SUBMODULE_MISMATCH:-0}" != "1" ]]; then
  SUBMODULE_STATUS="$(git -C "${EXECUTORCH_DIR}" submodule status --recursive || true)"
  if printf '%s\n' "${SUBMODULE_STATUS}" | grep -Eq '^[-+U]'; then
    echo "ERROR: ExecuTorch submodules are missing or not at recorded commits." >&2
    echo "${SUBMODULE_STATUS}" >&2
    echo "Run 'git -C ${EXECUTORCH_DIR} submodule update --init --recursive' or rerun with SME2_EXECUTORCH_ALLOW_SUBMODULE_MISMATCH=1." >&2
    exit 1
  fi
fi

echo "[sme2-profiling] Preflight: verify pip can download required wheels"
TORCH_REQ_LINE="$(grep -E '^torch==[0-9]+' "${EXECUTORCH_DIR}/requirements-dev.txt" 2>/dev/null | head -1 || true)"
TORCH_REQ="${TORCH_REQ_LINE:-torch}"
TORCH_EXTRA_INDEX="https://download.pytorch.org/whl/nightly/cpu"
TMP_DL_DIR="${ROOT_DIR}/.tmp_pip_downloads"
rm -rf "${TMP_DL_DIR}" && mkdir -p "${TMP_DL_DIR}"

echo "  - downloading: packaging==25.0 (PyPI)"
python -m pip download --no-deps -d "${TMP_DL_DIR}" packaging==25.0 >/dev/null

echo "  - downloading: ${TORCH_REQ} (PyTorch nightly index)"
python -m pip download --no-deps -d "${TMP_DL_DIR}" --extra-index-url "${TORCH_EXTRA_INDEX}" "${TORCH_REQ}" >/dev/null

rm -rf "${TMP_DL_DIR}"
echo "[sme2-profiling] Preflight OK: pip downloads working"

echo "[sme2-profiling] Installing ExecuTorch (editable)"
if (
  cd "${EXECUTORCH_DIR}"
  ./install_executorch.sh --editable
); then
  echo "[sme2-profiling] ExecuTorch install OK"
else
  echo "❌ ExecuTorch install failed." >&2
  echo "Common causes:" >&2
  echo "  - Corporate proxy / TLS certificates (e.g., 'OSStatus -26276' on macOS)" >&2
  echo "    Fix: ensure your Python trusts system certs, then re-run." >&2
  echo "    If you must (not recommended), re-run with SME2_PIP_INSECURE=1." >&2
  echo "  - Missing build tooling (rerun: bash scripts/check_prereqs.sh)" >&2
  exit 1
fi

echo "[sme2-profiling] Done."
echo "Next:"
echo "  - Build runners: bash model_profiling/scripts/build_runners.sh"
echo "  - Export model : source .venv/bin/activate && python model_profiling/export/export_model.py --model mobilenet_v3_small --dtype fp16 --outdir out_mobilenet/artifacts/"
