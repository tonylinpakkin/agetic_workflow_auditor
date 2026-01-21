from __future__ import annotations

import re
import requests
from dataclasses import dataclass, field
from typing import Callable, Dict, Iterable, List, Optional, Tuple

MarkdownText = str
TaskContext = Dict[str, str]


@dataclass(frozen=True)
class CheckDefinition:
    """Single structural/content check applied to a task output."""

    id: str
    description: str
    evaluator: Callable[[MarkdownText, TaskContext], Tuple[bool, Optional[str]]]
    hint: Optional[str] = None

    def run(self, output: MarkdownText, context: TaskContext) -> Tuple[bool, Optional[str]]:
        """Execute the check safely and capture diagnostic notes."""
        try:
            return self.evaluator(output, context)
        except Exception as exc:  # pragma: no cover - defensive
            return False, f"Check raised exception: {exc}"


@dataclass
class TaskEvaluation:
    """Aggregated evaluation results for a single task output."""

    task_name: str
    passed: List[str] = field(default_factory=list)
    failed: List[Tuple[str, Optional[str]]] = field(default_factory=list)
    score: float = 0.0

    def as_dict(self) -> Dict[str, object]:
        return {
            "task_name": self.task_name,
            "score": self.score,
            "passed": self.passed,
            "failed": [{"id": check_id, "notes": notes} for check_id, notes in self.failed],
        }


@dataclass
class EvaluateResult:
    """Top level wrapper for a full crew run."""

    audit_observation: str
    task_results: List[TaskEvaluation]

    def successful(self) -> bool:
        return all(result.score == 1.0 for result in self.task_results)


# --- Utility predicates ---------------------------------------------------- #

def _markdown_table_present(output: MarkdownText, headers: Iterable[str]) -> bool:
    """Return true if a markdown table with the expected headers exists."""
    header_pattern = r"\|\s*" + r"\s*\|\s*".join(map(re.escape, headers)) + r"\s*\|"
    return bool(re.search(header_pattern, output, re.IGNORECASE))


def _count_table_rows(output: MarkdownText) -> int:
    """DEPRECATED: Use _count_policy_table_rows instead."""
    tables = re.findall(r"\|.+\|", output)
    if len(tables) < 2:
        return 0
    # Exclude header + separator line -> remaining are rows
    return max(0, len(tables) - 2)


def _count_policy_table_rows(output: MarkdownText) -> int:
    """Count rows in the policy table specifically by locating it via headers."""
    headers = ["Source Name", "Section / Clause", "Key Excerpt", "Relevance to Observation", "Link or Reference"]
    header_pattern = r"\|\s*" + r"\s*\|\s*".join(map(re.escape, headers)) + r"\s*\|"

    # Find the header
    header_match = re.search(header_pattern, output, re.IGNORECASE)
    if not header_match:
        return 0

    # Find content after header
    start_pos = header_match.end()
    remaining = output[start_pos:]

    # Skip separator line (e.g., |---|---|---|)
    lines = remaining.split('\n')
    if len(lines) < 2:
        return 0

    # First line after header should be separator
    if re.match(r'^\s*\|[\s\-:]+\|', lines[0]):
        lines = lines[1:]

    # Count data rows until we hit a non-table line
    rows = 0
    for line in lines:
        stripped = line.strip()
        # Check if line is a table row
        if stripped and re.match(r'^\|.+\|', stripped):
            rows += 1
        # Stop at markdown heading or significant non-table content
        elif stripped and (re.match(r'^#+\s', stripped) or (not stripped.startswith('|') and len(stripped) > 10)):
            break

    return rows


def _section_present(output: MarkdownText, title: str) -> bool:
    pattern = rf"^##+\s*{re.escape(title)}"
    return bool(re.search(pattern, output, re.IGNORECASE | re.MULTILINE))


def _contains_any(output: MarkdownText, keywords: Iterable[str]) -> bool:
    return any(re.search(re.escape(word), output, re.IGNORECASE) for word in keywords)


