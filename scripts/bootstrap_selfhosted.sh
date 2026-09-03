#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Bring up and warm the self-hosted inference layer (Phase 5/6).
#
#   Ollama       -> serves qwen3:8b for generation      (Class B, GPU)
#   tei-embed    -> serves BAAI/bge-m3 embeddings       (Class B, GPU)
#   tei-rerank   -> serves BAAI/bge-reranker-v2-m3       (Class B, GPU)
#
# Idempotent: re-run any time. Requires Docker + the NVIDIA Container Toolkit.
# After it finishes, copy the printed lines into backend/.env (or start from
# backend/.env.example, which already has them).
# ---------------------------------------------------------------------------
set -euo pipefail

cd "$(dirname "$0")/.."

LLM_MODEL="${LLM_MODEL:-qwen3:8b}"

# Docker Compose v2 (`docker compose`) or the legacy v1 binary (`docker-compose`).
if docker compose version >/dev/null 2>&1; then
  DC="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
  DC="docker-compose"
else
  echo "ERROR: Docker Compose not found. Install the v2 plugin:" >&2
  echo "  sudo apt-get install -y docker-compose-plugin   # or: docker-compose-v2" >&2
  exit 1
fi

if ! docker info 2>/dev/null | grep -qi 'nvidia\|gpu'; then
  echo "WARNING: the Docker NVIDIA runtime doesn't look configured. If the model" >&2
  echo "         servers fail to start, install the NVIDIA Container Toolkit." >&2
fi

echo "==> Starting the gpu-profile services (postgres, redis, memgraph, ollama, tei-embed, tei-rerank)"
$DC --profile gpu up -d

echo "==> Waiting for Ollama (http://localhost:11434) ..."
for i in $(seq 1 60); do
  if curl -sf http://localhost:11434/api/tags >/dev/null 2>&1; then break; fi
  sleep 2
  [ "$i" = 60 ] && { echo "Ollama did not come up in time"; exit 1; }
done

echo "==> Pulling ${LLM_MODEL} (multi-GB, first run only) ..."
docker exec legalai-ollama ollama pull "${LLM_MODEL}"

for pair in "tei-embed:8080" "tei-rerank:8081"; do
  name="${pair%%:*}"; port="${pair##*:}"
  echo "==> Waiting for ${name} (http://localhost:${port}/health) -- downloads its model on first boot ..."
  for i in $(seq 1 150); do
    if curl -sf "http://localhost:${port}/health" >/dev/null 2>&1; then break; fi
    sleep 4
    [ "$i" = 150 ] && { echo "${name} did not become healthy in time (check: docker compose logs ${name})"; exit 1; }
  done
done

echo
echo "==> Self-hosted stack is up. GPU residency:"
nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader || true
echo
echo "==> Put these in backend/.env (already present in backend/.env.example):"
cat <<EOF

  LLM_BASE_URL=http://localhost:11434/v1
  LLM_MODEL=${LLM_MODEL}
  EMBEDDING_BASE_URL=http://localhost:8080/v1
  EMBEDDING_MODEL=BAAI/bge-m3
  RERANKER_BASE_URL=http://localhost:8081
  RERANKER_MODEL=BAAI/bge-reranker-v2-m3
  EXTERNAL_PROVIDERS_ENABLED=false

EOF
echo "==> Verify:  curl -s localhost:8000/api/models/status | jq   (after 'uvicorn app.main:app --reload')"
