"""Heuristic check for whether a NIM/OpenAI-compatible model supports
function calling (`tools=[...]`).

We use a prefix whitelist instead of a static enum because the NIM
catalog grows. New families can be added here when verified.
"""
from __future__ import annotations

TOOL_CAPABLE_PREFIXES: tuple[str, ...] = (
    # Meta Llama (3.1+ instruct variants support tools)
    "meta/llama-3.1-",
    "meta/llama-3.2-",
    "meta/llama-3.3-",
    "meta/llama-4-",
    # NVIDIA Nemotron family — built on Llama, tools-capable
    "nvidia/llama-3.1-nemotron-",
    "nvidia/llama-3.3-nemotron-",
    "nvidia/nemotron-3-",
    "nvidia/nemotron-4-",
    "nvidia/nemotron-mini-",
    "nvidia/llama3-chatqa-",
    "nvidia/mistral-nemo-minitron-",
    # Mistral family — most instruct models support tools
    "mistralai/mistral-large",
    "mistralai/mistral-medium",
    "mistralai/mistral-small",
    "mistralai/ministral-",
    "mistralai/devstral-",
    "mistralai/mistral-nemotron",
    "mistralai/mixtral-8x22b-instruct",
    # Qwen 2.5+ instruct
    "qwen/qwen2.5-",
    "qwen/qwen3-",
    "qwen/qwen3.5-",
    # DeepSeek v4
    "deepseek-ai/deepseek-v4",
    # Moonshot Kimi K2
    "moonshotai/kimi-",
    # OpenAI gpt-oss
    "openai/gpt-oss-",
    # IBM Granite 3+
    "ibm/granite-3",
    # ByteDance / MiniMax / Step
    "bytedance/seed-",
    "minimaxai/minimax-",
    "stepfun-ai/step-",
    # Z-AI GLM
    "z-ai/glm",
)


def model_supports_tools(model: str | None) -> bool:
    """Return True if the model id is in the tool-capable whitelist."""
    if not model:
        return False
    return model.startswith(TOOL_CAPABLE_PREFIXES)
