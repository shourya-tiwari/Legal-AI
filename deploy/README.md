# Deployment manifests (docs/v2/ROADMAP.md Phase 7 "Build & supply chain")

Two parallel representations of the same target state, kept in sync by hand:

- **`kustomize/`** -- plain Kubernetes YAML + Kustomize overlays. **Verified**: every target (`base`, `overlays/on-prem`, `overlays/cloud`, `overlays/gpu`) renders successfully via `kubectl kustomize <dir>` (kubectl's built-in Kustomize support needs no cluster to do this — it's pure client-side YAML rendering). Confirmed the on-prem overlay's `secret-patch.yaml` merges correctly (`MEMGRAPH_URI`/`REDIS_URL` overridden, everything else untouched), the cloud overlay's image/config patches apply, and the gpu overlay's two `NetworkPolicy` objects (base + inference-stack) both render and are additive, not conflicting.
- **`helm/legalai/`** -- a chart covering the same three profiles via `values.yaml`/`values-cloud.yaml`/`values-gpu.yaml`, plus the one thing plain Kustomize structurally can't do: compose a `DATABASE_URL` that embeds a templated password (`templates/secret.yaml`). **Not verified** — no `helm` binary is installed in the environment this was authored in, so `helm lint`/`helm template` have not been run. Written carefully against standard Helm/Sprig template syntax, but treat it as unreviewed-by-tooling until it's actually rendered somewhere `helm` exists.

## What's real vs. not, precisely

| Layer | Written | Rendered/validated | Actually deployed |
|---|---|---|---|
| `backend/Dockerfile` (`core` + `external` profiles) | Yes | Yes — both images built with `docker build`, confirmed the `core` image genuinely has no `google-genai` installed and that `app.main.app` imports inside the container | No registry to push to |
| `scripts/check_sbom_allowlist.py` | Yes | Yes — run against both built images; correctly passes `core`, correctly fails when checked against `external` under the `core` policy (the negative-control test) | N/A (it's a script, not a deployment) |
| Kustomize (`base`, `on-prem`, `cloud`, `gpu`) | Yes | Yes — `kubectl kustomize` on all four | No cluster in this environment to `kubectl apply` against |
| Helm chart | Yes | No — no `helm` binary here | No |
| `zarf.yaml`, `Kitfile` (repo root) | Yes | No — no `zarf`/`kit` CLI here | No |
| `infra/opentofu/` | Yes | No — no `terraform`/`tofu` CLI here | No |
| `NetworkPolicy` manifests (egress enforcement) | Yes | Rendered correctly, but a `NetworkPolicy` is a no-op unless the cluster's CNI implements it (Calico, Cilium, ...) — no cluster here to confirm one does | No |
| CI `sbom-and-image` job (`.github/workflows/backend-tests.yml`) | Yes | The `docker build`/`docker run`/allowlist steps mirror commands already run and verified locally; the Syft/Trivy/cosign steps use their standard published GitHub Actions but have not been executed here (no CI runner) | N/A |

This mirrors the same distinction `docs/v2/TASKS.md`'s per-item annotations make everywhere else in this project: "written and tested" is a different, stronger claim than "written," and both are different again from "actually running against a real target." None of the artifacts above should be read as claiming the third.
