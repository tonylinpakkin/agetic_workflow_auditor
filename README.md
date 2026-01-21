# Internal Audit Validation System

An end-to-end GenAI workflow demonstrating **multi-agent orchestration**, **RAG (Retrieval-Augmented Generation)**, and **multi-provider LLM integration**. Built with crewAI, this system connects LLMs with local document library to validate audit observations against Hong Kong regulatory policies (HKMA and SFC). Features a 5-stage pipeline with parallel retrieval, reflection-revision quality loops, and automated evaluation.

## Key Features

| Capability | Implementation |
|------------|----------------|
| **End-to-End GenAI Workflow** | 5-stage sequential pipeline with parallel retrieval |
| **Multi-Agent Architecture** | 4 specialized agents with distinct roles and tools |
| **RAG (Retrieval-Augmented Generation)** | Web search, PDF extraction, document parsing |
| **Multi-Provider LLM Support** | OpenAI, Anthropic, Google, DeepSeek, Groq, Ollama |
| **Internal Data Integration** | Connects LLMs with proprietary audit observations |
| **Quality Assurance** | Reflection-revision loop with automated evaluation |


## Workflow Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    INTERNAL AUDIT VALIDATION SYSTEM                         │
│                         Multi-Agent Workflow                                │
└─────────────────────────────────────────────────────────────────────────────┘

                            ┌──────────────────┐
                            │  Audit           │
                            │  Observation     │
                            │  (Input)         │
                            └────────┬─────────┘
                                     │
        ═════════════════════════════╪═════════════════════════════════
        ║            STAGE 1: PARALLEL POLICY RETRIEVAL               ║
        ═════════════════════════════╪═════════════════════════════════
                                     │
                    ┌────────────────┴────────────────┐
                    │                                 │
                    ▼                                 ▼
        ┌───────────────────────┐       ┌───────────────────────┐
        │  HKMA Policy          │       │  SFC Policy           │
        │  Retrieval Specialist │       │  Retrieval Specialist │
        │  (max 25 iterations)  │       │  (max 25 iterations)  │
        │                       │       │                       │
        │  Tools:               │       │  Tools:               │
        │  • RobustFileRead     │       │  • RobustFileRead     │
        │  • SecureWebScraper   │       │  • SecureWebScraper   │
        │  • PDFDownload        │       │  • PDFDownload        │
        │  • SerperDev(10)      │       │  • SerperDev(10)      │
        └───────────┬───────────┘       └───────────┬───────────┘
                    │                               │
                    ▼                               ▼
        ┌───────────────────────┐       ┌───────────────────────┐
        │ hkma_policy_          │       │ sfc_policy_           │
        │ retrieval.md          │       │ retrieval.md          │
        └───────────┬───────────┘       └───────────┬───────────┘
                    │                               │
                    └────────────────┬──────────────┘
                                     │
        ═════════════════════════════╪═════════════════════════════════
        ║            STAGE 2: POLICY AGGREGATION                      ║
        ═════════════════════════════╪═════════════════════════════════
                                     │
                                     ▼
                        ┌───────────────────────┐
                        │  Policy Aggregator    │
                        │  (max 15 iterations)  │
                        │                       │
                        │  • Consolidates       │
                        │  • Deduplicates       │
                        │  • Normalizes         │
                        │  (NO new retrieval)   │
                        └───────────┬───────────┘
                                    │
                                    ▼
                        ┌───────────────────────┐
                        │ policy_retrieval_     │
                        │ aggregated.md         │
                        └───────────┬───────────┘
                                    │
        ════════════════════════════╪══════════════════════════════════
        ║            STAGE 3: QUALITY REFLECTION                      ║
        ════════════════════════════╪══════════════════════════════════
                                    │
                                    ▼
                        ┌───────────────────────┐
                        │  Senior Audit         │
                        │  Reviewer             │
                        │  (max 15 iterations)  │
                        │                       │
                        │  • Validates URLs     │
                        │  • Checks citations   │
                        │  • Verifies dates     │
                        │  (NO tools - context  │
                        │   based review)       │
                        └───────────┬───────────┘
                                    │
                                    ▼
                        ┌───────────────────────┐
                        │  PASS or              │
                        │  NEEDS REVISION       │
                        │  + Feedback           │
                        └───────────┬───────────┘
                                    │
                                    ▼
                        ┌───────────────────────┐
                        │ retrieval_review.md   │
                        └───────────┬───────────┘
                                    │
        ════════════════════════════╪══════════════════════════════════
        ║            STAGE 4: POLICY REVISION                         ║
        ════════════════════════════╪══════════════════════════════════
                                    │
                                    ▼
                        ┌───────────────────────┐
                        │  Policy Aggregator    │
                        │  (Revision Mode)      │
                        │                       │
                        │  • Applies feedback   │
                        │  • Polish & refine    │
                        │  • Tools for critical │
                        │    gaps only          │
                        └───────────┬───────────┘
                                    │
                                    ▼
                        ┌───────────────────────┐
                        │ policy_retrieval_     │
                        │ final.md              │◄──── FINAL DELIVERABLE
                        └───────────┬───────────┘
                                    │
        ════════════════════════════╪══════════════════════════════════
        ║       STAGES 5a/5b: COMPLIANCE ANALYSIS (DISABLED)          ║
        ════════════════════════════╪══════════════════════════════════
                                    │
                    ┌───────────────┴───────────────┐
                    ▼                               ▼
        ┌ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┐   ┌ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┐
          analyze_compliance_           review_compliance_
          status                        analysis
        │ (commented out)       │   │ (commented out)       │
        └ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┘   └ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┘


