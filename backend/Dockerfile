# Backend image (docs/v2/ROADMAP.md Phase 7 "Build & supply chain",
# docs/v2/TASKS.md "Produce on-prem/air-gapped builds with
# legalai-providers-external excluded").
#
# Two profiles, selected by PROVIDER_PROFILE at build time:
#   core     (default) -- requirements.txt only. No google-genai anywhere in
#             the image. This is the on-prem/air-gapped build.
#   external -- requirements.txt + requirements-external.txt (Gemini, Class C).
#             The cloud/hybrid profile, where EXTERNAL_PROVIDERS_ENABLED=true
#             is actually meant to be used.
#
# Build:
#   docker build -t legalai-backend:core backend/                       # air-gapped default
#   docker build -t legalai-backend:external --build-arg PROVIDER_PROFILE=external backend/
#
# scripts/check_sbom_allowlist.py (run inside the built image, see
# .github/workflows/backend-tests.yml's `sbom-allowlist` job) is the
# mechanical proof that a `core` image never contains a commercial-provider
# SDK -- not just that no code imports one (tests/test_provider_isolation.py
# already proves that), but that pip never installed one at all.

FROM python:3.13-slim AS base

# PyMuPDF/opencv-python-headless (the "headless" variant specifically avoids
# needing libGL)/faiss-cpu all ship manylinux wheels for current CPython, so
# no apt packages or compiler toolchain are needed for the `core` profile --
# kept minimal on purpose, this is the air-gapped image's floor.
WORKDIR /app

ARG PROVIDER_PROFILE=core

COPY requirements.txt requirements-external.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
    && if [ "$PROVIDER_PROFILE" = "external" ]; then \
         pip install --no-cache-dir -r requirements-external.txt; \
       fi

COPY app ./app
COPY scripts ./scripts

# Baked into the image so `check_sbom_allowlist.py` can report it in the
# artifact it produces without needing a build arg passed at `docker run` time.
RUN echo "$PROVIDER_PROFILE" > /app/.provider_profile

EXPOSE 8000

# No secrets baked in -- every credential comes from the environment
# (docs/v2/ARCHITECTURE.md "Secrets management": Vault/KMS in production,
# a .env file only for local dev, never in the image).
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
