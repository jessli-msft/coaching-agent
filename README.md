# Agent Coach — Dynamics 365 Customer Service POC

> **Always-on, in-the-moment coaching** for customer service representatives, built on top of the Quality Evaluation Agent (QEA) and Governance Agent.

---

## Overview

**Agent Coach** is a proof-of-concept (POC) for a coaching capability embedded within Dynamics 365 Customer Service. It transforms quality insights and governance guidance into actionable, contextual coaching for service representatives — case by case, without disrupting their workflow.

The solution closes the loop between **evaluation → compliance → measurable improvement** by orchestrating three AI agents:

| Agent | Responsibility |
|---|---|
| **Quality Evaluation Agent (QEA)** | Scores the conversation across 6 quality dimensions (empathy, resolution effectiveness, communication clarity, process adherence, customer effort, knowledge accuracy) |
| **Governance Agent** | Checks the conversation against 7 compliance rules (identity verification, data privacy, mandatory disclosure, escalation protocol, closing procedure, prohibited language, accurate promises) |
| **Coaching Agent** | Synthesises QEA + Governance results into a prioritised, personalised coaching session with concrete action steps and example scripts |

---

## Architecture

```
Case (transcript)
     │
     ▼
Quality Evaluation Agent  ──┐
                             ├──▶  Coaching Agent  ──▶  CoachingSession
Governance Agent          ──┘
```

All agents are coordinated by the **AgentCoachOrchestrator**. Each agent calls Azure OpenAI (GPT-4o by default) with structured JSON output. A built-in mock mode enables full end-to-end testing without Azure credentials.

### Project Structure

```
coaching-agent/
├── src/
│   ├── agents/
│   │   ├── quality_evaluation_agent.py   # QEA — quality scoring
│   │   ├── governance_agent.py           # Governance — compliance checks
│   │   ├── coaching_agent.py             # Coaching — personalised recommendations
│   │   └── orchestrator.py              # End-to-end pipeline coordinator
│   ├── models/
│   │   ├── case.py                       # Case & ConversationTurn models
│   │   ├── evaluation.py                 # QualityEvaluation models
│   │   └── coaching.py                   # GovernanceCheck & CoachingSession models
│   └── config/
│       └── settings.py                   # Settings via environment variables
├── tests/
│   ├── conftest.py
│   ├── test_quality_evaluation_agent.py
│   ├── test_governance_agent.py
│   ├── test_coaching_agent.py
│   └── test_orchestrator.py
├── demo.py                               # CLI demo — showcases the full pipeline
├── requirements.txt
├── requirements-dev.txt
└── .env.example
```

---

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Azure OpenAI (optional for mock mode)

```bash
cp .env.example .env
# Edit .env with your Azure OpenAI endpoint and API key
```

### 3. Run the demo

```bash
# Mock mode (no Azure credentials required — great for exploring)
MOCK_LLM_RESPONSES=true python demo.py

# Real mode (requires .env with Azure OpenAI credentials)
python demo.py
```

The demo processes a sample billing-dispute case and prints:
- 📊 Quality evaluation scores across all dimensions
- 🏛️ Governance compliance check results
- 🎓 Personalised coaching session with prioritised recommendations

---

## Running Tests

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

All 35 tests run in mock mode — no Azure credentials required.

---

## Configuration

All settings are loaded from environment variables (or a `.env` file):

| Variable | Default | Description |
|---|---|---|
| `AZURE_OPENAI_ENDPOINT` | *(required for real mode)* | Your Azure OpenAI resource URL |
| `AZURE_OPENAI_API_KEY` | *(required for real mode)* | Azure OpenAI API key |
| `AZURE_OPENAI_API_VERSION` | `2024-02-01` | API version |
| `AZURE_OPENAI_DEPLOYMENT_NAME` | `gpt-4o` | Deployment / model name |
| `MAX_COACHING_RECOMMENDATIONS` | `5` | Maximum recommendations per session |
| `MOCK_LLM_RESPONSES` | `false` | Skip LLM calls; use deterministic mock data |

---

## Usage as a Library

```python
from src.agents.orchestrator import AgentCoachOrchestrator
from src.config.settings import Settings
from src.models.case import Case, ConversationTurn, SpeakerRole

settings = Settings(mock_llm_responses=True)  # or load from .env

case = Case(
    case_id="CASE-001",
    agent_id="agent-alex",
    agent_name="Alex",
    category="Billing",
    transcript=[
        ConversationTurn(speaker=SpeakerRole.AGENT, text="Thank you for calling..."),
        ConversationTurn(speaker=SpeakerRole.CUSTOMER, text="I have a billing issue..."),
        # ... more turns
    ],
)

orchestrator = AgentCoachOrchestrator(settings)
result = orchestrator.run(case)

print(result.coaching_session.opening_message)
for rec in result.coaching_session.recommendations:
    print(f"[{rec.priority.value.upper()}] {rec.title}")
```

---

## Phases

This repo is a **constantly evolving POC** for the Agent Coach. Future phases may include:

- Integration with Dynamics 365 Customer Service data connectors
- Real-time coaching triggers (during live calls)
- Supervisor dashboard with aggregated coaching trends
- Configurable coaching rule sets per team / skill group
- Agent skill-progression tracking over time
