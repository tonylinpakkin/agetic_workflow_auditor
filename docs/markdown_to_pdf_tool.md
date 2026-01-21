# MarkdownToPDFTool Documentation

## Overview

The `MarkdownToPDFTool` is a custom CrewAI tool that converts markdown files containing policy retrieval tables into professionally formatted PDF documents. It's specifically designed for the Internal Audit Validation System's 8-column policy tables.

## Features

- **Clickable Hyperlinks**: Automatically converts markdown links `[text](url)` to clickable hyperlinks in the PDF
- **Professional Styling**:
  - Landscape A4 orientation optimized for wide tables
  - Color-coded headers (blue background with white text)
  - Alternating row colors for better readability
  - Proper text wrapping in cells
  - Consistent font sizing and spacing
- **HTML Entity Escaping**: Safely handles special characters and quotes in text
- **Automatic Layout**: Intelligently sizes columns based on policy table structure

## Usage

### In CrewAI Agents

The tool is available to the **Policy Aggregator** agent during the `revise_policy_retrieval` task.

**Tool Parameters:**
- `markdown_file_path` (required): Path to the markdown file to convert
- `pdf_output_path` (optional): Path for the output PDF file. If not provided, creates a PDF with the same name as the markdown file

**Example Usage in Agent:**
```python
{
    "markdown_file_path": "output/20251118_141308/policy_retrieval_final.md",
    "pdf_output_path": "output/20251118_141308/policy_retrieval_final.pdf"
}
```

Or with automatic naming:
```python
{
    "markdown_file_path": "output/20251118_141308/policy_retrieval_final.md"
}
```

### Standalone Usage

You can also use the tool directly in Python:

```python
from internal_audit_validation_system.tools.custom_tool import MarkdownToPDFTool

# Create tool instance
tool = MarkdownToPDFTool()

# Convert markdown to PDF
result = tool._run(
    markdown_file_path="output/20251118_141308/policy_retrieval_final.md"
)

print(result)  # "Success: PDF created at output/20251118_141308/policy_retrieval_final.pdf"
```

### Command Line Usage

Use the standalone script for one-off conversions:

```bash
cd "/Users/bradb/Internal Audit Validation System"
python simple_md_to_pdf.py "output/20251118_141308/policy_retrieval_final.md"
```

## Expected Markdown Format

The tool expects markdown files with tables containing these columns:

| Column | Description |
|--------|-------------|
| Source Name | Regulation identifier (e.g., "HKMA SPM OR-1") |
| Section / Clause | Specific section reference (e.g., "3.2.4") |
| Key Excerpt | Verbatim quote from the policy |
| Relevance to Observation | How the policy relates to the audit observation |
| Document Path / URL | Source location (can include markdown links) |
| Effective Date | When the policy took effect |
| Confidence | Relevance certainty (High/Med/Low) |
| Link or Reference | Additional reference or "N/A" |

**Example Markdown:**
```markdown
| Source Name | Section / Clause | Key Excerpt | Relevance to Observation | Document Path / URL | Effective Date | Confidence | Link or Reference |
|-------------|------------------|-------------|--------------------------|---------------------|----------------|------------|-------------------|
| HKMA Circular | Section 1.2 | "Institutions must..." | Addresses requirements | [HKMA Document](https://example.com/doc.pdf) | 2023-01-15 | High | N/A |
```

## PDF Output Specifications

**Page Settings:**
- Format: Landscape A4 (297mm × 210mm)
- Margins: 1.5cm top/bottom, 1cm left/right

**Typography:**
- Title: 16pt, dark blue (#2c3e50)
- Headers: 8pt, bold, white text on blue background (#3498db)
- Cell content: 7pt, regular weight
- Line spacing: 9pt leading

**Table Styling:**
- Column widths: 3cm, 1.8cm, 5cm, 3.5cm, 4.5cm, 2cm, 1.5cm, 2cm
- Grid lines: 0.5pt grey borders
- Row colors: White and light grey (#f8f9fa) alternating
- Hyperlinks: Blue, underlined

## Technical Implementation

### Dependencies

The tool requires these Python packages:
- `reportlab` - PDF generation
- `crewai` - Tool framework integration

Install dependencies:
```bash
pip install reportlab crewai
```

### Key Methods

1. **`_parse_markdown_table(md_content)`**: Extracts table data from markdown
2. **`_process_cell_content(cell_text)`**: Converts markdown links to HTML and escapes special characters
3. **`_run(markdown_file_path, pdf_output_path)`**: Main execution method

### Error Handling

The tool handles common errors gracefully:
- **File not found**: Returns error message with file path
- **No table found**: Returns error if markdown doesn't contain expected table structure
- **Parsing errors**: Catches and reports any exceptions during conversion

## Integration with Workflow

The tool is integrated into the workflow at **Stage 4: Policy Revision**:

1. Policy Aggregator completes final markdown report
2. Agent optionally uses MarkdownToPDFTool to create PDF version
3. Both markdown and PDF outputs are available in timestamped output directory

**Task Configuration** (from `tasks.yaml`):
```yaml
revise_policy_retrieval:
  expected_output: |
    ...
    OPTIONAL: After completing the markdown report, you may use the "Convert Markdown to PDF" tool
    to create a professionally formatted PDF version of the final report.
```

## Testing

Test the tool with the included test script:

```bash
cd "/Users/bradb/Internal Audit Validation System"
python test_md_to_pdf_tool.py
```

Expected output:
```
Testing MarkdownToPDFTool with file: output/20251118_141308/policy_retrieval_final.md
Result: Success: PDF created at output/20251118_141308/policy_retrieval_final.pdf
```

## Troubleshooting

### Common Issues

**Issue**: "Error: No policy table found in markdown file"
- **Cause**: Markdown doesn't contain a table with "Source Name" header
- **Solution**: Ensure markdown follows expected format with 8-column table

**Issue**: PDF has broken links
- **Cause**: Markdown links not properly formatted
- **Solution**: Use standard markdown link syntax: `[text](url)`

**Issue**: Text is truncated in cells
- **Cause**: Very long content exceeds cell width
- **Solution**: Tool automatically truncates text over 200 characters for non-link cells

**Issue**: Import errors when running
- **Cause**: Missing dependencies
- **Solution**: Run `pip install reportlab` to install required packages

## Future Enhancements

Possible improvements:
- Support for multiple table formats beyond 8-column structure
- Configurable column widths based on content analysis
- Support for embedded images in markdown
- Multi-page tables with automatic page breaks
- Custom styling themes (colors, fonts)
- Summary statistics footer (e.g., "X policies from Y sources")

## References

- Tool implementation: [`custom_tool.py`](../src/internal_audit_validation_system/tools/custom_tool.py)
- Agent configuration: [`crew.py`](../src/internal_audit_validation_system/crew.py)
- Task configuration: [`tasks.yaml`](../src/internal_audit_validation_system/config/tasks.yaml)
- Standalone script: [`simple_md_to_pdf.py`](../simple_md_to_pdf.py)
