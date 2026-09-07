# backend/app/config.py
"""
Centralized, typed application configuration.

Single source of truth for environment-derived settings, replacing scattered
os.getenv(...) calls (and their inconsistent defaults) across service modules.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # ---- Model Router (docs/v2/AI_STACK.md) ----------------------------------
    # Providers are classified by WHERE they run, not who sells them:
    #   Class A -- deterministic / CPU     Class B -- self-hosted neural
    #   Class C -- external provider API (optional; absent in air-gapped builds)
    #
    # Self-hosted generation (Class B): an OpenAI-compatible endpoint --
    # Ollama (http://localhost:11434/v1), vLLM, SGLang, llama.cpp server, ...
    # Empty LLM_BASE_URL => the local-llm provider reports itself unavailable
    # and the router falls through to Class C (if enabled) -- the Phase 5->6
    # interim. Phase 6 makes a self-hosted model the default.
    LLM_BASE_URL: str = ""
    LLM_MODEL: str = "qwen2.5:3b"
    LLM_API_KEY: str = ""
    # Escalation target (Phase 6, docs/v2/AI_STACK.md "Escalation without a
    # bigger vendor"): same endpoint, a bigger self-hosted model. Used when a
    # caller passes hard=True and the policy has an `escalate_to` for the task.
    LLM_LARGE_MODEL: str = "qwen3:14b"

    # Self-hosted embeddings (Class B). EMBEDDING_BASE_URL points at a
    # TEI / Infinity / OpenAI-compatible embedding server; if unset, the
    # router uses the optional sentence-transformers extra when installed,
    # else the always-available Class A hashing embedder.
    EMBEDDING_BASE_URL: str = ""
    EMBEDDING_API_KEY: str = ""
    EMBEDDING_MODEL: str = "BAAI/bge-small-en-v1.5"

    # Self-hosted reranker (Class B). RERANKER_BASE_URL points at a dedicated
    # cross-encoder server -- a Text Embeddings Inference (TEI) container with
    # its /rerank route (docs/v2/MODEL_STACK.md). If unset, the router uses the
    # optional sentence-transformers CrossEncoder when installed, else the
    # always-available Class A lexical (token-overlap) reranker.
    RERANKER_BASE_URL: str = ""
    RERANKER_API_KEY: str = ""
    RERANKER_MODEL: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    # NLI faithfulness head (Phase 6, Class A -- the Verifier's safety gate,
    # app/services/model_router/providers/nli_local.py). In-process transformers
    # model; needs `requirements-local.txt`. Disabled or absent => the Verifier
    # falls back to lexical overlap, honestly labelled.
    NLI_MODEL: str = "MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli"
    NLI_ENABLED: bool = True

    # Zero-shot NER (Phase 6, Class B -- GLiNER, providers/gliner_local.py).
    # Optional `gliner` extra; regex extraction in nlp/entities.py is the floor.
    NER_MODEL: str = "urchade/gliner_multi-v2.1"
    NER_ENABLED: bool = True
    NER_LABELS: list[str] = [
        "party", "organization", "person", "monetary amount", "date",
        "duration", "governing law jurisdiction", "statute citation",
    ]
    RERANKER_ENABLED: bool = True

    # Class C gating. EXTERNAL_PROVIDERS_ENABLED=false OR STRICT_LOCAL_ONLY=true
    # keeps every request on self-hosted providers. On-prem/air-gapped builds
    # also simply don't install `google-genai` (requirements-external.txt), so
    # the provider is physically absent regardless of these flags.
    EXTERNAL_PROVIDERS_ENABLED: bool = True
    STRICT_LOCAL_ONLY: bool = False
    ROUTING_POLICY_PATH: str = ""

    # PII/PHI redaction gate (app/services/redaction.py, docs/v2/ARCHITECTURE.md
    # Security architecture item 3). Applies only to a Class C (external)
    # provider call -- self-hosted (Class B) calls never pass through this, so
    # an on-prem/air-gapped deployment sees zero behavior change either way.
    PII_REDACTION_ENABLED: bool = True

    # Document sensitivity classification (app/services/sensitivity/). The tier
    # a document gets is what the Class C gate keys on -- confidential/privileged
    # documents are never routed to an external provider. Disabled => every
    # document is treated as DEFAULT_SENSITIVITY_TIER.
    SENSITIVITY_ENABLED: bool = True
    DEFAULT_SENSITIVITY_TIER: str = "internal"

    # Commercial provider credentials (Class C -- only used when the matching
    # provider is installed and enabled).
    GOOGLE_API_KEY: str = ""
    GENAI_MODEL: str = "gemini-flash-latest"

    # CORS
    CORS_ALLOWED_ORIGINS: list[str] = ["http://127.0.0.1:5500", "http://localhost:5500", "*"]

    # Persistence (Phase 1 re-platform: docs/v2/ARCHITECTURE.md)
    # Defaults to a local SQLite file so the app/tests run with zero external
    # services; docker-compose.yml points this at Postgres for local dev.
    DATABASE_URL: str = "sqlite:///./legalai.db"
    REDIS_URL: str = "redis://localhost:6379/0"

    # Auth (docs/v2/ROADMAP.md Phase 1). Off by default so the existing public
    # frontend keeps working with zero credentials until keys are issued and
    # this is deliberately flipped on.
    AUTH_REQUIRED: bool = False
    # Per-user identity (Phase 7, app/auth.py's Session model). How long a
    # login session token is valid before requiring a fresh login.
    SESSION_TTL_HOURS: int = 24 * 7

    # Rate limiting (per org when AUTH_REQUIRED, else per client IP). Fails
    # open (request allowed) if Redis is unreachable.
    RATE_LIMIT_PER_MINUTE: int = 60

    # Knowledge Graph (Phase 3: docs/v2/KNOWLEDGE_GRAPH.md). Memgraph speaks
    # the Bolt protocol, same as Neo4j, hence the neo4j driver. KG features
    # no-op (log + skip) if unreachable -- see app/services/kg/client.py --
    # so the rest of the app doesn't depend on this being up.
    MEMGRAPH_URI: str = "bolt://127.0.0.1:7687"  # IP literal, not "localhost" -- skips a slow dual-stack DNS/connect attempt when Memgraph isn't running
    MEMGRAPH_USER: str = ""
    MEMGRAPH_PASSWORD: str = ""
    # Collapsed data layer (Phase 7, docs/v2/ROADMAP.md "Collapsed data
    # layer" -- the laptop/single-binary profile): "kuzu" swaps the KG
    # backend for an embedded, in-process graph database (app/services/kg/
    # kuzu_client.py) needing no server at all, instead of Memgraph.
    KG_BACKEND: str = "memgraph"  # "memgraph" | "kuzu"
    KUZU_DB_PATH: str = "./kuzu_data"

    # Durable execution (Phase 7, docs/v2/ROADMAP.md "Durable execution &
    # Memory Service", app/services/durable/dbos_engine.py). Off by default
    # -- app/agents/graph.py's synchronous LangGraph execution is still the
    # default; this is an opt-in alternative orchestrator over the same
    # AGENT_REGISTRY/planner/CaseState building blocks, checkpointing each
    # agent node individually so a crashed process resumes from the last
    # completed node instead of re-running the whole analysis. DBOS has no
    # SQLite mode -- needs a real Postgres URL, unlike the rest of this
    # app's persistence layer.
    DURABLE_EXECUTION_ENABLED: bool = False
    DBOS_DATABASE_URL: str = ""

    # ---- Observability (Phase 5, docs/v2/MODEL_STACK.md "Observability") -----
    # MODEL_CALL_LOGGING persists one row per routing decision to the
    # `model_calls` table (app/db_models.py) -- the join key for the eval
    # delta report and the operator cost/latency view. Fail-soft: a DB error
    # is swallowed, never breaks a model call.
    MODEL_CALL_LOGGING: bool = True
    # OpenTelemetry: off unless an OTLP collector endpoint is configured
    # (a self-hosted Langfuse / SigNoz / Grafana Tempo). Import- and
    # connection-fail-soft -- see app/observability.py.
    OTEL_ENABLED: bool = False
    OTEL_EXPORTER_OTLP_ENDPOINT: str = ""
    OTEL_SERVICE_NAME: str = "legalai-backend"


@lru_cache
def get_settings() -> Settings:
    return Settings()
