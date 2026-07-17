# NOTICE: This file is protected under RCF-PL
from datetime import datetime

from pydantic import BaseModel, Field


# ── layer 2: golden set ──────────────────────────────────────────────────────
# [RCF:PROTECTED]
class GoldenFreezeRequest(BaseModel):
    min_reward: float = Field(default=0.5, ge=-1.0, le=1.0)
    human_only: bool = True
    limit: int = Field(default=500, gt=0, le=5000)


# [RCF:PROTECTED]
class GoldenFreezeResponse(BaseModel):
    frozen: int
    frozen_at: datetime
    min_reward: float
    human_only: bool
    replaced: bool


# ── layer 3: harness ─────────────────────────────────────────────────────────
# [RCF:PROTECTED]
class HarnessRequest(BaseModel):
    base_provider_id: int
    base_model: str
    forged_provider_id: int
    forged_model: str
    system_prompt: str | None = None
    limit: int = Field(default=100, gt=0, le=1000)


# [RCF:PROTECTED]
class HarnessExample(BaseModel):
    input: str
    base_score: float
    forged_score: float
    delta: float


# [RCF:PROTECTED]
class HarnessResponse(BaseModel):
    evaluated: int
    base_model: str
    forged_model: str
    mean_base: float
    mean_forged: float
    delta: float
    message: str | None = None
    examples: list[HarnessExample] = []
