# NOTICE: This file is protected under RCF-PL
"""Pydantic schemas for the Self-Forging golden set + evaluation harness."""
from __future__ import annotations

from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field


SplitName = Literal["train", "validation", "heldout"]


class FreezeRequest(BaseModel):
    min_reward: float = Field(0.5, ge=-1.0, le=1.0)
    human_only: bool = True
    limit: int = Field(500, gt=0, le=5000)
    ratios: dict[str, float] | None = None


# Backward-compatible alias for existing router
GoldenFreezeRequest = FreezeRequest


class FreezeResponse(BaseModel):
    version: int = 1
    frozen: int
    counts: dict[str, int] = Field(default_factory=dict)
    status: str = "ready"
    frozen_at: datetime
    min_reward: float
    human_only: bool
    replaced: bool = False
    warnings: list[str] = Field(default_factory=list)


# Backward-compatible alias for existing router
GoldenFreezeResponse = FreezeResponse


class GoldenExampleResponse(BaseModel):
    input: str
    expected: str
    reward: float | None = None
    model: str | None = None
    human_labeled: bool = False
    frozen_at: datetime
    dataset_version: int | None = None
    split: SplitName | None = None
    session_id: str | None = None
    split_group_key: str | None = None
    rejected_response: str | None = None
    dpo_pair_status: str | None = None


class ExportRequest(BaseModel):
    version: int | None = None
    split: SplitName = "train"
    format: Literal["sft", "chat", "dpo"] = "sft"
    system_prompt: str = ""
    limit: int = Field(500, gt=0, le=5000)


class ExportResponse(BaseModel):
    format: str
    split: str = "train"
    dataset_version: int | None = None
    examples: int
    golden_available: int
    jsonl: str
    skipped_unpaired: int | None = None
    skipped_cross_session: int | None = None
    warnings: list[str] = Field(default_factory=list)


class HarnessRequest(BaseModel):
    version: int | None = None
    split: SplitName = "heldout"

    base_provider_id: int
    base_model: str

    forged_provider_id: int
    forged_model: str

    system_prompt: str | None = None
    limit: int = Field(100, gt=0, le=1000)


class HarnessExampleResult(BaseModel):
    input: str
    base_score: float
    forged_score: float
    delta: float


class HarnessResponse(BaseModel):
    evaluated: int
    split: str = "heldout"
    dataset_version: int | None = None
    base_model: str
    forged_model: str
    mean_base: float
    mean_forged: float
    delta: float
    message: str | None = None
    examples: list[HarnessExampleResult] = Field(default_factory=list)