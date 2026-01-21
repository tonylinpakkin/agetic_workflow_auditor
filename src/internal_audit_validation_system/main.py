#!/usr/bin/env python
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from internal_audit_validation_system.crew import InternalAuditValidationSystemCrew
from internal_audit_validation_system.evaluation.criteria import EvaluateResult
from internal_audit_validation_system.evaluation.runner import evaluate_outputs

# This main file is intended to be a way for you to run your
# crew locally, so refrain from adding unnecessary logic into this file.
# Replace with inputs you want to test with, it will automatically
# interpolate any tasks and agents information

EVALUATION_DIR = Path("evaluation")
EVALUATION_PAYLOAD_PATH = EVALUATION_DIR / "latest_payload.json"
EVALUATION_REPORT_PATH = EVALUATION_DIR / "latest_report.json"
OUTPUT_DIR = Path("output")


def _setup_output_directory_with_timestamp() -> str:
    """Create timestamped output subdirectory and return timestamp string."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Create main output directory if it doesn't exist
    OUTPUT_DIR.mkdir(exist_ok=True)

    # Create timestamped subdirectory
    timestamped_dir = OUTPUT_DIR / timestamp
    timestamped_dir.mkdir(exist_ok=True)

    return timestamp


def _extract_task_markdown(raw_output: Any) -> Dict[str, str]:
    """Normalise crew output into a mapping of task name -> markdown string."""
    if raw_output is None:
        return {}

    if hasattr(raw_output, "model_dump"):
        payload = raw_output.model_dump()
    elif hasattr(raw_output, "to_dict"):
        payload = raw_output.to_dict()
    elif isinstance(raw_output, dict):
        payload = raw_output
    else:
        return {}

    tasks = payload.get("tasks_output") or []
    task_outputs: Dict[str, str] = {}
    for record in tasks:
        task_name = (
            record.get("task_id")
            or record.get("task_name")
            or record.get("name")
            or record.get("id")
        )
        if not task_name:
            continue

        output_block = record.get("output") or {}
        markdown = (
            output_block.get("raw_output")
            or output_block.get("final_output")
            or output_block.get("text")
            or output_block.get("content")
            or ""
        )
        task_outputs[task_name] = str(markdown)

    return task_outputs


def _run_evaluation(crew_output: Any, inputs: Dict[str, Any]) -> Optional[EvaluateResult]:
    """Persist task outputs and execute the evaluation harness."""
    observation = inputs.get("audit_observation", "")
    task_outputs = _extract_task_markdown(crew_output)
    if not task_outputs:
        print("Evaluation skipped: no task outputs found.")
        return None

    EVALUATION_DIR.mkdir(exist_ok=True)

    payload = [
        {
            "audit_observation": observation,
            "outputs": task_outputs,
        }
    ]
    EVALUATION_PAYLOAD_PATH.write_text(json.dumps(payload, indent=2))

    result = evaluate_outputs(observation, task_outputs)
    summary = {
        "audit_observation": result.audit_observation,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "task_results": [task.as_dict() for task in result.task_results],
        "successful": result.successful(),
    }
    EVALUATION_REPORT_PATH.write_text(json.dumps([summary], indent=2))

    print("Evaluation summary:")
    for task in result.task_results:
        percent = int(task.score * 100)
        print(f" - {task.task_name}: {percent}% ({len(task.passed)} passed / {len(task.failed)} failed)")
        for check_id, notes in task.failed:
            if notes:
                print(f"   - {check_id}: {notes}")

    return result


def run():
    """
    Run the crew.
    """
    # Setup output directory and get timestamp
    timestamp = _setup_output_directory_with_timestamp()

    # Create crew instance with timestamp - this will automatically update all task output paths
    crew_instance = InternalAuditValidationSystemCrew(timestamp=timestamp)

    # Get the crew object
    crew_obj = crew_instance.crew()

    inputs = {
        "audit_observation": "Lack of risk assessment procedures for selling investment products."
    }
    crew_output = crew_obj.kickoff(inputs=inputs)
    _run_evaluation(crew_output, inputs)


def train():
    """
    Train the crew for a given number of iterations.
    """
    inputs = {
        "audit_observation": "sample_value"
    }
    try:
        InternalAuditValidationSystemCrew().crew().train(
            n_iterations=int(sys.argv[1]),
            filename=sys.argv[2],
            inputs=inputs,
        )

    except Exception as e:
        raise Exception(f"An error occurred while training the crew: {e}")


def replay():
    """
    Replay the crew execution from a specific task.
    """
    try:
        InternalAuditValidationSystemCrew().crew().replay(task_id=sys.argv[1])

    except Exception as e:
        raise Exception(f"An error occurred while replaying the crew: {e}")


def test():
    """
    Test the crew execution and returns the results.
    """
    inputs = {
        "audit_observation": "sample_value"
    }
    try:
        InternalAuditValidationSystemCrew().crew().test(
            n_iterations=int(sys.argv[1]),
            openai_model_name=sys.argv[2],
            inputs=inputs,
        )

    except Exception as e:
        raise Exception(f"An error occurred while testing the crew: {e}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: main.py <command> [<args>]")
        sys.exit(1)

    command = sys.argv[1]
    if command == "run":
        run()
    elif command == "train":
        train()
    elif command == "replay":
        replay()
    elif command == "test":
        test()
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
