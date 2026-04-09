"""Data models for customer service cases and conversation transcripts."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class SpeakerRole(str, Enum):
    """Who spoke a given turn in the conversation."""

    AGENT = "agent"
    CUSTOMER = "customer"
    SYSTEM = "system"


class CaseStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    ESCALATED = "escalated"


class ConversationTurn(BaseModel):
    """A single utterance within a customer service conversation."""

    speaker: SpeakerRole
    text: str
    timestamp: Optional[datetime] = None

    def __str__(self) -> str:
        return f"[{self.speaker.value.upper()}] {self.text}"


class Case(BaseModel):
    """A customer service case with its full conversation transcript."""

    case_id: str = Field(..., description="Unique identifier for the case")
    agent_id: str = Field(..., description="Identifier for the service representative")
    agent_name: str = Field(default="", description="Display name of the agent")
    customer_id: str = Field(default="", description="Identifier for the customer")
    category: str = Field(default="", description="Issue category / topic")
    status: CaseStatus = Field(default=CaseStatus.RESOLVED)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    transcript: List[ConversationTurn] = Field(
        default_factory=list,
        description="Ordered list of conversation turns",
    )

    @property
    def formatted_transcript(self) -> str:
        """Return a human-readable string of the full transcript."""
        return "\n".join(str(turn) for turn in self.transcript)

    @property
    def agent_turns(self) -> List[ConversationTurn]:
        return [t for t in self.transcript if t.speaker == SpeakerRole.AGENT]

    @property
    def customer_turns(self) -> List[ConversationTurn]:
        return [t for t in self.transcript if t.speaker == SpeakerRole.CUSTOMER]
