"""Request models for the Touchline API."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Persona = Literal["CASUAL_FAN", "TACTICO_ANALYST", "BROADCAST_STUDIO"]
Language = Literal["en", "es", "ar"]
Club = Literal["NLR", "MCB"]


class AnalyzeRequest(BaseModel):
    minute: int = Field(default=54, ge=1, le=90)
    persona: Persona = "CASUAL_FAN"
    favorite_club: Club = "NLR"
    spotlight_player_id: str | None = None
    language: Language = "en"
    custom_question: str | None = Field(default=None, max_length=400)


class DiagnoseRequest(BaseModel):
    minute: int = Field(default=67, ge=1, le=90)
    team_id: Club = "NLR"
    persona: Persona = "CASUAL_FAN"
    language: Language = "en"


class AutoEventRequest(BaseModel):
    segment_minute: int = Field(default=54, ge=1, le=90)