def _bullet_list_after_phrase(output: MarkdownText, phrase: str, min_items: int) -> bool:
    """Check for bullet list after a phrase, allowing for headings, colons, and blank lines."""
    # Look for the phrase as a heading (with # markdown) or in text
    # Allow optional punctuation like colons after the phrase
    pattern = rf"(?:^#+\s*.*{re.escape(phrase)}.*$|{re.escape(phrase)}[\s:]*)"
    match = re.search(pattern, output, re.IGNORECASE | re.MULTILINE)

    if not match:
        return False

    # Look for bullet list after the phrase (allowing blank lines and various bullet styles)
    remaining = output[match.end():]
    # Allow whitespace and newlines before bullets, then require min_items bullet points
    bullet_pattern = rf"(?:\s*\n)+([-*+]\s+.+(?:\s*\n+[-*+]\s+.+){{{min_items - 1},}})"

    return bool(re.search(bullet_pattern, remaining, re.MULTILINE))


def _extract_policy_table_rows(output: MarkdownText) -> List[str]:
    """Extract data rows from the policy table."""
    headers = ["Source Name", "Section / Clause", "Key Excerpt", "Relevance to Observation", "Link or Reference"]
    header_pattern = r"\|\s*" + r"\s*\|\s*".join(map(re.escape, headers)) + r"\s*\|"

    # Find the header
    header_match = re.search(header_pattern, output, re.IGNORECASE)
    if not header_match:
        return []

    # Find content after header
    start_pos = header_match.end()
    remaining = output[start_pos:]

    # Skip separator line
    lines = remaining.split('\n')
    if len(lines) < 2:
        return []

    # Skip first line if it's the separator
    start_idx = 0
    if lines and re.match(r'^\s*\|[\s\-:]+\|[\s\-:|]*$', lines[0]):
        start_idx = 1

    # Collect data rows (skip separator lines)
    rows = []
    for line in lines[start_idx:]:
        stripped = line.strip()
        # Skip empty lines and separator lines
        if not stripped:
            continue
        # Stop at markdown heading
        if re.match(r'^#+\s', stripped):
            break
        # Skip separator lines (only contain pipes, dashes, colons, spaces)
        if re.match(r'^\|[\s\-:|]+\|$', stripped):
            continue
        # Add data rows
        if re.match(r'^\|.+\|', stripped):
            rows.append(stripped)
        # Stop at significant non-table content
        elif not stripped.startswith('|') and len(stripped) > 10:
            break

    return rows


def _validate_table_content(output: MarkdownText) -> Tuple[bool, Optional[str]]:
    """Check that table rows have meaningful content in key columns."""
    rows = _extract_policy_table_rows(output)

    if not rows:
        return True, None  # No rows to validate (other checks will catch this)

    for i, row in enumerate(rows):
        # Split by | and get cells (first and last are empty due to leading/trailing |)
        cells = row.split('|')
        # Remove first and last empty cells
        if len(cells) > 2:
            cells = cells[1:-1]
        cells = [cell.strip() for cell in cells]

        if len(cells) >= 5:
            source_name = cells[0]
            key_excerpt = cells[2]

            # Check for substantive content (not just whitespace or single characters)
            if not source_name or len(source_name) < 2:
                return False, f"Row {i+1} has empty or insufficient Source Name"
            if not key_excerpt or len(key_excerpt) < 5:
                return False, f"Row {i+1} has empty or insufficient Key Excerpt"

    return True, None


def _validate_link_column(output: MarkdownText) -> Tuple[bool, Optional[str]]:
    """Check that Link column uses 'N/A' convention for missing links."""
    rows = _extract_policy_table_rows(output)

    if not rows:
        return True, None  # No rows to validate

    for i, row in enumerate(rows):
        # Split by | and get cells (first and last are empty due to leading/trailing |)
        cells = row.split('|')
        # Remove first and last empty cells
        if len(cells) > 2:
            cells = cells[1:-1]
        cells = [cell.strip() for cell in cells]

        if len(cells) >= 5:
            link_cell = cells[4]

            # If not a URL and not empty, should be N/A
            if link_cell and not re.match(r'^https?://', link_cell, re.IGNORECASE):
                if not re.match(r'^n/?a$', link_cell, re.IGNORECASE):
                    return False, f"Row {i+1} Link column should be a URL or 'N/A', found: '{link_cell}'"

    return True, None


