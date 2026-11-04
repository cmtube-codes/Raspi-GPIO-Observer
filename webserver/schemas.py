"""Pydantic schemas used by API and web actions."""

from typing import Literal

from pydantic import BaseModel, Field


class GPIOConfig(BaseModel):
    gpio: int = Field(..., ge=0, le=40)
    pull_down: bool = True
    edge: Literal["rising", "falling", "both"] = "rising"


class GPIOOutputConfig(BaseModel):
    gpio: int = Field(..., ge=0, le=40)
    state: Literal["high", "low"] = "low"
