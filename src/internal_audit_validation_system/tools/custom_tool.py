from crewai.tools import BaseTool
from typing import Type, Optional
from pydantic import BaseModel, Field, field_validator
import requests
from bs4 import BeautifulSoup
import warnings
from urllib3.exceptions import InsecureRequestWarning
import io
import os
from pathlib import Path
from PyPDF2 import PdfReader
import re
import html
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT

# Suppress SSL warnings
warnings.filterwarnings('ignore', category=InsecureRequestWarning)


class MyCustomToolInput(BaseModel):
    """Input schema for MyCustomTool."""
    argument: str = Field(..., description="Description of the argument.")

class MyCustomTool(BaseTool):
    name: str = "Name of my tool"
    description: str = (
        "Clear description for what this tool is useful for, your agent will need this information to use it."
    )
    args_schema: Type[BaseModel] = MyCustomToolInput

    def _run(self, argument: str) -> str:
        # Implementation goes here
        return "this is an example of a tool output, ignore it and move along."


class RobustFileReadToolSchema(BaseModel):
    """Input schema for RobustFileReadTool with string 'None' handling."""

    file_path: str = Field(..., description="Mandatory file full path to read the file")
    start_line: Optional[int] = Field(1, description="Line number to start reading from (1-indexed)")
    line_count: Optional[int] = Field(None, description="Number of lines to read. If None, reads the entire file")

    @field_validator('line_count', mode='before')
    @classmethod
    def convert_none_string_line_count(cls, v):
        """Convert string 'None' to actual None for line_count field"""
        if isinstance(v, str) and v.lower() in ('none', 'null', ''):
            return None
        return v

    @field_validator('start_line', mode='before')
    @classmethod
    def convert_none_string_start_line(cls, v):
        """Convert string 'None' to 1 for start_line field (default value)"""
        if isinstance(v, str) and v.lower() in ('none', 'null', ''):
            return 1
        return v


class SecureWebScraperInput(BaseModel):
    """Input schema for SecureWebScraper."""
    website_url: str = Field(..., description="The URL of the website to scrape")

class SecureWebScraperTool(BaseTool):
    name: str = "Secure Web Scraper (SSL-tolerant)"
    description: str = (
        "A web scraping tool configured to handle regulatory and official websites that may have SSL "
        "certificate verification issues. Use this to read content from Hong Kong regulators (e.g., SFC, HKMA, HKEX), "
        "industry bodies (e.g., HKAB), and other authorities' policy pages that fail standard TLS verification."
    )
    args_schema: Type[BaseModel] = SecureWebScraperInput

    def _run(self, website_url: str) -> str:
        try:
            # Disable SSL verification for problematic government sites
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
            response = requests.get(website_url, verify=False, headers=headers, timeout=30)
            response.raise_for_status()

            # Parse the HTML content
            soup = BeautifulSoup(response.text, 'html.parser')

            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()

            # Get text and clean it up
            text = soup.get_text()
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = '\n'.join(chunk for chunk in chunks if chunk)

            return text[:10000]  # Limit to first 10000 characters

        except Exception as e:
            return f"Error scraping website: {str(e)}"


class PDFDownloadToolInput(BaseModel):
    """Input schema for PDFDownloadTool."""
    pdf_url: str = Field(..., description="The URL of the PDF document to download and extract text from")

class PDFDownloadTool(BaseTool):
    name: str = "Download and Extract PDF Content"
    description: str = (
        "Downloads a PDF document from a URL and extracts its text content. "
        "Use this tool when you need to read the contents of PDF files from web sources, "
        "such as regulatory documents, policy papers, or compliance guidelines from HKMA or other authorities. "
        "The tool handles SSL certificate issues and returns the extracted text content."
    )
    args_schema: Type[BaseModel] = PDFDownloadToolInput

    def _run(self, pdf_url: str) -> str:
        try:
            # Download the PDF with SSL verification disabled for problematic sites
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
            response = requests.get(pdf_url, verify=False, headers=headers, timeout=60)
            response.raise_for_status()

            # Check if the response is actually a PDF
            content_type = response.headers.get('Content-Type', '')
            if 'application/pdf' not in content_type and not pdf_url.lower().endswith('.pdf'):
                return f"Error: The URL does not appear to point to a PDF document. Content-Type: {content_type}"

            # Read the PDF from the downloaded content
            pdf_file = io.BytesIO(response.content)
            pdf_reader = PdfReader(pdf_file)

            # Extract text from all pages
            text_content = []
            num_pages = len(pdf_reader.pages)

            for page_num in range(num_pages):
                page = pdf_reader.pages[page_num]
                text = page.extract_text()
                if text:
                    text_content.append(f"--- Page {page_num + 1} ---\n{text}")

            if not text_content:
                return "Error: No text could be extracted from the PDF. The PDF might be image-based or encrypted."

            full_text = "\n\n".join(text_content)

            # Limit output to prevent token overflow (approximately 50000 characters)
            if len(full_text) > 50000:
                full_text = full_text[:50000] + f"\n\n[Content truncated. Total pages: {num_pages}]"

            return full_text

        except requests.exceptions.RequestException as e:
            return f"Error downloading PDF from {pdf_url}: {str(e)}"
        except Exception as e:
            return f"Error processing PDF: {str(e)}"


