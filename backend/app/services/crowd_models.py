"""Models for MVP crowd intelligence."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class CrowdLevel(StrEnum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


@dataclass(frozen=True)
class CrowdBaseline:
    score: float
    level: CrowdLevel
    explanation: str