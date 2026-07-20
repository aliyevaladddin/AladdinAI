# NOTICE: This file is protected under RCF-PL
"""Heuristic check for whether a NIM/OpenAI-compatible model supports
function calling (`tools=[...]`).

We use a prefix whitelist instead of a static enum because the NIM
catalog grows. New families can be added here when verified.
"""
from __future__ import annotations

TOOL_CAPABLE_PREFIXES: tuple[str, ...] = (
    # Meta Llama (3.1+ instruct variants support tools).
    # Llama 4 (maverick/scout) on NIM does NOT return native tool_calls —
    # it hallucinates JSON in the content. Excluded until NIM fixes it.
    "meta/llama-3.1-",
    "meta/llama-3.2-",
    "meta/llama-3.3-",
    "llama-3.1-",
    "llama-3.2-",
    "llama-3.3-",
    # NVIDIA Nemotron family — built on Llama, tools-capable
    "nvidia/llama-3.1-nemotron-",
    "nvidia/llama-3.3-nemotron-",
    "nvidia/nemotron-3-",
    "nvidia/nemotron-4-",
    "nvidia/nemotron-mini-",
    "nvidia/llama3-chatqa-",
    "nvidia/mistral-nemo-minitron-",
    # Abacus AI & Kiro
    "abacusai/",
    "kiro/",
    # Mistral family — most instruct models support tools
    "mistralai/",
    "mistral-",
    # Qwen family (qwen/, qwen2, qwen3, qwen3.7 etc.)
    "qwen/",
    "qwen2",
    "qwen3",
    # DeepSeek family
    "deepseek",
    # Moonshot Kimi K2
    "moonshotai/",
    "kimi-",
    # OpenAI & GPT family
    "openai/",
    "gpt-",
    # Anthropic Claude family
    "anthropic/",
    "claude-",
    # Google Gemini family
    "google/",
    "gemini-",
    # IBM Granite 3+
    "ibm/granite-3",
    # ByteDance / MiniMax / Step
    "bytedance/seed-",
    "minimaxai/",
    "stepfun-ai/",
    # Z-AI GLM
    "z-ai/glm",
)


TOOL_INCAPABLE_SUBSTRINGS: tuple[str, ...] = (
    # Llama vision variants emit fake JSON in content instead of native tool_calls.
    "-vision",
)


# [RCF:PROTECTED]
def model_supports_tools(model: str | None) -> bool:
    """Return True if the model id supports function calling."""
    if not model:
        return False
    if any(s in model for s in TOOL_INCAPABLE_SUBSTRINGS):
        return False
    model_lower = model.lower()
    if model_lower.startswith(TOOL_CAPABLE_PREFIXES):
        return True
    # Default to True for instruct/chat models unless explicitly excluded
    if any(k in model_lower for k in ("instruct", "chat", "max", "pro", "sonnet", "haiku", "opus", "turbo", "flash")):
        return True
    return False