┌─────────────────────────────────────────────────────────────────────────────┐
│                           OUTPUT STRUCTURE                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   output/YYYYMMDD_HHMMSS/                                                   │
│   ├── hkma_policy_retrieval.md      (Stage 1a)                              │
│   ├── sfc_policy_retrieval.md       (Stage 1b)                              │
│   ├── policy_retrieval_aggregated.md (Stage 2)                              │
│   ├── retrieval_review.md           (Stage 3)                               │
│   └── policy_retrieval_final.md     (Stage 4) ★ Final Deliverable           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Supported LLM Providers

This project uses crewAI with LiteLLM, supporting 100+ LLM providers. Change the `model` parameter in `crew.py` to switch providers.

| Provider | Model Format | Example |
|----------|--------------|---------|
| **OpenAI** | `gpt-*` | `gpt-4o-mini`, `gpt-4o`, `gpt-4-turbo` |
| **Anthropic** | `claude-*` | `claude-3-5-sonnet-20241022`, `claude-3-opus-20240229` |
| **Google** | `gemini/*` | `gemini/gemini-1.5-pro`, `gemini/gemini-1.5-flash` |
| **DeepSeek** | `deepseek/*` | `deepseek/deepseek-chat`, `deepseek/deepseek-coder` |
| **Azure OpenAI** | `azure/*` | `azure/gpt-4o` |
| **AWS Bedrock** | `bedrock/*` | `bedrock/anthropic.claude-3-sonnet` |
| **Ollama (local)** | `ollama/*` | `ollama/llama3`, `ollama/mistral` |
| **Groq** | `groq/*` | `groq/llama3-70b-8192` |

### Required Environment Variables

| Provider | Environment Variable |
|----------|---------------------|
| OpenAI | `OPENAI_API_KEY` |
| Anthropic | `ANTHROPIC_API_KEY` |
| Google | `GEMINI_API_KEY` |
| DeepSeek | `DEEPSEEK_API_KEY` |
| Azure | `AZURE_API_KEY`, `AZURE_API_BASE` |
| AWS Bedrock | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` |
| Groq | `GROQ_API_KEY` |

**Current default:** `gpt-4o-mini` (OpenAI)

## Installation

Requires Python >=3.10 <3.14. This project uses [UV](https://docs.astral.sh/uv/) for dependency management.

```bash
# Install uv if not already installed
pip install uv

# Install dependencies
uv sync
# or
crewai install
```

## Configuration

### LLM Provider Setup

Create a `.env` file with API keys for your chosen provider(s):

```bash
# OpenAI (default)
OPENAI_API_KEY=your-openai-key

# Google Gemini
GEMINI_API_KEY=your-gemini-key

# Anthropic Claude
ANTHROPIC_API_KEY=your-anthropic-key

# Groq
GROQ_API_KEY=your-groq-key

# DeepSeek
DEEPSEEK_API_KEY=your-deepseek-key

# Azure OpenAI
AZURE_API_KEY=your-azure-key
AZURE_API_BASE=https://your-resource.openai.azure.com

# Web search (required for policy retrieval)
SERPER_API_KEY=your-serper-key
```

### Switching LLM Provider

Edit `src/internal_audit_validation_system/crew.py` and change the `model` parameter in each agent's LLM configuration:

```python
# OpenAI (default)
llm=LLM(model="gpt-4o-mini", temperature=0.7)

# Anthropic Claude
llm=LLM(model="claude-3-5-sonnet-20241022", temperature=0.7)

# Google Gemini
llm=LLM(model="gemini/gemini-1.5-flash", temperature=0.7)

# Groq (fast inference)
llm=LLM(model="groq/llama3-70b-8192", temperature=0.7)

# DeepSeek
llm=LLM(model="deepseek/deepseek-chat", temperature=0.7)

# Local Ollama
llm=LLM(model="ollama/llama3", temperature=0.7)
```

### Customizing Files

- `src/internal_audit_validation_system/config/agents.yaml` - Agent definitions
- `src/internal_audit_validation_system/config/tasks.yaml` - Task definitions
- `src/internal_audit_validation_system/crew.py` - Crew logic, tools, and LLM config
- `src/internal_audit_validation_system/main.py` - Custom inputs

## Running the Project

```bash
# Run the crew
python src/internal_audit_validation_system/main.py run
# or
crewai run

# Train the crew
python src/internal_audit_validation_system/main.py train <n_iterations> <filename>

# Replay from a specific task
python src/internal_audit_validation_system/main.py replay <task_id>

# Test with different models
python src/internal_audit_validation_system/main.py test <n_iterations> <model_name>
```

## Evaluating Task Quality

Use the evaluation harness to identify which task is degrading overall output:

```bash
python -m internal_audit_validation_system.evaluation.runner \
  --input-json evaluation/sample_payload.json \
  --write-report evaluation/latest_report.json
```

The CLI prints per-task pass rates across structural checks and writes detailed findings to the report.

## Documentation

See [CLAUDE.md](CLAUDE.md) for detailed development guidelines, architecture documentation, and configuration reference.

## Support

- [crewAI Documentation](https://docs.crewai.com)
- [crewAI GitHub](https://github.com/joaomdmoura/crewai)
- [crewAI Discord](https://discord.com/invite/X4JWnZnxPb)
