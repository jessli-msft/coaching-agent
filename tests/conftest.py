"""Shared test fixtures."""

from __future__ import annotations

import pytest

from src.config.settings import Settings
from src.models.case import Case, ConversationTurn, SpeakerRole


@pytest.fixture()
def mock_settings() -> Settings:
    """Return Settings with mock LLM enabled so no Azure credentials are needed."""
    return Settings(mock_llm_responses=True)


@pytest.fixture()
def sample_case() -> Case:
    """Return a minimal but realistic customer service case."""
    return Case(
        case_id="TEST-001",
        agent_id="agent-001",
        agent_name="Test Agent",
        customer_id="cust-001",
        category="Billing",
        transcript=[
            ConversationTurn(
                speaker=SpeakerRole.AGENT,
                text="Thank you for calling. How can I help?",
            ),
            ConversationTurn(
                speaker=SpeakerRole.CUSTOMER,
                text="I was charged incorrectly.",
            ),
            ConversationTurn(
                speaker=SpeakerRole.AGENT,
                text="I'll look into that right away.",
            ),
            ConversationTurn(
                speaker=SpeakerRole.CUSTOMER,
                text="Great, thank you.",
            ),
            ConversationTurn(
                speaker=SpeakerRole.AGENT,
                text="I've processed the refund. Is there anything else?",
            ),
        ],
    )