class RobustFileReadTool(BaseTool):
    """A tool for reading LOCAL file contents with robust validation that handles string 'None' values.

    IMPORTANT: This tool is for reading LOCAL files from the filesystem ONLY.
    Do NOT use this tool with URLs or web addresses. For PDF URLs, use PDFDownloadTool instead.

    This tool extends the base FileReadTool functionality but adds validation to handle
    cases where LLMs pass the string 'None' instead of actual None for optional parameters.

    Args:
        file_path (Optional[str]): Path to the LOCAL file to be read. If provided,
            this becomes the default file path for the tool.
    """

    name: str = "Read a file's content"
    description: str = (
        "A tool that reads the content of a LOCAL file from the filesystem. "
        "IMPORTANT: This tool ONLY works with local file paths (e.g., /path/to/file.txt or file.txt), NOT URLs. "
        "You can provide either absolute paths (e.g., /full/path/to/file.txt) or relative paths (e.g., file.txt, output/file.md). "
        "Relative paths will be resolved from the current working directory. "
        "If you need to read a PDF from a URL, use 'Download and Extract PDF Content' tool instead. "
        "To use this tool, provide a 'file_path' parameter with the path to the local file you want to read. "
        "Optionally, provide 'start_line' to start reading from a specific line and 'line_count' to limit the number of lines read."
    )
    args_schema: Type[BaseModel] = RobustFileReadToolSchema
    file_path: Optional[str] = None

    def __init__(self, file_path: Optional[str] = None, **kwargs):
        """Initialize the RobustFileReadTool.

        Args:
            file_path (Optional[str]): Path to the local file to be read.
            **kwargs: Additional keyword arguments passed to BaseTool.
        """
        if file_path is not None:
            kwargs["description"] = (
                f"A tool that reads local file content. The default file is {file_path}, but you can provide "
                f"a different 'file_path' parameter to read another file. You can also specify 'start_line' "
                f"and 'line_count' to read specific parts of the file."
            )
        super().__init__(**kwargs)
        self.file_path = file_path

    def _run(
        self,
        file_path: Optional[str] = None,
        start_line: Optional[int] = 1,
        line_count: Optional[int] = None,
    ) -> str:
        file_path = file_path or self.file_path
        start_line = start_line or 1
        line_count = line_count or None

        if file_path is None:
            return (
                "Error: No file path provided. Please provide a file path either in the constructor or as an argument."
            )

        # Check if user is trying to pass a URL
        if file_path.startswith('http://') or file_path.startswith('https://'):
            return (
                f"Error: This tool only reads LOCAL files. You provided a URL: {file_path}\n"
                "For PDF URLs, use the 'Download and Extract PDF Content' tool instead."
            )

        # Convert relative paths to absolute paths
        # This allows the tool to work with both relative and absolute paths
        if not os.path.isabs(file_path):
            file_path = os.path.abspath(file_path)

        try:
            with open(file_path, "r") as file:
                if start_line == 1 and line_count is None:
                    return file.read()

                start_idx = max(start_line - 1, 0)

                selected_lines = [
                    line
                    for i, line in enumerate(file)
                    if i >= start_idx and (line_count is None or i < start_idx + line_count)
                ]

                if not selected_lines and start_idx > 0:
                    return f"Error: Start line {start_line} exceeds the number of lines in the file."

                return "".join(selected_lines)
        except FileNotFoundError:
            return f"Error: File not found at path: {file_path}"
        except PermissionError:
            return f"Error: Permission denied when trying to read file: {file_path}"
        except Exception as e:
            return f"Error: Failed to read file {file_path}. {str(e)}"


class MarkdownToPDFToolInput(BaseModel):
    """Input schema for MarkdownToPDFTool."""
    markdown_file_path: str = Field(..., description="Path to the markdown file to convert to PDF")
    pdf_output_path: Optional[str] = Field(None, description="Optional path for the output PDF file. If not provided, will create PDF with same name as markdown file")


