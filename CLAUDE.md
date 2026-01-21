# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a crewAI-based multi-agent system that validates internal audit observations against Hong Kong regulatory policies (HKMA and SFC). The system uses specialized AI agents to retrieve, aggregate, review, and revise policy compliance information through a sequential workflow.

## Running the System

**Primary execution commands:**
```bash
# Run the crew with default audit observation
python src/internal_audit_validation_system/main.py run

# Train the crew (requires n_iterations and filename)
python src/internal_audit_validation_system/main.py train <n_iterations> <filename>

# Replay from a specific task
python src/internal_audit_validation_system/main.py replay <task_id>

# Test with different models
python src/internal_audit_validation_system/main.py test <n_iterations> <model_name>
```

**Environment setup:**
- Requires Python >=3.10, <3.14
- Uses UV for dependency management
- Set `OPENAI_API_KEY` in `.env` file before running

**Running evaluations:**
```bash
python -m internal_audit_validation_system.evaluation.runner \
  --input-json evaluation/sample_payload.json \
  --write-report evaluation/latest_report.json
```

## Architecture

### Multi-Agent Workflow (5 Active Tasks in 4 Stages)

**Stage 1: Parallel Policy Retrieval**
- `retrieve_hkma_policies` - HKMA Policy Retrieval Specialist searches HKMA sources
- `retrieve_sfc_policies` - SFC Policy Retrieval Specialist searches SFC sources
- Both agents run with max 25 iterations, output separate markdown tables

**Stage 2: Policy Aggregation**
- `retrieve_relevant_policies` - Policy Aggregator consolidates HKMA + SFC outputs
- Works ONLY from context (no new retrieval), deduplicates, normalizes
- Outputs: `policy_retrieval_aggregated.md`

**Stage 3: Quality Reflection**
- `reflect_policy_retrieval` - Senior Audit Reviewer validates citations, dates, URLs
- Returns PASS or NEEDS REVISION verdict with feedback
- Outputs: `retrieval_review.md`

**Stage 4: Policy Revision**
- `revise_policy_retrieval` - Policy Aggregator revises based on reflection feedback
- Primary goal is polishing; tools used only for critical gaps
- Outputs: `policy_retrieval_final.md` (final deliverable)

**Stages 5a/5b: Compliance Analysis (Currently Disabled)**
- `analyze_compliance_status` and `review_compliance_analysis` are commented out in [crew.py](src/internal_audit_validation_system/crew.py:382-383)

### Agent Configuration

All agents use GPT-4o-mini with temperature 0.7, max 5 retries, 120s timeout:

| Agent | Max Iterations | Tools |
|-------|----------------|-------|
| HKMA Policy Retrieval Specialist | 25 | RobustFileRead, SecureWebScraper, PDFDownload, SerperDev(10) |
| SFC Policy Retrieval Specialist | 25 | RobustFileRead, SecureWebScraper, PDFDownload, SerperDev(10) |
| Policy Aggregator | 15 | SerperDev(10), MarkdownToPDF |
| Senior Audit Reviewer | 15 | None (context-based review) |

### Custom Tools ([custom_tool.py](src/internal_audit_validation_system/tools/custom_tool.py))

**RobustFileReadTool** - Reads LOCAL files only
- Handles relative/absolute paths
- Validation prevents URL usage (returns error if http/https detected)
- Supports line range reading

**SecureWebScraperTool** - Scrapes regulatory websites
- SSL verification disabled for HKMA/SFC certificate issues
- HTML cleaning, 10k character limit
- Returns text-only content

**PDFDownloadTool** - Downloads and extracts PDF content
- SSL-tolerant for problematic government sites
- Text extraction from all pages, 50k character limit
- Handles page-based truncation

**SerperDevTool** (from crewai_tools) - Web search
- Returns top 10 results
- CRITICAL: Make ONE search at a time (never batch multiple queries)
- Use simple dict format: `{"search_query": "your query here"}`

**MarkdownToPDFTool** - Converts markdown reports to professional PDF documents
- Specifically designed for policy retrieval tables with 8-column structure
- Automatically converts markdown links `[text](url)` to clickable hyperlinks in PDF
- Landscape A4 orientation for wide tables
- Professional styling: blue headers, alternating row colors, proper text wrapping
- Usage: `{"markdown_file_path": "path/to/file.md", "pdf_output_path": "optional/output.pdf"}`
- If pdf_output_path not provided, creates PDF with same name as markdown file

