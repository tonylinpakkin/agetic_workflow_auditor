# Output Configuration for Timestamped Files

## Overview

The Internal Audit Validation System has been configured to save all markdown output files to the `output/` directory with unique timestamps. This prevents files from being overwritten on each run and maintains a history of all audit validation runs.

## How It Works

### Automatic Timestamping

When you run the system using `python main.py run`, the following happens:

1. **Timestamp Generation**: A timestamp is generated in the format `YYYYMMDD_HHMMSS` (e.g., `20251018_175512`)
2. **Output Directory Creation**: The `output/` directory is created if it doesn't exist
3. **Dynamic Path Updates**: All task output file paths are updated to include the timestamp

### Output Files

Each run generates the following files in the `output/` directory:

| Base Filename | Task | Example Output |
|---------------|------|----------------|
| `policy_retrieval_{timestamp}.md` | retrieve_relevant_policies | `policy_retrieval_20251018_175512.md` |
| `retrieval_review_{timestamp}.md` | reflect_policy_retrieval | `retrieval_review_20251018_175512.md` |
| `policy_retrieval_final_{timestamp}.md` | revise_policy_retrieval | `policy_retrieval_final_20251018_175512.md` |
| `review_report_{timestamp}.md` | review_compliance_analysis | `review_report_20251018_175512.md` |

### File References

The system automatically updates task descriptions to reference the correct timestamped files:

- **reflect_policy_retrieval** task reads from `output/policy_retrieval_{timestamp}.md`
- **revise_policy_retrieval** task reads from:
  - `output/policy_retrieval_{timestamp}.md`
  - `output/retrieval_review_{timestamp}.md`

## Benefits

1. **No Overwrites**: Each run preserves its output, allowing you to compare results across different runs
2. **Audit Trail**: Complete history of all validation runs with timestamps
3. **Easy Comparison**: Compare how the system performed on the same observation over time
4. **Data Integrity**: Previous results are never lost or modified

## File Location

All output files are saved to: `/Users/bradb/Downloads/Internal Audit Validation System v1/output/`

## Configuration Files Modified

1. **[config/tasks.yaml](src/internal_audit_validation_system/config/tasks.yaml)**: Updated base paths to use `output/` directory
2. **[main.py](src/internal_audit_validation_system/main.py)**: Added timestamp generation and dynamic path updating

## Example Run

```bash
# Run the system
python main.py run

# Output files created:
# - output/policy_retrieval_20251018_180000.md
# - output/retrieval_review_20251018_180000.md
# - output/policy_retrieval_final_20251018_180000.md
# - output/review_report_20251018_180000.md (if that task runs)
```

## Notes

- All files from the same run share the same timestamp
- The timestamp is generated when `run()` is called, before the crew starts
- Task descriptions are dynamically updated to reference the correct timestamped files
- The evaluation files in `evaluation/` continue to use "latest" naming convention