def _validate_url_reachability(output: MarkdownText) -> Tuple[bool, Optional[str]]:
    """Check that URLs in Link column are reachable (return HTTP 2xx or 3xx status).

    This validation helps detect hallucinated URLs that agents may fabricate
    by pattern-matching instead of using web search tools.
    """
    rows = _extract_policy_table_rows(output)

    if not rows:
        return True, None  # No rows to validate

    unreachable_urls = []

    for i, row in enumerate(rows):
        # Split by | and get cells
        cells = row.split('|')
        if len(cells) > 2:
            cells = cells[1:-1]
        cells = [cell.strip() for cell in cells]

        if len(cells) >= 5:
            link_cell = cells[4]

            # Only check actual URLs, skip N/A entries
            if link_cell and re.match(r'^https?://', link_cell, re.IGNORECASE):
                try:
                    # HEAD request is faster than GET for checking existence
                    # Timeout of 10 seconds, disable SSL verification for known HKMA cert issues
                    response = requests.head(
                        link_cell,
                        timeout=10,
                        allow_redirects=True,
                        verify=False  # Disable SSL verification due to HKMA server issues
                    )

                    # If HEAD fails, try GET (some servers don't support HEAD)
                    if response.status_code >= 400:
                        response = requests.get(
                            link_cell,
                            timeout=10,
                            allow_redirects=True,
                            verify=False
                        )

                    # Accept 2xx and 3xx status codes as valid
                    if response.status_code >= 400:
                        unreachable_urls.append((i+1, link_cell, response.status_code))

                except requests.exceptions.RequestException as e:
                    unreachable_urls.append((i+1, link_cell, f"Error: {str(e)}"))

    if unreachable_urls:
        error_details = "\n".join([
            f"  - Row {row_num}: {url} (Status: {status})"
            for row_num, url, status in unreachable_urls
        ])
        return False, f"Found {len(unreachable_urls)} unreachable URL(s):\n{error_details}"

    return True, None


# --- Task specific check collections -------------------------------------- #

def _retrieve_checks() -> List[CheckDefinition]:
    headers = [
        "Source Name",
        "Section / Clause",
        "Key Excerpt",
        "Relevance to Observation",
        "Link or Reference",
    ]
    return [
        CheckDefinition(
            id="table_present",
            description="Markdown table with required columns exists.",
            evaluator=lambda output, _: (
                _markdown_table_present(output, headers),
                "Missing table or incorrect headers."
                if not _markdown_table_present(output, headers)
                else None,
            ),
        ),
        CheckDefinition(
            id="table_rows",
            description="Table contains at least one policy entry.",
            evaluator=lambda output, _: (
                (_count_policy_table_rows(output) >= 1),
                f"Only {_count_policy_table_rows(output)} row(s) detected in policy table.",
            ),
        ),
        CheckDefinition(
            id="table_content_quality",
            description="Table rows contain meaningful content in Source Name and Key Excerpt columns.",
            evaluator=lambda output, _: _validate_table_content(output),
        ),
        CheckDefinition(
            id="link_column_format",
            description="Link column uses 'N/A' for missing links or contains valid URLs.",
            evaluator=lambda output, _: _validate_link_column(output),
        ),
        CheckDefinition(
            id="url_reachability",
            description="URLs in Link column are reachable (HTTP 2xx/3xx status) - prevents hallucinated URLs.",
            evaluator=lambda output, _: _validate_url_reachability(output),
            hint="This check detects fabricated URLs that agents may generate by pattern-matching. "
                 "If this fails, the agent likely hallucinated URLs instead of using web search tools."
        ),
        CheckDefinition(
            id="critical_requirements",
            description="Includes bullet list summarising top three critical requirements.",
            evaluator=lambda output, _: (
                _bullet_list_after_phrase(output, "critical requirements", 3),
                "Unable to locate bullet list titled 'critical requirements'.",
            ),
        ),
        CheckDefinition(
            id="hkma_reference",
            description="Mentions HKMA or relevant regulatory authority.",
            evaluator=lambda output, _: (
                _contains_any(output, ["HKMA", "Hong Kong Monetary Authority"]),
                "No explicit HKMA reference found.",
            ),
        ),
        CheckDefinition(
            id="sfc_reference",
            description="Mentions SFC or relevant regulatory authority.",
            evaluator=lambda output, _: (
                _contains_any(output, ["SFC", "Securities and Futures Commission"]),
                "No explicit SFC reference found.",
            ),
        ),
    ]


