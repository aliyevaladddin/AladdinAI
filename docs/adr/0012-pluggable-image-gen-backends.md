// NOTICE: This file is protected under RCF-PL
# ADR-0012: Pluggable Image Generation Backends (NIM FLUX sunset → DashScope)

**Status**: Accepted

**Date**: 2026-08-16

**Deciders**: aliyev, Claude

**Tags**: backend, infrastructure

## Context

`generate_image` (added with the image pipeline) was hardcoded to the hosted
NVIDIA NIM endpoint `https://ai.api.nvidia.com/v1/genai/black-forest-labs/flux.1-schnell`,
reusing the calling agent's NIM API key. On 2026-08-16 the endpoint was
verified dead: TCP connections are accepted but no response ever arrives
(65–120 s of silence, `HTTP 000` from curl, `ReadTimeout` in the app).
Neighbouring hosted image models answer `Not found for account`, and the
FLUX.1-dev page on build.nvidia.com is marked **Downloadable** — self-hosted
NIM only, which requires a ~24 GB-VRAM GPU this deployment does not have.
Hosted chat on `integrate.api.nvidia.com` remains healthy, i.e. NVIDIA
retired hosted image generation specifically.

User-visible symptom: the agent hangs for 120 s and returns an empty error.
The single-vendor hardcoding meant one dead upstream silently broke image
generation for every user, with no fallback and no fast failure.

## Decision

Make image generation **backend-pluggable** in `backend/app/services/image_gen.py`,
selected by env so a dead upstream never requires a code change:

| Env var | Meaning |
|---|---|
| `IMAGE_GEN_BACKEND` | `openai` (default) \| `dashscope` |
| `IMAGE_GEN_URL` | Submit URL (per-backend defaults in code) |
| `IMAGE_GEN_MODEL` | Model name; OpenAI-compatible gateways want it in the body |
| `IMAGE_GEN_API_KEY` | Overrides the agent's provider key — images may come from a different vendor than the chat LLM |

- The `openai` path keeps the existing one-shot POST contract (NIM `artifacts`
  or OpenAI `data[].b64_json` responses both decode).
- The `dashscope` path implements DashScope's async contract: submit →
  `task_id` → poll `/api/v1/tasks/<id>` every 2 s → `SUCCEEDED` → download the
  result URL.
- Without `IMAGE_GEN_API_KEY` the agent's own provider key is reused
  (`app.crypto.decrypt`, same path as `llm_service`) — no second key path.
- Fail-fast: generation timeout lowered 120 s → 60 s (a working backend
  answers in seconds); `ConnectError` is retried once because Codespaces DNS
  is measurably flaky (`EAI_AGAIN`).

Current working configuration: **DashScope `wan2.2-t2i-flash`** (intl host)
via the existing QWEN key. Verified end-to-end: ~6 s to a real 1.3 MB PNG.

## Consequences

### Positive
- A dead upstream is an env change, not a code change or an outage.
- Image vendor is decoupled from the chat-LLM vendor.
- Fast, descriptive errors instead of a 120 s silent hang.
- Same doctrine as ADR-0005 (unified interface hides the backend) and
  ADR-0010 (native meta-search replaced dead external dependency).

### Negative
- New deployments must configure the env vars or generation fails with a
  clear 4xx/timeout instead of "working by accident".
- Two response contracts to maintain (single-POST vs async task polling).
- DashScope results arrive with 2 s polling granularity.

### Neutral
- Tool contract unchanged: `generate_image` still returns bytes + mime and
  persists via `media_storage.save_bytes`; frontend renders identically.

## Alternatives Considered

### Alternative 1: Keep/repair the NIM hosted path
- **Description**: Retry longer or re-enable FLUX on build.nvidia.com.
- **Pros**: Zero code change.
- **Cons**: Hosted endpoint is dead (verified), self-host needs a GPU we do
  not have; waiting turns every image request into a 120 s hang.
- **Why not chosen**: No live endpoint to point at; dependency stays fragile.

### Alternative 2: Full `ImageProvider` model + UI + fallback chain
- **Description**: Image backends as first-class providers (like
  `LLMProvider`): DB-backed, UI-configurable, `resolve_image_provider()`
  priority chain with circuit breaker.
- **Pros**: The durable product-level fix — users never see this failure class.
- **Cons**: A full feature (model, migration, UI, resolver), too slow as an
  immediate unblock.
- **Why not chosen (yet)**: Approved as phase 2; this ADR's env contract is
  its stepping stone and stays compatible with it.

### Alternative 3: Per-user third-party keys (OpenAI etc.)
- **Description**: Each user supplies their own image-API key.
- **Pros**: Maximum choice.
- **Cons**: Requires per-user key management we don't have today.
- **Why not chosen**: Out of scope for the unblock; covered later by
  Alternative 2.

## Implementation Notes

- `backend/app/services/image_gen.py` — backend dispatch + DashScope adapter;
  `_decode_image` unchanged (already understood both response shapes).
- LLM-side resilience landed the same day: `llm_service` retries
  `TransportError` up to 3× before the first streamed byte; error messages
  always carry the exception class (`type(e).__name__`).
- Verified: live DashScope task round-trip, end-to-end PNG generation,
  `ruff` clean, 279 backend tests green.

## References

- [ADR-0005](0005-media-storage-abstraction.md) — unified-interface doctrine
- [ADR-0010](0010-native-agent-meta-search.md) — replacing a dead external dependency
- `backend/app/services/image_gen.py`, `backend/app/tools/image.py`
