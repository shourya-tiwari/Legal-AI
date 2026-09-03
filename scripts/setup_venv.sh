#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Create the backend's Linux virtualenv.
#
# Uses --system-site-packages so it inherits an existing GPU PyTorch stack
# (torch+cuXXX / transformers / accelerate) from ~/.local if one is present --
# the in-process neural providers (sentence-transformers) then run on the GPU
# with no extra multi-GB torch download. Core app deps are still pinned and
# installed into the venv itself.
# ---------------------------------------------------------------------------
set -euo pipefail
cd "$(dirname "$0")/../backend"

python3 -m venv --system-site-packages .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

echo
echo "Core env ready. Optional extras:"
echo "  .venv/bin/pip install -r requirements-local.txt          # in-process neural embed/rerank (GPU)"
echo "  .venv/bin/pip install -r requirements-external.txt        # Gemini (Class C) plugin"
echo "  .venv/bin/pip install -r requirements-observability.txt   # OpenTelemetry tracing"
echo "  .venv/bin/pip install -r requirements-eval.txt            # Inspect AI + HF datasets"
echo
echo "Run the suite:  cd backend && .venv/bin/python -m pytest -q"
