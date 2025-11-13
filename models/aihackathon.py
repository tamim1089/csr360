#!/usr/bin/env python3
"""
generate_ai_report_service.py

Enhanced AI Report Generator Service
- Provides REST API to generate PDF reports from AI-generated markdown
- Communicates with Ollama API to generate content
- Returns JSON response with status and PDF download link
- Runs as a persistent service
"""

import requests
import re
import os
from datetime import datetime
from flask import Flask, request, send_file, jsonify, send_from_directory
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
)
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm

# ========== Configuration ==========
OLLAMA_API_URL = "http://47.94.52.149:9000/api/generate"
OUTPUT_DIR = "./generated_reports"
REQUEST_TIMEOUT = 120  # seconds for Ollama API request
DEFAULT_MODEL = "deepseek-v2:latest"

# Create output directory if it doesn't exist
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ========== PDF Styles ==========
styles = getSampleStyleSheet()
styles.add(ParagraphStyle(
    name='TitleCenter',
    parent=styles['Title'],
    alignment=1,
    spaceAfter=12,
    fontSize=20,
    textColor=colors.HexColor("#1a1a1a")
))
styles.add(ParagraphStyle(
    name='H1',
    parent=styles['Heading1'],
    fontSize=18,
    leading=22,
    spaceAfter=8,
    textColor=colors.HexColor("#2c3e50")
))
styles.add(ParagraphStyle(
    name='H2',
    parent=styles['Heading2'],
    fontSize=14,
    leading=18,
    spaceAfter=6,
    textColor=colors.HexColor("#34495e")
))
styles.add(ParagraphStyle(
    name='Body',
    parent=styles['BodyText'],
    fontSize=10.5,
    leading=14,
    spaceAfter=6
))
styles.add(ParagraphStyle(
    name='BulletList',
    parent=styles['BodyText'],
    leftIndent=12,
    bulletIndent=6,
    leading=13,
    spaceAfter=2
))

