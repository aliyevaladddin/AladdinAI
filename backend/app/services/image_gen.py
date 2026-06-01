"""Text-to-image generation via NVIDIA NIM (FLUX.1-schnell by default).

The image endpoint lives on a different host/path than chat completions
(`ai.api.nvidia.com/v1/genai/...` vs the provider's chat `base_url`), so the
URL is configured independently through `IMAGE_GEN_URL` rather than derived
from `provider.base_url`. The API key, however, is the same NIM key the
provider already holds — we reuse `app.crypto.decrypt` exactly like
`llm_service` does, never inventing a second key path.

`generate_image_bytes` returns raw image bytes + mime; callers persist them
with `media_service.save_bytes` and hand them back as outgoing attachments,
the same contract `send_image` uses.
"""
from __future__ import annotations

import base64
import logging
import os

import httpx

from app.crypto import decrypt
from app.models.llm_provider import LLMProvider
from app.services.llm_service import LLMError

log = logging.getLogger(__name__)

# Hosted NIM FLUX.1-schnell — fast (few-step) text-to-image. Overridable.
DEFAULT_IMAGE_GEN_URL = (
    "https://ai.api.nvidia.com/v1/genai/black-forest-labs/flux.1-schnell"
)
DEFAULT_STEPS = 4  # FLUX.1-schnell is distilled for very few steps
DEFAULT_TIMEOUT = 120.0


def _decode_image(data: dict) -> bytes:
    """Pull base64 image bytes out of either the native NIM `artifacts`
    response or the OpenAI-compatible `data[...].b64_json` response."""
    # Native NIM genai: {"artifacts": [{"base64": "..."}]}
    artifacts = data.get("artifacts")
    if isinstance(artifacts, list) and artifacts:
        b64 = artifacts[0].get("base64")
        if b64:
            return base64.b64decode(b64)
    # OpenAI-compatible /v1/images/generations: {"data": [{"b64_json": "..."}]}
    items = data.get("data")
    if isinstance(items, list) and items:
        b64 = items[0].get("b64_json")
        if b64:
            return base64.b64decode(b64)
    raise LLMError(f"No image in response: {str(data)[:200]}")


def _sniff_mime(img: bytes) -> str:
    """Detect image mime from magic bytes — NIM may return PNG or JPEG."""
    if img[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if img[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if img[:4] == b"RIFF" and img[8:12] == b"WEBP":
        return "image/webp"
    return "image/png"  # sensible default; save_bytes maps it to .png


async def generate_image_bytes(
    provider: LLMProvider,
    prompt: str,
    *,
    steps: int | None = None,
    seed: int = 0,
    timeout: float = DEFAULT_TIMEOUT,
) -> tuple[bytes, str]:
    """Generate an image from `prompt` via NIM. Returns (image_bytes, mime).

    Raises LLMError on any upstream/decoding failure.
    """
    prompt = (prompt or "").strip()
    if not prompt:
        raise LLMError("Empty image prompt")

    url = os.environ.get("IMAGE_GEN_URL", DEFAULT_IMAGE_GEN_URL)
    api_key = decrypt(provider.api_key_encrypted) if provider.api_key_encrypted else None

    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    payload: dict = {
        "prompt": prompt,
        "steps": steps if steps is not None else DEFAULT_STEPS,
        "seed": seed,
    }
    # Optional model override (some genai gateways want it in the body).
    model = os.environ.get("IMAGE_GEN_MODEL")
    if model:
        payload["model"] = model

    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise LLMError(f"HTTP {e.response.status_code}: {e.response.text[:300]}") from e
        except httpx.HTTPError as e:
            raise LLMError(str(e)) from e

    try:
        data = resp.json()
    except ValueError as e:
        raise LLMError(f"Image endpoint returned non-JSON: {resp.text[:200]}") from e

    img_bytes = _decode_image(data)
    return img_bytes, _sniff_mime(img_bytes)
