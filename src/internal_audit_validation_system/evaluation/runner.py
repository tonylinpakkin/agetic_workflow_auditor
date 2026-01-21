from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Dict, Iterable, List

from internal_audit_validation_system.evaluation.criteria import (
    EvaluateResult,
    TaskEvaluation,
    analyze_compliance_checks,
    retrieve_policies_checks,
    review_analysis_checks,
    run_checks,
)


TASK_TO_CHECKS = {
    "retrieve_relevant_policies": retrieve_policies_checks,
    "analyze_compliance_status": analyze_compliance_checks,
    "review_compliance_analysis": review_analysis_checks,
}


def evaluate_outputs(
    audit_observation: str,
    task_outputs: Dict[str, str],
) -> EvaluateResult:
    """Run structural checks across all task outputs."""
    results: List[TaskEvaluation] = []
    for task_name, checks in TASK_TO_CHECKS.items():
        content = task_outputs.get(task_name, "")
        evaluation = run_checks(task_name, content, checks)
        results.append(evaluation)
    return EvaluateResult(audit_observation=audit_observation, task_results=results)


def _format_console_report(result: EvaluateResult) -> str:
    lines: List[str] = []
    lines.append(f"Audit observation: {result.audit_observation}")
    for task in result.task_results:
        percent = int(task.score * 100)
        lines.append(f"- {task.task_name}: {percent}% ({len(task.passed)} passed / {len(task.failed)} failed)")
        if task.failed:
            for check_id, notes in task.failed:
                note_text = f" - {check_id}: {notes or 'no details'}"
                lines.append(note_text)
    return "\n".join(lines)


def _load_json_payload(path: Path) -> Iterable[Dict[str, object]]:
    data = json.loads(path.read_text())
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return [data]
    raise ValueError("JSON payload must be an object or array of objects.")


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate crew task outputs for structural quality issues.",
    )
    parser.add_argument(
        "--input-json",
        required=True,
        help="Path to a JSON file with task outputs.",
    )
    parser.add_argument(
        "--write-report",
        help="Optional path to write the JSON evaluation report.",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    entries = _load_json_payload(Path(args.input_json))
    results: List[EvaluateResult] = []
    for entry in entries:
        try:
            audit_observation = str(entry["audit_observation"])
            outputs = entry.get("outputs") or {}
            if not isinstance(outputs, dict):
                raise TypeError("'outputs' must be a mapping of task name to markdown output.")
            results.append(evaluate_outputs(audit_observation, outputs))
        except KeyError as exc:
            raise KeyError(f"Missing required key in JSON payload: {exc}")

    for result in results:
        print(_format_console_report(result))
        print()

    if args.write_report:
        serialisable = [
            {
                "audit_observation": res.audit_observation,
                "task_results": [task.as_dict() for task in res.task_results],
            }
            for res in results
        ]
        Path(args.write_report).write_text(json.dumps(serialisable, indent=2))

    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
