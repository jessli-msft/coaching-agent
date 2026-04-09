"""Demo script — showcases the Agent Coach end-to-end pipeline.

Run with:
    python demo.py

Set MOCK_LLM_RESPONSES=true (default) to run without Azure credentials,
or configure your .env file with real Azure OpenAI credentials.
"""

from __future__ import annotations

import os
import textwrap

# Enable mock mode by default so the demo works without Azure credentials.
os.environ.setdefault("MOCK_LLM_RESPONSES", "true")

import logging

logging.basicConfig(level=logging.WARNING)

from src.agents.orchestrator import AgentCoachOrchestrator
from src.config.settings import get_settings
from src.models.case import Case, ConversationTurn, SpeakerRole
from src.models.coaching import CoachingPriority

_PRIORITY_ICONS = {
    CoachingPriority.CRITICAL: "🔴",
    CoachingPriority.HIGH: "🟠",
    CoachingPriority.MEDIUM: "🟡",
    CoachingPriority.LOW: "🔵",
}


def build_sample_case() -> Case:
    """Return a realistic sample customer service case."""
    return Case(
        case_id="CASE-2024-0042",
        agent_id="agent-alex-123",
        agent_name="Alex",
        customer_id="cust-98765",
        category="Billing Dispute",
        transcript=[
            ConversationTurn(
                speaker=SpeakerRole.AGENT,
                text="Thank you for calling Contoso Support. My name is Alex, how can I help you today?",
            ),
            ConversationTurn(
                speaker=SpeakerRole.CUSTOMER,
                text="Hi, I'm really frustrated. I was charged twice for my subscription this month!",
            ),
            ConversationTurn(
                speaker=SpeakerRole.AGENT,
                text="I understand that's frustrating. Let me pull up your account right away.",
            ),
            ConversationTurn(
                speaker=SpeakerRole.CUSTOMER,
                text="My account email is jane.doe@example.com.",
            ),
            ConversationTurn(
                speaker=SpeakerRole.AGENT,
                text="I can see your account. Yes, I can see there were two charges of $29.99 on the 3rd and 4th. That was a system error on our side. I'll process a refund for the duplicate charge right now.",
            ),
            ConversationTurn(
                speaker=SpeakerRole.CUSTOMER,
                text="Thank goodness. How long will the refund take?",
            ),
            ConversationTurn(
                speaker=SpeakerRole.AGENT,
                text="The refund will appear on your statement within 3-5 business days. I've also added a note to your account. Is there anything else I can help you with today?",
            ),
            ConversationTurn(
                speaker=SpeakerRole.CUSTOMER,
                text="No that's all. Thank you.",
            ),
            ConversationTurn(
                speaker=SpeakerRole.AGENT,
                text="You're welcome. To summarise: I've processed a refund of $29.99 which you'll see in 3-5 business days. Have a great day!",
            ),
        ],
    )


def print_separator(char: str = "─", width: int = 72) -> None:
    print(char * width)


def print_header(title: str) -> None:
    print_separator("═")
    print(f"  {title}")
    print_separator("═")


def print_section(title: str) -> None:
    print()
    print_separator()
    print(f"  {title}")
    print_separator()


def display_result(result) -> None:  # noqa: ANN001
    """Pretty-print the full orchestration result."""
    ev = result.evaluation
    gov = result.governance
    session = result.coaching_session

    # ── Quality Evaluation ───────────────────────────────────────────────────
    print_section("📊  QUALITY EVALUATION RESULTS")
    print(f"  Overall Score: {ev.overall_score:.1f} / 10\n")
    for score in ev.scores:
        bar_filled = int(score.score)
        bar = "█" * bar_filled + "░" * (10 - bar_filled)
        print(f"  {score.dimension.value:<30} {bar}  {score.score:4.1f}")
    print()
    print("  Strengths:")
    for s in ev.strengths:
        print(f"    ✅ {s}")
    print()
    print("  Improvement Areas:")
    for a in ev.improvement_areas:
        print(f"    📌 {a}")
    print()
    print("  Summary:")
    print(textwrap.fill(ev.summary, width=68, initial_indent="  ", subsequent_indent="  "))

    # ── Governance Check ─────────────────────────────────────────────────────
    print_section("🏛️  GOVERNANCE & COMPLIANCE CHECK")
    status_icon = "✅  COMPLIANT" if gov.overall_compliant else "❌  NON-COMPLIANT"
    print(f"  Status: {status_icon}\n")
    for item in gov.compliance_items:
        icon = {"pass": "✅", "fail": "❌", "warning": "⚠️", "not_applicable": "➖"}[
            item.status.value
        ]
        print(f"  {icon}  [{item.rule_id}] {item.rule_name}")
        if item.finding:
            print(
                textwrap.fill(
                    f"     Finding: {item.finding}",
                    width=70,
                    subsequent_indent="              ",
                )
            )
    print()
    print("  Summary:")
    print(textwrap.fill(gov.summary, width=68, initial_indent="  ", subsequent_indent="  "))

    # ── Coaching Session ──────────────────────────────────────────────────────
    print_section("🎓  AGENT COACHING SESSION")
    print(f"  Session ID: {session.session_id}")
    print(f"  Agent: {session.agent_name or session.agent_id}\n")

    if session.opening_message:
        print(
            textwrap.fill(
                f"  💬 {session.opening_message}",
                width=70,
                subsequent_indent="     ",
            )
        )
        print()

    print(f"  Recommendations ({len(session.recommendations)} total):\n")
    for i, rec in enumerate(session.recommendations, 1):
        icon = _PRIORITY_ICONS.get(rec.priority, "•")
        print(f"  {i}. {icon}  [{rec.priority.value.upper()}] {rec.title}")
        print(
            textwrap.fill(
                rec.description,
                width=68,
                initial_indent="     ",
                subsequent_indent="     ",
            )
        )
        if rec.action_steps:
            print("     Action Steps:")
            for step in rec.action_steps:
                print(
                    textwrap.fill(
                        f"       → {step}",
                        width=70,
                        subsequent_indent="         ",
                    )
                )
        if rec.example_script:
            print()
            print(
                textwrap.fill(
                    f'     📝 Example: "{rec.example_script}"',
                    width=70,
                    subsequent_indent="              ",
                )
            )
        print()

    if session.closing_message:
        print(
            textwrap.fill(
                f"  🌟 {session.closing_message}",
                width=70,
                subsequent_indent="     ",
            )
        )


def main() -> None:
    settings = get_settings()
    case = build_sample_case()

    print_header(
        f"🤖  AGENT COACH POC — Dynamics 365 Customer Service\n"
        f"     Case: {case.case_id}  |  Agent: {case.agent_name}  |  Category: {case.category}"
    )

    print(f"\n  Mode: {'🔧 MOCK (no Azure OpenAI)' if settings.mock_llm_responses else '☁️  Azure OpenAI'}\n")

    print_section("📋  CONVERSATION TRANSCRIPT")
    for turn in case.transcript:
        speaker_label = f"[{turn.speaker.value.upper():<8}]"
        print(
            textwrap.fill(
                f"  {speaker_label} {turn.text}",
                width=72,
                subsequent_indent="               ",
            )
        )

    print()
    print("  Running Agent Coach pipeline...")
    orchestrator = AgentCoachOrchestrator(settings)
    result = orchestrator.run(case)

    display_result(result)
    print_separator("═")
    print()


if __name__ == "__main__":
    main()
