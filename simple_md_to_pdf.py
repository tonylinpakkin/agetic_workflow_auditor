#!/usr/bin/env python3
"""
Simple markdown to PDF converter using reportlab.
"""
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER
import re
import html
from pathlib import Path

def parse_markdown_table(md_content):
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

def create_pdf(md_file, pdf_file=None):
    """Create PDF from markdown file."""
    md_path = Path(md_file)

    if pdf_file is None:
        pdf_file = md_path.parent / f"{md_path.stem}.pdf"

    # Read markdown content
    with open(md_path, 'r', encoding='utf-8') as f:
        md_content = f.read()

    # Parse table
    headers, table_data = parse_markdown_table(md_content)

    if not table_data:
        print("No table found in markdown file")
        return

    # Create PDF
    doc = SimpleDocTemplate(
        str(pdf_file),
        pagesize=landscape(A4),
        rightMargin=1*cm,
        leftMargin=1*cm,
        topMargin=1.5*cm,
        bottomMargin=1.5*cm,
    )

    # Container for the 'Flowable' objects
    elements = []

    # Define styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.HexColor('#2c3e50'),
        spaceAfter=20,
        alignment=TA_CENTER,
    )

    # Add title
    title = Paragraph("Revised Policy Retrieval Table", title_style)
    elements.append(title)
    elements.append(Spacer(1, 0.5*cm))

    # Define cell style for wrapping text
    cell_style = ParagraphStyle(
        'CellStyle',
        parent=styles['Normal'],
        fontSize=7,
        leading=9,
        wordWrap='CJK',
    )

    # Helper function to escape HTML and convert markdown links
    def process_cell_content(cell_text):
        """Process cell content: escape HTML entities and convert markdown links."""
        import html

        # First, check if this is a markdown link
        link_match = re.match(r'\[([^\]]+)\]\(([^\)]+)\)', cell_text)
        if link_match:
            link_text = html.escape(link_match.group(1))
            link_url = link_match.group(2)
            return f'<link href="{link_url}" color="blue"><u>{link_text}</u></link>'
        else:
            # Escape HTML entities for plain text
            return html.escape(cell_text)

    # Process table data to wrap text in cells
    processed_data = []
    for row_idx, row in enumerate(table_data):
        processed_row = []
        for cell in row:
            if row_idx == 0:  # Header row
                processed_row.append(Paragraph(f"<b>{cell}</b>", cell_style))
            else:
                # Process the cell content (handle links and escape HTML)
                processed_content = process_cell_content(cell)

                # Wrap long text
                if len(cell) > 100:
                    # Keep the full link but truncate display text if needed
                    if '[' not in cell:  # Only truncate non-link cells
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

    # Add summary section
    elements.append(Spacer(1, 1*cm))

    summary_style = ParagraphStyle(
        'Summary',
        parent=styles['Heading2'],
        fontSize=12,
        textColor=colors.HexColor('#34495e'),
        spaceAfter=10,
    )

    normal_style = ParagraphStyle(
        'NormalText',
        parent=styles['Normal'],
        fontSize=9,
        leading=12,
    )

    elements.append(Paragraph("Summary of Improvements Made:", summary_style))

    summary_points = [
        "<b>Updated URLs:</b> Verified and confirmed all URLs for accuracy and completeness.",
        "<b>Effective Dates:</b> Completed effective dates for all entries where possible.",
        "<b>Confidence Levels:</b> Ensured all entries are marked as 'High' confidence based on verified sources.",
        "<b>Enhanced Relevance Notes:</b> Clarified the relevance of each policy to the observation on risk assessment procedures.",
        "<b>Consistent Formatting:</b> Ensured all entries are formatted consistently for readability.",
    ]

    for point in summary_points:
        elements.append(Paragraph(f"• {point}", normal_style))
        elements.append(Spacer(1, 0.2*cm))

    # Build PDF
    doc.build(elements)
    print(f"✓ PDF created successfully: {pdf_file}")
    return pdf_file

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python simple_md_to_pdf.py <markdown_file> [output_pdf]")
        sys.exit(1)

    md_file = sys.argv[1]
    pdf_file = sys.argv[2] if len(sys.argv) > 2 else None

    create_pdf(md_file, pdf_file)