### Data Structure: 8-Column Policy Table

Every policy table output must contain these columns:

| Column | Description | Example |
|--------|-------------|---------|
| Source Name | Regulation identifier | "HKMA SPM OR-1" |
| Section / Clause | Specific section | "3.2.4" |
| Key Excerpt | Verbatim quote (≤1 sentence) | "Institutions must maintain..." |
| Relevance to Observation | How it applies | "Directly addresses backup requirements" |
| Document Path / URL | Source location (never N/A) | "https://www.hkma.gov.hk/..." |
| Effective Date | When it took effect | "2023-01-15" |
| Confidence | Relevance certainty | "High" / "Med" / "Low" |
| Link or Reference | Additional reference | URL or "N/A" |

## Key Files and Configuration

### Configuration Files
- [agents.yaml](src/internal_audit_validation_system/config/agents.yaml) - 6 agent definitions (4 active + 2 disabled/legacy)
- [tasks.yaml](src/internal_audit_validation_system/config/tasks.yaml) - 8 task definitions (5 active)
- [crew.py](src/internal_audit_validation_system/crew.py) - Crew implementation with sequential processing

### Code Entry Points
- [main.py](src/internal_audit_validation_system/main.py) - Main execution with timestamped output management
- [custom_tool.py](src/internal_audit_validation_system/tools/custom_tool.py) - Custom tool implementations
- [criteria.py](src/internal_audit_validation_system/evaluation/criteria.py) - Quality check definitions
- [runner.py](src/internal_audit_validation_system/evaluation/runner.py) - Evaluation harness

### Output Management

**Timestamped outputs:** Each run creates a timestamped directory in `output/YYYYMMDD_HHMMSS/` containing:
- `hkma_policy_retrieval.md` (Stage 1a)
- `sfc_policy_retrieval.md` (Stage 1b)
- `policy_retrieval_aggregated.md` (Stage 2)
- `retrieval_review.md` (Stage 3)
- `policy_retrieval_final.md` (Stage 4 - final deliverable)

Timestamps are generated in [main.py](src/internal_audit_validation_system/main.py:23-34) and propagated to all tasks via [crew.py](src/internal_audit_validation_system/crew.py:52-73) path updates.

**Evaluation outputs:** Saved to `evaluation/` directory:
- `latest_payload.json` - Task outputs formatted for evaluation
- `latest_report.json` - Quality check results with pass rates

## Evaluation Framework

### Quality Checks ([criteria.py](src/internal_audit_validation_system/evaluation/criteria.py))

**Policy Retrieval Checks (8 total):**
1. `table_present` - Markdown table with correct columns
2. `table_rows` - At least 1 policy row
3. `table_content_quality` - Meaningful Source Name and Key Excerpt (≥2 chars, ≥5 chars)
4. `link_column_format` - URLs or "N/A" only
5. `url_reachability` - HTTP 2xx/3xx status (prevents hallucinated URLs)
6. `critical_requirements` - Bullet list with ≥3 items
7. `hkma_reference` - HKMA mentioned
8. `sfc_reference` - SFC mentioned

**Compliance Analysis Checks (6 total):**
- Status section, classification, supporting evidence (≥2 bullets)
- Risk assessment, investigation areas, policy table present

**Review Analysis Checks (4 total):**
- Adequacy assessment, deficiencies, recommendations, readiness verdict

**Scoring:** Pass rate = (passed checks / total checks) × 100%

## Critical Development Guidelines

### Tool Usage Rules

1. **SerperDevTool - ONE SEARCH AT A TIME**
   - Never batch multiple search queries
   - Complete each search, review results, then decide if another is needed
   - Use simple dict: `{"search_query": "HKMA SPM OR-1 operational risk"}`

2. **URL Verification is Mandatory**
   - When adding new sources in revision task, MUST verify URLs via SerperDevTool
   - Never fabricate or guess URLs based on patterns
   - The `url_reachability` check will fail on unreachable URLs

