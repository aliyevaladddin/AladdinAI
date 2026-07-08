// NOTICE: This file is protected under RCF-PL
# ADR-0007: Voice Pipeline on NVIDIA Riva with ffmpeg Transcoding

**Status**: Accepted

**Date**: 2026-06-27

**Deciders**: Aladdin Aliyev

**Tags**: backend, voice, asr, tts, nvidia-riva, dependencies

## Context

We added voice: users speak to agents in the browser and optionally hear replies.
The browser's `MediaRecorder` emits `audio/webm` (Opus). NVIDIA Riva ASR does not
decode webm — its `AudioEncoding` proto accepts LINEAR_PCM / FLAC / MULAW /
OGGOPUS / ALAW (no webm) and is mono-only. Feeding webm produced
`StatusCode.INTERNAL: failed to open stateful work request`.

Separately, the Riva model actually deployed on NVCF was a **streaming-only**
ASR model (`nemotron-asr-streaming`), while the first implementation called the
**offline** `offline_recognize` API — yielding
`INVALID_ARGUMENT: Unavailable model ... type=offline`.

We needed a voice path that is sovereign (routes through NIM/Riva, no third-party
speech API) and actually works against the deployed model.

## Decision

Build the voice pipeline as **opt-in** (`SPEECH_BACKEND`, default `openai`;
`riva_grpc` selects Riva) with two key adaptations:

1. **Transcode on ingress** — `_to_wav_pcm16()` in `speech.py` shells out to
   `ffmpeg` (stdin→stdout) to convert browser webm/Opus into 16 kHz mono PCM-16 WAV.
   `ffmpeg` becomes a **system dependency** of the project (added to
   `backend/Dockerfile` and `Dockerfile.prod`).
2. **Use the streaming ASR API** — `_transcribe_riva` uses
   `streaming_response_generator` with `StreamingRecognitionConfig(interim_results=False)`,
   sending raw PCM (WAV header stripped, `[44:]`) in ~3200-byte chunks (0.1 s of
   16 kHz mono) and collecting `result.is_final`.

Config: one host `RIVA_GRPC_URL=grpc.nvcf.nvidia.com:443` for the whole cloud;
ASR and TTS differ only by Function ID (`RIVA_ASR_FUNCTION_ID` /
`RIVA_TTS_FUNCTION_ID`). The API key comes from the connected NVIDIA NIM provider
(`nvapi-...`), not a separate env var. `SPEECH_LANGUAGE` must match the deployed
model's language (Riva truncates `en-US`→`en`).

## Consequences

### Positive
- Voice in/out without any third-party speech API — sovereign by default.
- ASR confirmed working live end-to-end after the four fixes below.
- Voice is opt-in, so default deploys are unaffected.

### Negative
- **`ffmpeg` is now a required system dependency** — must be present in every
  image/host that runs voice.
- Tightly coupled to the *streaming* Riva API and the deployed model's encoding,
  sample rate, and language. A different deployed model may need config changes.

### Neutral
- TTS (`RIVA_TTS_FUNCTION_ID`, e.g. voice `Russian-RU.Female-1`) is a separate
  function and must be verified independently when Voice Reply is enabled.

## Alternatives Considered

### Alternative 1: Offline Riva recognition (`offline_recognize`)
- **Description**: Send a whole WAV in one offline request.
- **Pros**: Simpler code; no chunking.
- **Cons**: The deployed NVCF model is streaming-only → `Unavailable model`.
- **Why not chosen**: Doesn't match the deployed model.

### Alternative 2: Decode webm/Opus in-process (Python lib)
- **Description**: Use a Python audio lib instead of shelling to ffmpeg.
- **Pros**: No external binary.
- **Cons**: Heavier/less reliable Opus support; ffmpeg is the de-facto standard.
- **Why not chosen**: ffmpeg is robust and already common in containers.

### Alternative 3: Third-party speech API (e.g. OpenAI Whisper endpoint)
- **Description**: Offload ASR/TTS to an external provider.
- **Pros**: No transcoding/model-deploy concerns.
- **Cons**: Breaks the sovereign posture; external dependency and data egress.
- **Why not chosen** (as default): kept as the *other* `SPEECH_BACKEND` option
  (`openai`-compatible) but Riva is the sovereign path.

## Implementation Notes

**Full recipe for working voice (all four required):**
1. `nvidia-riva-client` installed in the active Python env.
2. `ffmpeg` present (webm→PCM transcode).
3. A real NVCF Function ID set (`RIVA_ASR_FUNCTION_ID`, not the `your-asr` placeholder).
4. The **streaming** ASR API path (not offline).

## References

- `backend/app/services/speech.py`, `backend/Dockerfile`, `backend/Dockerfile.prod`
