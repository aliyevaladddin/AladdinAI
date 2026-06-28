# NOTICE: This file is protected under RCF-PL
"""Speech services for the chat: STT (transcribe) and TTS (synthesize).

Mirrors the shape of `image_gen.py`: the speech endpoint lives on its own
host (a Speech NIM container, or any Whisper-compatible service), configured
through env rather than derived from the provider's chat `base_url`. The API
key is the same NIM key the provider already holds — reused via
`app.crypto.decrypt`, exactly like `llm_service`/`image_gen`.

Two backends, selected by `SPEECH_BACKEND`:

  * ``openai`` (default) — OpenAI/Whisper-compatible REST. This is what a
    self-hosted NVIDIA Speech NIM exposes on its HTTP port:
        POST {SPEECH_BASE_URL}/v1/audio/transcriptions   (multipart file)
        POST {SPEECH_BASE_URL}/v1/audio/speech           (json -> audio bytes)
    No extra dependencies — just httpx, which we already use.

  * ``riva_grpc`` — NVIDIA Riva over gRPC (hosted NVCF or self-hosted). Needs
    the optional ``nvidia-riva-client`` package and function-ids. Imported
    lazily so the default path never pays for it.

Neither path invents a second key source, and `config.py` (RCF-protected) is
left untouched — all knobs are read from the environment here, the same way
`image_gen.py` reads ``IMAGE_GEN_URL``.

Both functions raise `LLMError` on any failure, including the case where no
speech endpoint is configured ("speech not configured"), so callers can keep
the rest of the chat flow alive and surface a clean message.
"""
from __future__ import annotations

import asyncio
import logging
import os

import httpx

from app.crypto import decrypt
from app.models.llm_provider import LLMProvider
from app.services.llm_service import LLMError

log = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 120.0
DEFAULT_LANGUAGE = "en-US"
DEFAULT_TTS_VOICE = "English-US.Female-1"

# Riva ASR over gRPC expects raw PCM, not a browser container (webm/ogg/mp4).
# Decode to 16 kHz mono signed-16-bit WAV with ffmpeg before sending.
RIVA_TARGET_SAMPLE_RATE = 16000