3. **File Read vs PDF Download**
   - RobustFileReadTool: LOCAL files only (will error on URLs)
   - PDFDownloadTool: For PDF URLs only
   - Tool descriptions explicitly prevent misuse

4. **SSL Certificate Handling**
   - SecureWebScraper and PDFDownload both disable SSL verification (`verify=False`)
   - Required for HKMA/SFC sites with certificate issues
   - Warnings suppressed in [custom_tool.py](src/internal_audit_validation_system/tools/custom_tool.py:14)

### Task Context Dependencies

Tasks receive context from previous tasks as defined in tasks.yaml:
- `retrieve_relevant_policies` receives context from HKMA + SFC retrieval tasks
- `reflect_policy_retrieval` receives context from aggregation task
- `revise_policy_retrieval` receives context from reflection task

**IMPORTANT:** Aggregator task description is overridden in [crew.py](src/internal_audit_validation_system/crew.py:280-300) to enforce consolidation-only behavior (no new retrieval).

### Regulatory Sources

**HKMA Sources (prioritize these):**
- HKMA Supervisory Policy Manual (SPM) modules: OR-1, TM-E-1, TM-G-2, etc.
- HKMA circulars, guidelines, FAQs
- Site filter: `site:hkma.gov.hk`

**SFC Sources (especially for securities/asset management):**
- Code of Conduct for Persons Licensed by or Registered with the SFC
- Fund Manager Code of Conduct (FMCC)
- Client Assets Rules / Client Money Rules (CASS/CMA)
- Unit Trusts and Mutual Funds Code (UT Code)
- SFC circulars, FAQs, guidance notes
- Site filter: `site:sfc.hk`

## Common Issues and Solutions

**Issue:** Agent fabricates URLs instead of using web search
- **Solution:** Ensure `url_reachability` check is enabled - it will fail on hallucinated URLs
- Policy Aggregator has SerperDevTool to prevent this during revision

**Issue:** Task hangs or exceeds iterations
- **Solution:** Check max_iter settings in agent definitions (25 for retrieval, 15 for aggregation/review)
- Review rate limiting: crew level max_rpm=10

**Issue:** SSL certificate errors from HKMA/SFC sites
- **Solution:** Already handled - custom tools disable verification via `verify=False`

**Issue:** Evaluation fails on missing sections
- **Solution:** Review criteria.py check definitions to understand exact requirements
- Use [workflow_flowchart.md](workflow_flowchart.md) to verify task sequence

## Testing and Debugging

**Modify the default audit observation:**
Edit [main.py](src/internal_audit_validation_system/main.py:127-129) in the `run()` function:
```python
inputs = {
    "audit_observation": "Your custom observation here"
}
```

**Enable/disable tasks:**
Edit the task list in [crew.py](src/internal_audit_validation_system/crew.py:376-385):
```python
tasks=[
    self.retrieve_hkma_policies(),
    self.retrieve_sfc_policies(),
    self.retrieve_relevant_policies(),
    self.reflect_policy_retrieval(),
    self.revise_policy_retrieval(),
    # Uncomment these to enable compliance analysis:
    # self.analyze_compliance_status(),
    # self.review_compliance_analysis()
]
```

**View detailed logs:**
The crew runs with `verbose=True` - all agent actions, tool calls, and outputs are printed to console.

## Project Structure

```
.
├── src/internal_audit_validation_system/
│   ├── config/
│   │   ├── agents.yaml          # Agent role, goal, backstory definitions
│   │   └── tasks.yaml           # Task descriptions, expected outputs, context
│   ├── tools/
│   │   └── custom_tool.py       # RobustFileRead, SecureWebScraper, PDFDownload
│   ├── evaluation/
│   │   ├── criteria.py          # Quality check definitions
│   │   └── runner.py            # Evaluation execution
│   ├── crew.py                  # Crew assembly, task/agent wiring
│   └── main.py                  # Entry point with timestamped output setup
├── output/                      # Timestamped run outputs
├── evaluation/                  # Evaluation payloads and reports
├── knowledge/                   # Local policy documents (if any)
├── pyproject.toml              # Dependencies and scripts
└── workflow_flowchart.md       # Detailed system architecture diagram
```
