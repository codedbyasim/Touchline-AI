"""Shared agent-to-agent blackboard."""

from __future__ import annotations

from pydantic import BaseModel, Field


class MatchBlackboardState(BaseModel):
    telemetry: dict | None = None
    causal: dict | None = None
    personalization: dict | None = None
    audit: dict | None = None
    errors: list[str] = Field(default_factory=list)
    handoffs: list[str] = Field(default_factory=list)

    def handoff(self, sender: str, receiver: str, note: str) -> None:
        self.handoffs.append(f"{sender} -> {receiver}: {note}")
