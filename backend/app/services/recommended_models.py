"""Recommended-model catalog for safety checks, gates, and extraction.

For each role we keep an *ordered* list of candidate model identifiers.
Resolution walks the list and returns the first candidate that is actually
present in the agent provider's `models_available` catalog.

Matching is substring-based (case-insensitive) because model IDs differ
slightly across NIM endpoints — e.g. `nvidia/llama-3.1-nemoguard-8b-content-safety`
on NIM hosted vs `meta/llama-guard-3-8b` on a local NIM. The substring needs
to be specific enough to avoid false positives (we never match on bare
"llama" or "guard").

Update this file (NOT the database) to add new recommendations — it's the
single source of truth. The resolver returns `None` if nothing matches,
which the UI renders as "no recommendation available for this provider".
"""
from __future__ import annotations

# Order matters: we return the first candidate that the provider exposes.
SAFETY_RECOMMENDATIONS: dict[str, list[str]] = {
    "ingress": [
        "llama-3.1-nemoguard-8b-content-safety",
        "llama-guard-3-8b",
        "llama-guard-3",
        "llama-guard",
        "shieldgemma",
    ],
    "egress": [
        "llama-3.1-nemoguard-8b-content-safety",
        "llama-guard-3-8b",
        "llama-guard-3",
        "llama-guard",
        "shieldgemma",
    ],
    "pii": [
        "gliner-pii",
        "gliner",
        "piiranha",
        "deberta-pii",
    ],
}

GATE_RECOMMENDATIONS: dict[str, list[str]] = {
    "handoff": [
        "llama-3.1-nemoguard-8b-topic-control",
        "nemoguard-8b-topic-control",
        "topic-control",
        "mistral-nemo-12b-instruct",
        "llama-3.1-8b-instruct",
    ],
    "memory_write": [
        "llama-3.1-nemoguard-8b-topic-control",
        "nemoguard-8b-topic-control",
        "llama-3.2-3b-instruct",
        "llama-3.1-8b-instruct",
        "mistral-7b-instruct",
    ],
    "recall_rerank": [
        "llama-3.2-nv-rerankqa",
        "rerankqa",
        "bge-reranker",
        "llama-3.2-3b-instruct",
        "llama-3.1-8b-instruct",
    ],
}

EXTRACTION_RECOMMENDATIONS: list[str] = [
    "llama-3.1-70b-instruct",
    "llama-3.1-8b-instruct",
    "llama-3.2-3b-instruct",
    "mistral-nemo-12b-instruct",
    "mistral-7b-instruct",
]


def _match(catalog: list[str], candidate: str) -> str | None:
    """Return the catalog entry whose id contains `candidate` (case-insensitive)."""
    needle = candidate.lower()
    for entry in catalog:
        if not isinstance(entry, str):
            continue
        if needle in entry.lower():
            return entry
    return None


def resolve_one(catalog: list[str], candidates: list[str]) -> str | None:
    """First candidate (in order) that has a substring match in the catalog."""
    if not catalog:
        return None
    for cand in candidates:
        hit = _match(catalog, cand)
        if hit:
            return hit
    return None


def resolve_safety(catalog: list[str]) -> dict[str, str | None]:
    return {check: resolve_one(catalog, cands) for check, cands in SAFETY_RECOMMENDATIONS.items()}


def resolve_gates(catalog: list[str]) -> dict[str, str | None]:
    return {gate: resolve_one(catalog, cands) for gate, cands in GATE_RECOMMENDATIONS.items()}


def resolve_extraction(catalog: list[str]) -> str | None:
    return resolve_one(catalog, EXTRACTION_RECOMMENDATIONS)