def _analyze_checks() -> List[CheckDefinition]:
    return [
        CheckDefinition(
            id="status_section",
            description="Contains an explicit compliance status section.",
            evaluator=lambda output, _: (
                _section_present(output, "Compliance Status")
                or _contains_any(output, ["Compliance Status Assessment"]),
                "Missing compliance status section.",
            ),
        ),
        CheckDefinition(
            id="status_value",
            description="Classifies status as compliant / non-compliant / partial.",
            evaluator=lambda output, _: (
                _contains_any(output, ["compliant", "non-compliant", "partial"]),
                "Unable to identify compliance classification.",
            ),
        ),
        CheckDefinition(
            id="supporting_evidence",
            description="Includes supporting evidence section with at least two bullet items.",
            evaluator=lambda output, _: (
                _section_present(output, "Supporting Evidence")
                and len(re.findall(r"^[-*]\s+.+", output, re.MULTILINE)) >= 2,
                "Evidence section missing or too few evidence bullets.",
            ),
        ),
        CheckDefinition(
            id="risk_assessment",
            description="Contains a risk assessment section.",
            evaluator=lambda output, _: (
                _section_present(output, "Risk Assessment"),
                "Risk assessment section missing.",
            ),
        ),
        CheckDefinition(
            id="investigation_section",
            description="Identifies areas for further investigation.",
            evaluator=lambda output, _: (
                _section_present(output, "Areas Requiring Further Investigation")
                or _contains_any(output, ["Areas Requiring Further Investigation", "Areas Requiring Clarification"]),
                "Missing further investigation section.",
            ),
        ),
        CheckDefinition(
            id="policy_table_present",
            description="Carries forward the policy table from Task 1.",
            evaluator=lambda output, _: (
                _markdown_table_present(
                    output,
                    ["Source Name", "Section / Clause", "Key Excerpt", "Relevance to Observation", "Link or Reference"],
                ),
                "Policy table not found in analysis output.",
            ),
        ),
    ]


def _review_checks() -> List[CheckDefinition]:
    return [
        CheckDefinition(
            id="adequacy_assessment",
            description="States overall adequacy of compliance analysis.",
            evaluator=lambda output, _: (
                _contains_any(output, ["adequate", "needs revision", "satisfactory", "unsatisfactory"]),
                "No adequacy verdict detected.",
            ),
        ),
        CheckDefinition(
            id="deficiencies",
            description="Lists concrete deficiencies or unclear areas.",
            evaluator=lambda output, _: (
                len(re.findall(r"(?i)(deficien|gap|weakness|unclear)", output)) > 0,
                "Could not find deficiency references.",
            ),
        ),
        CheckDefinition(
            id="recommendations",
            description="Provides recommended actions or clarifications.",
            evaluator=lambda output, _: (
                len(re.findall(r"(?i)(recommend|action|address)", output)) > 0,
                "No actionable recommendation language detected.",
            ),
        ),
        CheckDefinition(
            id="readiness_verdict",
            description="Includes a final readiness verdict (ready / needs revision).",
            evaluator=lambda output, _: (
                _contains_any(output, ["ready for approval", "needs revision", "revision required"]),
                "Missing explicit readiness verdict.",
            ),
        ),
    ]


retrieve_policies_checks = _retrieve_checks()
analyze_compliance_checks = _analyze_checks()
review_analysis_checks = _review_checks()


def run_checks(task_name: str, output: MarkdownText, checks: List[CheckDefinition]) -> TaskEvaluation:
    """Evaluate a task output against a suite of checks and compute a score."""
    evaluation = TaskEvaluation(task_name=task_name)
    if not checks:
        evaluation.score = 1.0
        return evaluation

    passed = 0
    for check in checks:
        ok, notes = check.run(output, {})
        if ok:
            evaluation.passed.append(check.id)
            passed += 1
        else:
            evaluation.failed.append((check.id, notes))

    evaluation.score = round(passed / len(checks), 2)
    return evaluation
