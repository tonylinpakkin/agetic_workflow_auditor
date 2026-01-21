# Quick Start: Markdown to PDF Conversion

## For Users

### Command Line (Simplest)
```bash
cd "/Users/bradb/Internal Audit Validation System"
python simple_md_to_pdf.py "output/20251118_141308/policy_retrieval_final.md"
```

**Result**: Creates `policy_retrieval_final.pdf` in the same directory

### Python Script
```python
from src.internal_audit_validation_system.tools.custom_tool import MarkdownToPDFTool

tool = MarkdownToPDFTool()
result = tool._run("output/20251118_141308/policy_retrieval_final.md")
print(result)
```

## For Agents

The `policy_aggregator` agent can use this tool during the `revise_policy_retrieval` task:

```python
{
    "markdown_file_path": "output/20251118_141308/policy_retrieval_final.md",
    "pdf_output_path": "output/20251118_141308/policy_retrieval_final.pdf"
}
```

## Expected Input Format

Markdown file with table:
```markdown
| Source Name | Section / Clause | Key Excerpt | Relevance to Observation | Document Path / URL | Effective Date | Confidence | Link or Reference |
|-------------|------------------|-------------|--------------------------|---------------------|----------------|------------|-------------------|
| HKMA Circular | Section 1.2 | "Quote..." | Explanation | [Link Text](https://url.com) | 2023-01-15 | High | N/A |
```

## Output Features

✅ Clickable hyperlinks from markdown links
✅ Professional blue headers
✅ Alternating row colors
✅ Landscape A4 format
✅ Automatic text wrapping

## Troubleshooting

**Problem**: "No policy table found"
**Solution**: Ensure markdown has a table with "Source Name" column

**Problem**: Links not clickable
**Solution**: Use proper markdown syntax: `[text](url)`

**Problem**: Import errors
**Solution**: Run `pip install reportlab`

## More Information

- Full documentation: [`docs/markdown_to_pdf_tool.md`](markdown_to_pdf_tool.md)
- Integration summary: [`TOOL_INTEGRATION_SUMMARY.md`](../TOOL_INTEGRATION_SUMMARY.md)
- Tool source code: [`src/internal_audit_validation_system/tools/custom_tool.py`](../src/internal_audit_validation_system/tools/custom_tool.py)
