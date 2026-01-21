from internal_audit_validation_system.evaluation.criteria import (
    analyze_compliance_checks,
    retrieve_policies_checks,
    review_analysis_checks,
    run_checks,
)


def test_retrieve_checks_success():
    sample_output = """| Source Name | Section / Clause | Key Excerpt | Relevance to Observation | Link or Reference |
|-------------|-----------------|-------------|--------------------------|-------------------|
| HKMA Guideline | 1.1 | Enforces risk controls. | Demonstrates regulatory requirement. | https://example.com |
| HKMA Circular | 3.2 | Requires backup procedures. | Directly relevant to missing backups. | https://example.com |
| SFC Code of Conduct | 12.1 | Licensed persons must maintain proper records. | Demonstrates regulatory requirement. | https://example.com |

### Top Three Critical Requirements
- Maintain documented backup procedures.
- Perform periodic risk assessments.
- Evidence regulatory compliance to HKMA and SFC.
"""
    result = run_checks("retrieve_relevant_policies", sample_output, retrieve_policies_checks)
    assert result.score == 1.0


def test_retrieve_checks_single_policy():
    """Test that a single policy entry is acceptable."""
    sample_output = """| Source Name | Section / Clause | Key Excerpt | Relevance to Observation | Link or Reference |
|-------------|-----------------|-------------|--------------------------|-------------------|
| HKMA Guideline | 1.1 | Enforces risk controls. | Demonstrates regulatory requirement. | N/A |

### Top Three Critical Requirements
- Maintain documented backup procedures.
- Perform periodic risk assessments.
- Evidence regulatory compliance to HKMA and Securities and Futures Commission.
"""
    result = run_checks("retrieve_relevant_policies", sample_output, retrieve_policies_checks)
    assert result.score == 1.0
    assert all(check_id != "table_rows" for check_id, _ in result.failed)


def test_retrieve_checks_na_link():
    """Test that N/A is accepted for missing links."""
    sample_output = """| Source Name | Section / Clause | Key Excerpt | Relevance to Observation | Link or Reference |
|-------------|-----------------|-------------|--------------------------|-------------------|
| HKMA Guideline | 1.1 | Enforces risk controls and audit procedures. | Demonstrates regulatory requirement. | N/A |
| Internal Policy | 2.1 | Document retention rules. | Addresses documentation gaps. | https://example.com |

### Critical Requirements
- Maintain documented backup procedures.
- Perform periodic risk assessments.
- Evidence regulatory compliance to HKMA.
"""
    result = run_checks("retrieve_relevant_policies", sample_output, retrieve_policies_checks)
    assert all(check_id != "link_column_format" for check_id, _ in result.failed)


def test_retrieve_checks_critical_requirements_with_heading():
    """Test that critical requirements work with markdown heading."""
    sample_output = """| Source Name | Section / Clause | Key Excerpt | Relevance to Observation | Link or Reference |
|-------------|-----------------|-------------|--------------------------|-------------------|
| HKMA Guideline | 1.1 | Enforces risk controls. | Demonstrates regulatory requirement. | https://example.com |

## Top Three Critical Requirements

- Maintain documented backup procedures.
- Perform periodic risk assessments.
- Evidence regulatory compliance to HKMA.
"""
    result = run_checks("retrieve_relevant_policies", sample_output, retrieve_policies_checks)
    assert all(check_id != "critical_requirements" for check_id, _ in result.failed)


def test_retrieve_checks_multiple_tables():
    """Test that row counting doesn't get confused by multiple tables."""
    sample_output = """
Here's some other table:

| Column A | Column B |
|----------|----------|
| Data 1   | Data 2   |
| Data 3   | Data 4   |

And here's the policy table:

| Source Name | Section / Clause | Key Excerpt | Relevance to Observation | Link or Reference |
|-------------|-----------------|-------------|--------------------------|-------------------|
| HKMA Guideline | 1.1 | Enforces risk controls. | Demonstrates regulatory requirement. | https://example.com |

### Critical Requirements
- Maintain documented backup procedures.
- Perform periodic risk assessments.
- Evidence regulatory compliance to Hong Kong Monetary Authority.
"""
    result = run_checks("retrieve_relevant_policies", sample_output, retrieve_policies_checks)
    # Should have exactly 1 policy row despite other table
    passed_table_rows = "table_rows" in result.passed
    assert passed_table_rows, "Should correctly count 1 policy row despite multiple tables"


def test_retrieve_checks_empty_cells():
    """Test that empty critical cells are caught."""
    sample_output = """| Source Name | Section / Clause | Key Excerpt | Relevance to Observation | Link or Reference |
|-------------|-----------------|-------------|--------------------------|-------------------|
|  | 1.1 |  | Demonstrates regulatory requirement. | N/A |

### Critical Requirements
- Maintain documented backup procedures.
- Perform periodic risk assessments.
- Evidence regulatory compliance to HKMA.
"""
    result = run_checks("retrieve_relevant_policies", sample_output, retrieve_policies_checks)
    assert any(check_id == "table_content_quality" for check_id, _ in result.failed)


def test_retrieve_checks_invalid_link_format():
    """Test that invalid link format is caught."""
    sample_output = """| Source Name | Section / Clause | Key Excerpt | Relevance to Observation | Link or Reference |
|-------------|-----------------|-------------|--------------------------|-------------------|
| HKMA Guideline | 1.1 | Enforces risk controls. | Demonstrates regulatory requirement. | see attachment |

### Critical Requirements
- Maintain documented backup procedures.
- Perform periodic risk assessments.
- Evidence regulatory compliance to HKMA.
"""
    result = run_checks("retrieve_relevant_policies", sample_output, retrieve_policies_checks)
    assert any(check_id == "link_column_format" for check_id, _ in result.failed)


def test_analyze_checks_detect_missing_policy_table():
    sample_output = """## Compliance Status Assessment
Non-compliant.

## Supporting Evidence from Policies
- Policy A demonstrates control failure.
- Policy B reinforces requirement.

## Risk Assessment
High regulatory exposure.

## Areas Requiring Further Investigation or Clarification
- Investigate missing approvals."""
    result = run_checks("analyze_compliance_status", sample_output, analyze_compliance_checks)
    # missing policy table should drop the score
    assert any(check_id == "policy_table_present" for check_id, _ in result.failed)


def test_review_checks_require_final_verdict():
    sample_output = """Overall adequacy assessment indicates major gaps.

Key gaps:
- Missing evidence.
- Weak linkage to policy.

Recommended actions:
- Provide supporting citations."""
    result = run_checks("review_compliance_analysis", sample_output, review_analysis_checks)
    assert any(check_id == "readiness_verdict" for check_id, _ in result.failed)


def test_retrieve_checks_sfc_coverage():
    """Test that SFC reference is detected for cross-regulator coverage."""
    sample_output = """| Source Name | Section / Clause | Key Excerpt | Relevance to Observation | Link or Reference |
|-------------|-----------------|-------------|--------------------------|-------------------|
| SFC Code of Conduct | 12.1 | Licensed persons must act in best interests of clients. | Demonstrates regulatory requirement. | https://example.com |
| HKMA Guideline | 1.1 | Enforces risk controls. | Demonstrates regulatory requirement. | https://example.com |

### Top Three Critical Requirements
- Maintain documented backup procedures.
- Perform periodic risk assessments.
- Evidence regulatory compliance to Securities and Futures Commission.
"""
    result = run_checks("retrieve_relevant_policies", sample_output, retrieve_policies_checks)
    assert result.score == 1.0
    assert "sfc_reference" in result.passed