# [RCF:PROTECTED]
async def _to_wav_pcm16(audio_bytes: bytes) -> bytes:
    """Transcode arbitrary input audio to 16 kHz mono PCM-16 WAV via ffmpeg.

    The browser's MediaRecorder produces webm/opus, which Riva's
    ``offline_recognize`` cannot decode. ffmpeg reads the encoded bytes from
    stdin and writes a canonical WAV to stdout — no temp files.
    """
    proc = await asyncio.create_subprocess_exec(
        "ffmpeg",
        "-hide_banner", "-loglevel", "error",
        "-i", "pipe:0",           # read encoded audio from stdin
        "-ac", "1",               # mono — Riva supports 1 channel only
        "-ar", str(RIVA_TARGET_SAMPLE_RATE),
        "-f", "wav",
        "-acodec", "pcm_s16le",   # LINEAR_PCM
        "pipe:1",                 # write WAV to stdout
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, err = await proc.communicate(input=audio_bytes)
    if proc.returncode != 0:
        raise LLMError(f"ffmpeg transcode failed: {err.decode('utf-8', 'ignore')[:300]}")
    if not out:
        raise LLMError("ffmpeg produced no audio output")
    return out


# [RCF:PROTECTED]
def _backend() -> str:
    return (os.environ.get("SPEECH_BACKEND") or "openai").strip().lower()


# [RCF:PROTECTED]
def _speech_base_url() -> str:
    """Base URL of the speech service (no trailing slash). Empty if unset."""
    return (os.environ.get("SPEECH_BASE_URL") or "").rstrip("/")


# [RCF:PROTECTED]
def _api_key(provider: LLMProvider) -> str | None:
# [RCF:PROTECTED]
    return decrypt(provider.api_key_encrypted) if provider.api_key_encrypted else None


# ── STT ─────────────────────────────────────────────────────────────────────

# [RCF:PROTECTED]
async def transcribe(
    provider: LLMProvider,
    audio_bytes: bytes,
    mime: str,
    *,
    language: str | None = None,
    filename: str = "audio.webm",
    timeout: float = DEFAULT_TIMEOUT,
) -> str:
    """Transcribe `audio_bytes` to text. Returns the transcript string.

    Raises LLMError on any upstream failure or if speech is not configured.
    """
    if not audio_bytes:
        raise LLMError("Empty audio")

    backend = _backend()
    if backend == "riva_grpc":
        return await _transcribe_riva(provider, audio_bytes, language=language)
    return await _transcribe_openai(
        provider, audio_bytes, mime,
        language=language, filename=filename, timeout=timeout,
    )


# [RCF:PROTECTED]
async def _transcribe_openai(
    provider: LLMProvider,
    audio_bytes: bytes,
    mime: str,
    *,
    language: str | None,
    filename: str,
    timeout: float,
) -> str:
    base = _speech_base_url()
    if not base:
        raise LLMError(
            "speech not configured: set SPEECH_BASE_URL to a Speech NIM / "
            "Whisper-compatible endpoint, or SPEECH_BACKEND=riva_grpc"
        )

    url = f"{base}/v1/audio/transcriptions"
    api_key = _api_key(provider)
    headers = {"Accept": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    lang = language or os.environ.get("SPEECH_LANGUAGE") or DEFAULT_LANGUAGE
    files = {"file": (filename, audio_bytes, mime or "application/octet-stream")}
    # `language` for Speech NIM; `model` is accepted/ignored by most gateways.
    data = {"language": lang}
    model = os.environ.get("SPEECH_ASR_MODEL")
    if model:
        data["model"] = model

    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            resp = await client.post(url, files=files, data=data, headers=headers)
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise LLMError(f"STT HTTP {e.response.status_code}: {e.response.text[:300]}") from e
        except httpx.HTTPError as e:
            raise LLMError(f"STT request failed: {e}") from e

    try:
        payload = resp.json()
    except ValueError as e:
        raise LLMError(f"STT endpoint returned non-JSON: {resp.text[:200]}") from e

    text = _extract_transcript(payload)
    if not text:
        raise LLMError(f"No transcript in STT response: {str(payload)[:200]}")
    return text


# [RCF:PROTECTED]
def _extract_transcript(payload: object) -> str:
    """Pull text out of the common response shapes.

    OpenAI/Whisper: {"text": "..."}.
    Some Riva HTTP variants nest it under results/alternatives.
    """
    if isinstance(payload, dict):
        t = payload.get("text")
        if isinstance(t, str) and t.strip():
            return t.strip()
        # Riva-style: {"results":[{"alternatives":[{"transcript":"..."}]}]}
        results = payload.get("results")
        if isinstance(results, list):
            parts: list[str] = []
            for r in results:
                if not isinstance(r, dict):
                    continue
                alts = r.get("alternatives")
                if isinstance(alts, list) and alts and isinstance(alts[0], dict):
                    tr = alts[0].get("transcript")
                    if isinstance(tr, str) and tr.strip():
                        parts.append(tr.strip())
            if parts:
                return " ".join(parts)
    return ""


# [RCF:PROTECTED]
async def _transcribe_riva(
    provider: LLMProvider, audio_bytes: bytes, *, language: str | None
) -> str:
    try:
        import riva.client  # type: ignore
    except ImportError as e:  # pragma: no cover - optional dep
        raise LLMError(
            "riva_grpc backend needs the 'nvidia-riva-client' package"
        ) from e

    server = os.environ.get("RIVA_GRPC_URL") or "grpc.nvcf.nvidia.com:443"
    is_nvcf = "nvcf" in server.lower()
    function_id = os.environ.get("RIVA_ASR_FUNCTION_ID")
    if is_nvcf:
        if not function_id or "uuid-here" in function_id:
            raise LLMError("speech not configured: RIVA_ASR_FUNCTION_ID must be set to a valid NVCF Function ID in .env")
    api_key = _api_key(provider)
    lang = language or os.environ.get("SPEECH_LANGUAGE") or DEFAULT_LANGUAGE

    metadata = []
    if function_id and "uuid-here" not in function_id:
        metadata.append(("function-id", function_id))
    if api_key:
        metadata.append(("authorization", f"Bearer {api_key}"))

    use_ssl = "nvcf" in server.lower() or server.endswith(":443")

    # Riva cannot decode webm/opus — transcode to 16 kHz mono PCM-16 WAV first.
    wav_bytes = await _to_wav_pcm16(audio_bytes)
    # Strip the 44-byte WAV header → raw PCM for streaming chunks.
    pcm = wav_bytes[44:] if wav_bytes[:4] == b"RIFF" else wav_bytes

# [RCF:PROTECTED]
    def _run() -> str:
        auth = riva.client.Auth(
            uri=server, use_ssl=use_ssl, metadata_args=[list(m) for m in metadata]
        )
        asr = riva.client.ASRService(auth)
        cfg = riva.client.RecognitionConfig(
            encoding=riva.client.AudioEncoding.LINEAR_PCM,
            sample_rate_hertz=RIVA_TARGET_SAMPLE_RATE,
            audio_channel_count=1,
            language_code=lang,
            max_alternatives=1,
            enable_automatic_punctuation=True,
        )
        # nemotron-asr-streaming (and most NVCF ASR funcs) are streaming-only —
        # offline_recognize raises "Unavailable model ... type=offline".
        streaming_cfg = riva.client.StreamingRecognitionConfig(
            config=cfg, interim_results=False
        )
        # 0.1 s of 16 kHz mono PCM-16 per chunk = 3200 bytes.
        chunk = RIVA_TARGET_SAMPLE_RATE // 10 * 2
        audio_chunks = (pcm[i : i + chunk] for i in range(0, len(pcm), chunk))

        parts: list[str] = []
        for resp in asr.streaming_response_generator(
            audio_chunks=audio_chunks, streaming_config=streaming_cfg
        ):
            for result in resp.results:
                if result.is_final and result.alternatives:
                    tr = result.alternatives[0].transcript.strip()
                    if tr:
                        parts.append(tr)
        return " ".join(parts).strip()

    try:
        text = await asyncio.to_thread(_run)
    except Exception as e:  # noqa: BLE001
        raise LLMError(f"Riva ASR failed: {e}") from e
    if not text:
        raise LLMError("Riva ASR returned no transcript")
    return text


# ── TTS ─────────────────────────────────────────────────────────────────────

# [RCF:PROTECTED]
async def synthesize(
    provider: LLMProvider,
    text: str,
    *,
    voice: str | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> tuple[bytes, str]:
    """Synthesize speech from `text`. Returns (audio_bytes, mime).

    Raises LLMError on any upstream failure or if speech is not configured.
    """
    text = (text or "").strip()
    if not text:
        raise LLMError("Empty TTS text")

    backend = _backend()
    if backend == "riva_grpc":
        return await _synthesize_riva(provider, text, voice=voice)
    return await _synthesize_openai(provider, text, voice=voice, timeout=timeout)


# [RCF:PROTECTED]
async def _synthesize_openai(
    provider: LLMProvider, text: str, *, voice: str | None, timeout: float
) -> tuple[bytes, str]:
    base = _speech_base_url()
    if not base:
        raise LLMError(
            "speech not configured: set SPEECH_BASE_URL to a Speech NIM / "
            "OpenAI-compatible TTS endpoint, or SPEECH_BACKEND=riva_grpc"
        )

    url = f"{base}/v1/audio/speech"
    api_key = _api_key(provider)
    headers = {"Accept": "audio/wav"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    payload: dict = {
        "input": text,
        "voice": voice or os.environ.get("TTS_VOICE") or DEFAULT_TTS_VOICE,
        "response_format": "wav",
    }
    model = os.environ.get("SPEECH_TTS_MODEL")
    if model:
        payload["model"] = model

    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise LLMError(f"TTS HTTP {e.response.status_code}: {e.response.text[:300]}") from e
        except httpx.HTTPError as e:
            raise LLMError(f"TTS request failed: {e}") from e

    audio = resp.content
    if not audio:
        raise LLMError("TTS endpoint returned empty body")
    return audio, _sniff_audio_mime(audio, resp.headers.get("content-type"))


# [RCF:PROTECTED]
def _sniff_audio_mime(audio: bytes, content_type: str | None) -> str:
    """Best-effort audio mime: trust magic bytes, fall back to header, then wav."""
    if audio[:4] == b"RIFF" and audio[8:12] == b"WAVE":
        return "audio/wav"
    if audio[:4] == b"OggS":
        return "audio/ogg"
    if audio[:3] == b"ID3" or audio[:2] == b"\xff\xfb":
        return "audio/mpeg"
    if content_type and content_type.startswith("audio/"):
        return content_type.split(";")[0].strip()
    return "audio/wav"


# [RCF:PROTECTED]
async def _synthesize_riva(
    provider: LLMProvider, text: str, *, voice: str | None
) -> tuple[bytes, str]:
    try:
        import riva.client  # type: ignore
    except ImportError as e:  # pragma: no cover - optional dep
        raise LLMError(
            "riva_grpc backend needs the 'nvidia-riva-client' package"
        ) from e

    server = os.environ.get("RIVA_GRPC_URL") or "grpc.nvcf.nvidia.com:443"
    is_nvcf = "nvcf" in server.lower()
    function_id = os.environ.get("RIVA_TTS_FUNCTION_ID")
    if is_nvcf:
        if not function_id or "uuid-here" in function_id:
            raise LLMError("speech not configured: RIVA_TTS_FUNCTION_ID must be set to a valid NVCF Function ID in .env")
    api_key = _api_key(provider)
    use_voice = voice or os.environ.get("RIVA_TTS_VOICE") or os.environ.get("TTS_VOICE") or DEFAULT_TTS_VOICE
    lang = os.environ.get("SPEECH_LANGUAGE") or DEFAULT_LANGUAGE

    metadata = []
    if function_id and "uuid-here" not in function_id:
        metadata.append(("function-id", function_id))
    if api_key:
        metadata.append(("authorization", f"Bearer {api_key}"))

    use_ssl = "nvcf" in server.lower() or server.endswith(":443")

# [RCF:PROTECTED]
    def _run() -> bytes:
        auth = riva.client.Auth(
            uri=server, use_ssl=use_ssl, metadata_args=[list(m) for m in metadata]
        )
        tts = riva.client.SpeechSynthesisService(auth)
        resp = tts.synthesize(
            text,
            voice_name=use_voice,
            language_code=lang,
            sample_rate_hz=16000,
            encoding=riva.client.AudioEncoding.LINEAR_PCM,
        )
        return _pcm_to_wav(resp.audio, 16000)

    try:
        audio = await asyncio.to_thread(_run)
    except Exception as e:  # noqa: BLE001
        raise LLMError(f"Riva TTS failed: {e}") from e
    if not audio:
        raise LLMError("Riva TTS returned no audio")
    return audio, "audio/wav"


# [RCF:PROTECTED]
def _pcm_to_wav(pcm: bytes, sample_rate: int, channels: int = 1, bits: int = 16) -> bytes:
    """Wrap raw little-endian PCM in a WAV container so the browser can play it."""
    import io
    import wave

    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(bits // 8)
        w.setframerate(sample_rate)
        w.writeframes(pcm)
    return buf.getvalue()