class MarkdownToPDFTool(BaseTool):
    name: str = "Convert Markdown to PDF"
    description: str = (
        "Converts a markdown file containing policy tables to a professionally formatted PDF document. "
        "This tool is specifically designed for policy retrieval reports with tables containing columns like "
        "Source Name, Section/Clause, Key Excerpt, Relevance, Document Path/URL, Effective Date, Confidence, and Link. "
        "The generated PDF includes: clickable hyperlinks from markdown links, landscape orientation for wide tables, "
        "professional styling with color-coded headers, alternating row colors, and proper text wrapping. "
        "Use this tool to create final deliverable PDF reports from markdown outputs."
    )
    args_schema: Type[BaseModel] = MarkdownToPDFToolInput

    def _parse_markdown_table(self, md_content: str):
        """Extract table data from markdown content."""
        lines = md_content.strip().split('\n')

        # Find the table
        table_start = None
        for i, line in enumerate(lines):
            if '|' in line and 'Source Name' in line:
                table_start = i
                break

        if table_start is None:
            return None, []

        # Parse header
        header_line = lines[table_start]
        headers = [cell.strip() for cell in header_line.split('|')[1:-1]]

        # Skip separator line
        data_start = table_start + 2

        # Parse data rows
        table_data = [headers]
        for line in lines[data_start:]:
            if not line.strip() or not line.startswith('|'):
                break
            cells = [cell.strip() for cell in line.split('|')[1:-1]]
            table_data.append(cells)

        return headers, table_data

    def _process_cell_content(self, cell_text: str) -> str:
        """Process cell content: escape HTML entities and convert markdown links."""
        # First, check if this is a markdown link
        link_match = re.match(r'\[([^\]]+)\]\(([^\)]+)\)', cell_text)
        if link_match:
            link_text = html.escape(link_match.group(1))
            link_url = link_match.group(2)
            return f'<link href="{link_url}" color="blue"><u>{link_text}</u></link>'
        else:
            # Escape HTML entities for plain text
            return html.escape(cell_text)

    def _run(self, markdown_file_path: str, pdf_output_path: Optional[str] = None) -> str:
        try:
            # Resolve file paths
            md_path = Path(markdown_file_path)
            if not md_path.exists():
                return f"Error: Markdown file not found at path: {markdown_file_path}"

            if pdf_output_path is None:
                pdf_path = md_path.parent / f"{md_path.stem}.pdf"
            else:
                pdf_path = Path(pdf_output_path)

            # Read markdown content
            with open(md_path, 'r', encoding='utf-8') as f:
                md_content = f.read()

            # Parse table
            headers, table_data = self._parse_markdown_table(md_content)

            if not table_data:
                return "Error: No policy table found in markdown file. Expected a table with 'Source Name' column."

            # Create PDF
            doc = SimpleDocTemplate(
                str(pdf_path),
                pagesize=landscape(A4),
                rightMargin=1*cm,
                leftMargin=1*cm,
                topMargin=1.5*cm,
                bottomMargin=1.5*cm,
            )

            elements = []

            # Define styles
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=16,
                textColor=colors.HexColor('#2c3e50'),
                spaceAfter=20,
                alignment=TA_LEFT,
            )

            cell_style = ParagraphStyle(
                'CellStyle',
                parent=styles['Normal'],
                fontSize=7,
                leading=9,
                wordWrap='CJK',
            )

            # Add title
            title = Paragraph("Policy Retrieval Report", title_style)
            elements.append(title)
            elements.append(Spacer(1, 0.5*cm))

            # Process table data
            processed_data = []
            for row_idx, row in enumerate(table_data):
                processed_row = []
                for cell in row:
                    if row_idx == 0:  # Header row
                        processed_row.append(Paragraph(f"<b>{cell}</b>", cell_style))
                    else:
                        # Process the cell content (handle links and escape HTML)
                        processed_content = self._process_cell_content(cell)

                        # Wrap long text (but keep full links)
                        if len(cell) > 100 and '[' not in cell:
                            processed_content = html.escape(cell[:200] + '...') if len(cell) > 200 else processed_content

                        processed_row.append(Paragraph(processed_content, cell_style))
                processed_data.append(processed_row)

            # Create table with column widths
            col_widths = [3*cm, 1.8*cm, 5*cm, 3.5*cm, 4.5*cm, 2*cm, 1.5*cm, 2*cm]
            table = Table(processed_data, colWidths=col_widths, repeatRows=1)

            # Add style to table
            table.setStyle(TableStyle([
                # Header row
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, 0), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 8),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('TOPPADDING', (0, 0), (-1, 0), 8),
                # Data rows
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 7),
                ('TOPPADDING', (0, 1), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
                ('LEFTPADDING', (0, 0), (-1, -1), 5),
                ('RIGHTPADDING', (0, 0), (-1, -1), 5),
                # Grid
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                # Alternating row colors
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
            ]))

            elements.append(table)

            # Build PDF
            doc.build(elements)

            return f"Success: PDF created at {pdf_path}"

        except Exception as e:
            return f"Error converting markdown to PDF: {str(e)}"