# ========== Ollama API Communication ==========
def fetch_markdown_from_ollama(prompt: str, model: str = DEFAULT_MODEL) -> str:
    """
    Send prompt to Ollama API and extract markdown content from response.
    """
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False
    }
    
    print(f"[{datetime.now()}] Sending request to Ollama API...")
    print(f"  Model: {model}")
    print(f"  Prompt length: {len(prompt)} characters")
    
    try:
        resp = requests.post(OLLAMA_API_URL, json=payload, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        text = data.get("response", "") or ""
        
        print(f"[{datetime.now()}] Response received ({len(text)} characters)")
        
        # Extract fenced markdown if present
        markdown_match = re.search(r"```(?:markdown)?\s*(.*?)\s*```", text, re.DOTALL)
        if markdown_match:
            return markdown_match.group(1).strip()
        return text.strip()
        
    except requests.exceptions.Timeout:
        raise RuntimeError(f"Request to Ollama API timed out after {REQUEST_TIMEOUT}s")
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Failed to communicate with Ollama API: {str(e)}")
    except Exception as e:
        raise RuntimeError(f"Unexpected error: {str(e)}")


# ========== Markdown Parser ==========
def parse_markdown(md_text: str):
    """
    Parse markdown text into structured blocks for PDF generation.
    Returns: List of (block_type, content) tuples
    """
    lines = md_text.splitlines()
    blocks = []
    i = 0

    def push_paragraph(buf):
        if buf:
            blocks.append(('p', ' '.join([ln.strip() for ln in buf]).strip()))
            buf.clear()

    para_buf = []
    
    while i < len(lines):
        ln = lines[i].rstrip()
        
        # Skip empty lines
        if not ln:
            push_paragraph(para_buf)
            i += 1
            continue

        # Headers
        if ln.startswith('# '):
            push_paragraph(para_buf)
            blocks.append(('h1', ln[2:].strip()))
            i += 1
            continue
        if ln.startswith('## '):
            push_paragraph(para_buf)
            blocks.append(('h2', ln[3:].strip()))
            i += 1
            continue
        if ln.startswith('### '):
            push_paragraph(para_buf)
            blocks.append(('h3', ln[4:].strip()))
            i += 1
            continue

        # Unordered lists
        if re.match(r'^\s*[-\*]\s+', ln):
            push_paragraph(para_buf)
            items = []
            while i < len(lines) and re.match(r'^\s*[-\*]\s+', lines[i]):
                items.append(re.sub(r'^\s*[-\*]\s+', '', lines[i]).strip())
                i += 1
            blocks.append(('ul', items))
            continue

        # Ordered lists
        if re.match(r'^\s*\d+\.\s+', ln):
            push_paragraph(para_buf)
            items = []
            while i < len(lines) and re.match(r'^\s*\d+\.\s+', lines[i]):
                items.append(re.sub(r'^\s*\d+\.\s+', '', lines[i]).strip())
                i += 1
            blocks.append(('ol', items))
            continue

        # Tables
        if '|' in ln:
            push_paragraph(para_buf)
            table_lines = []
            while i < len(lines) and '|' in lines[i]:
                table_lines.append(lines[i].strip())
                i += 1
            
            rows = []
            for row in table_lines:
                # Skip separator rows
                if re.match(r'^\s*\|?\s*-{2,}\s*(\|\s*-{2,}\s*)+\|?\s*$', row):
                    continue
                cells = [c.strip() for c in re.split(r'\|', row)]
                # Remove empty edge cells
                if cells and cells[0] == '':
                    cells = cells[1:]
                if cells and cells[-1] == '':
                    cells = cells[:-1]
                if cells:
                    rows.append(cells)
            
            if rows:
                blocks.append(('table', rows))
            continue

        # Regular paragraph text
        para_buf.append(ln)
        i += 1

    push_paragraph(para_buf)
    return blocks


# ========== PDF Generation ==========
def build_story_from_blocks(blocks):
    """Convert parsed markdown blocks into ReportLab story elements."""
    story = []
    
    # Use first h1 as centered title
    if blocks and blocks[0][0] == 'h1':
        story.append(Paragraph(blocks[0][1], styles['TitleCenter']))
        story.append(Spacer(1, 8))
        blocks = blocks[1:]

    for typ, content in blocks:
        if typ == 'h1':
            story.append(Paragraph(content, styles['H1']))
        elif typ == 'h2':
            story.append(Paragraph(content, styles['H2']))
        elif typ == 'h3':
            story.append(Paragraph(f"<b>{content}</b>", styles['Body']))
            story.append(Spacer(1, 4))
        elif typ == 'p':
            story.append(Paragraph(content, styles['Body']))
        elif typ == 'ul':
            for item in content:
                story.append(Paragraph(f"• {item}", styles['BulletList']))
        elif typ == 'ol':
            for idx, item in enumerate(content, start=1):
                story.append(Paragraph(f"{idx}. {item}", styles['BulletList']))
        elif typ == 'table':
            max_cols = max(len(r) for r in content)
            norm_rows = [r + [''] * (max_cols - len(r)) for r in content]
            
            table = Table(norm_rows, hAlign='LEFT')
            table.setStyle(TableStyle([
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#e8f4f8")),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ]))
            story.append(KeepTogether(table))
        
        story.append(Spacer(1, 6))
    
    return story


def add_page_number(canvas, doc):
    """Add page numbers to PDF footer."""
    canvas.saveState()
    footer = f"AI Generated Report — Page {doc.page} — {datetime.now().strftime('%Y-%m-%d')}"
    canvas.setFont('Helvetica', 8)
    canvas.setFillColor(colors.grey)
    w = canvas.stringWidth(footer, 'Helvetica', 8)
    canvas.drawString((A4[0] - w) / 2.0, 10 * mm, footer)
    canvas.restoreState()


def write_pdf_from_markdown(markdown_text: str, output_path: str):
    """Generate PDF file from markdown text."""
    print(f"[{datetime.now()}] Parsing markdown...")
    blocks = parse_markdown(markdown_text)
    print(f"[{datetime.now()}] Building PDF story ({len(blocks)} blocks)...")
    story = build_story_from_blocks(blocks)
    
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=20*mm,
        rightMargin=20*mm,
        topMargin=20*mm,
        bottomMargin=20*mm
    )
    
    print(f"[{datetime.now()}] Generating PDF...")
    doc.build(story, onFirstPage=add_page_number, onLaterPages=add_page_number)
    print(f"[{datetime.now()}] PDF generated successfully: {output_path}")


# ========== Main Generation Function ==========
def generate_report(prompt: str, model: str = DEFAULT_MODEL, filename: str = None) -> dict:
    """
    Generate PDF report from prompt using Ollama API.
    Returns: dict with status, message, filename, and path
    """
    try:
        # Generate timestamp-based filename if not provided
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"AI_Report_{timestamp}.pdf"
        
        # Ensure .pdf extension
        if not filename.endswith('.pdf'):
            filename += '.pdf'
        
        output_path = os.path.join(OUTPUT_DIR, filename)
        
        # Fetch markdown from Ollama
        markdown = fetch_markdown_from_ollama(prompt, model)
        
        if not markdown:
            raise RuntimeError("Empty response received from Ollama API")
        
        # Generate PDF
        write_pdf_from_markdown(markdown, output_path)
        
        return {
            "status": "success",
            "message": "PDF report generated successfully",
            "filename": filename,
            "path": output_path,
            "size_bytes": os.path.getsize(output_path)
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "filename": None,
            "path": None
        }


# ========== Flask API ==========
app = Flask(__name__)


@app.route('/', methods=['GET'])
def index():
    """API documentation endpoint."""
    return jsonify({
        "service": "AI Report Generator",
        "version": "2.0",
        "endpoints": {
            "/generate_report": {
                "method": "POST",
                "description": "Generate a PDF report from a prompt",
                "parameters": {
                    "prompt": "required - The prompt to send to the AI model",
                    "model": "optional - Ollama model name (default: deepseek-v2:latest)",
                    "filename": "optional - Custom filename for the PDF (default: auto-generated)"
                },
                "example": {
                    "prompt": "Generate a report about AI trends in 2025 with statistics",
                    "model": "deepseek-v2:latest",
                    "filename": "ai_trends_2025.pdf"
                }
            },
            "/download/<filename>": {
                "method": "GET",
                "description": "Download a generated PDF report"
            },
            "/list": {
                "method": "GET",
                "description": "List all generated reports"
            }
        }
    })


@app.route('/generate_report', methods=['POST'])
def api_generate_report():
    """
    API endpoint to generate PDF report.
    
    Expected JSON body:
    {
        "prompt": "Your prompt here",
        "model": "deepseek-v2:latest", 
        "filename": "custom_name.pdf", 
        "return_file": true   
    }
    """
    try:
        data = request.get_json(force=True)
    except Exception:
        return jsonify({
            "status": "error",
            "message": "Invalid JSON in request body"
        }), 400
    
    if not data or 'prompt' not in data:
        return jsonify({
            "status": "error",
            "message": "Missing required field 'prompt' in request body",
            "example": {
                "prompt": "Generate a report about AI in 2025",
                "model": "deepseek-v2:latest",
                "filename": "my_report.pdf",
                "return_file": True
            }
        }), 400
    
    prompt = data['prompt']
    model = data.get('model', DEFAULT_MODEL)
    filename = data.get('filename')
    return_file = data.get('return_file', True)  # Default to True for direct PDF return
    
    print(f"\n{'='*60}")
    print(f"[{datetime.now()}] New report generation request")
    print(f"  Prompt: {prompt[:100]}{'...' if len(prompt) > 100 else ''}")
    print(f"  Model: {model}")
    print(f"  Custom filename: {filename or 'auto-generated'}")
    print(f"  Return file directly: {return_file}")
    print(f"{'='*60}\n")
    
    # Generate the report
    result = generate_report(prompt, model, filename)
    
    if result['status'] == 'success':
        print(f"\n✅ Report generated successfully: {result['filename']}\n")
        
        # Return PDF file directly if requested (default behavior)
        if return_file:
            return send_file(
                result['path'],
                as_attachment=True,
                download_name=result['filename'],
                mimetype='application/pdf'
            )
        else:
            # Return JSON response with download URL
            return jsonify({
                "status": "success",
                "message": result['message'],
                "filename": result['filename'],
                "download_url": f"/download/{result['filename']}",
                "size_bytes": result['size_bytes']
            }), 200
    else:
        print(f"\n❌ Error generating report: {result['message']}\n")
        return jsonify({
            "status": "error",
            "message": result['message']
        }), 500


@app.route('/download/<filename>', methods=['GET'])
def download_report(filename):
    """Download a generated PDF report."""
    try:
        return send_from_directory(OUTPUT_DIR, filename, as_attachment=True)
    except FileNotFoundError:
        return jsonify({
            "status": "error",
            "message": f"File '{filename}' not found"
        }), 404


@app.route('/list', methods=['GET'])
def list_reports():
    """List all generated PDF reports."""
    try:
        files = [f for f in os.listdir(OUTPUT_DIR) if f.endswith('.pdf')]
        reports = []
        for f in files:
            path = os.path.join(OUTPUT_DIR, f)
            reports.append({
                "filename": f,
                "size_bytes": os.path.getsize(path),
                "created": datetime.fromtimestamp(os.path.getctime(path)).isoformat(),
                "download_url": f"/download/{f}"
            })
        return jsonify({
            "status": "success",
            "count": len(reports),
            "reports": sorted(reports, key=lambda x: x['created'], reverse=True)
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


# ========== Main Entry Point ==========
def main():
    """Start the Flask API service."""
    print("\n" + "="*60)
    print("🚀 AI Report Generator Service Starting...")
    print("="*60)
    print(f"Output directory: {os.path.abspath(OUTPUT_DIR)}")
    print(f"Ollama API: {OLLAMA_API_URL}")
    print(f"Default model: {DEFAULT_MODEL}")
    print(f"\nAPI Server: http://127.0.0.1:5000")
    print(f"Documentation: http://127.0.0.1:5000/")
    print("="*60 + "\n")
    
    app.run(host='127.0.0.1', port=5000, debug=False)


if __name__ == "__main__":
    main()
