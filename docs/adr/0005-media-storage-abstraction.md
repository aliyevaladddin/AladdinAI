// NOTICE: This file is protected under RCF-PL
# ADR-0005: Unified Media Storage Abstraction (Local FS vs MongoDB GridFS)

**Status**: Accepted

**Date**: 2026-06-04

**Deciders**: Aladdin Aliyev

**Tags**: backend, storage, mongodb, media

## Context

AladdinAI handles binary media — uploaded images for vision, generated images,
voice clips, and document attachments. The original implementation wrote files to
the local filesystem. That breaks on stateless/ephemeral deploys (e.g. Render),
where the local disk is not persistent and is not shared across instances.

We need media that survives restarts and is reachable from any backend instance,
without forcing every self-hosted operator onto the same backend.

## Decision

Introduce a **unified media storage interface** that auto-switches between two
backends, chosen per user:

1. `services/media_mongo.py` — MongoDB **GridFS** backend (motor, async).
2. `services/media_storage.py` — unified interface that resolves the active
   backend in priority order:
   1. user's `system_settings.media_storage_backend`
   2. `STORAGE_BACKEND` env var
   3. default `local`

Call sites (`vision.py`, `image.py`) go through the unified interface and never
touch a concrete backend directly.

## Consequences

### Positive
- Media survives restarts and is shared across instances when GridFS is selected.
- Per-user choice: a local dev keeps files on disk; a cloud tenant uses GridFS.
- Single integration surface — call sites are backend-agnostic.
- Reuses the MongoDB Atlas cluster already required for vector memory; no new
  storage service to provision.

### Negative
- GridFS stores blobs in MongoDB — large/heavy media inflates the cluster and
  competes with the vector workload.
- Two code paths to keep behaviorally identical.

### Neutral
- GridFS operations in motor 3.7.1 (`upload_from_stream` / `open_download_stream`)
  are **async and must be awaited** — a common source of false "this is sync" review
  findings. Verified async.

## Alternatives Considered

### Alternative 1: Local filesystem only
- **Description**: Keep writing to disk.
- **Pros**: Simplest; zero dependencies.
- **Cons**: Lost on ephemeral deploys; not shared across instances.
- **Why not chosen**: Fails the core "works on Render / multi-instance" requirement.

### Alternative 2: External object store (S3 / GCS / R2)
- **Description**: Push media to a cloud object store.
- **Pros**: Purpose-built for blobs, cheap at scale, CDN-friendly.
- **Cons**: New required dependency and credentials for every operator; conflicts
  with the sovereign / self-hosted, bring-your-own-infra posture.
- **Why not chosen**: Adds an external dependency the platform deliberately avoids;
  can be added later as a third backend behind the same interface.

## Implementation Notes

- `system_settings` table carries the per-user `media_storage_backend` choice.
- Adding a future backend (e.g. S3) = implement the interface + extend the resolver
  in `media_storage.py`; call sites need no changes.

## References

- [ADR-0002: MongoDB vs Postgres](0002-mongodb-vs-postgres.md)
- `backend/app/services/media_storage.py`, `backend/app/services/media_mongo.py`
