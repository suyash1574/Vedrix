from typing import Dict, Any, List, Optional
import math
import json
from fpdf import FPDF

def _clean_unicode(text: str) -> str:
    """
    Replaces common unsupported unicode characters with ASCII equivalents or sanitizes them
    to prevent fpdf/latin-1 crashes.
    """
    if not isinstance(text, str):
        return ""
    replacements = {
        '\u2013': '-',   # en dash
        '\u2014': '-',   # em dash
        '\u2018': "'",   # left single quote
        '\u2019': "'",   # right single quote
        '\u201c': '"',   # left double quote
        '\u201d': '"',   # right double quote
        '\u2022': '*',   # bullet point
        '\u2026': '...', # ellipsis
        '\xa0': ' ',     # non-breaking space
        '🚀': '[Rocket]',
        '🎯': '[Target]',
        '🎙️': '[Mic]',
        '🎙': '[Mic]',
        '👋': '[Hello]',
        '✓': '[Yes]',
        '✔': '[Yes]',
        '→': '->',
        '✅': '[Check]',
        '❌': '[Cross]',
        '🧠': '[Brain]',
        '💻': '[Code]',
        '📊': '[Chart]',
        '🏆': '[Cup]'
    }
    for orig, rep in replacements.items():
        text = text.replace(orig, rep)
    # Final encoding fallback to latin-1
    return text.encode('latin-1', 'replace').decode('latin-1')

def _draw_radar_chart(pdf, cx: float, cy: float, radius: float, skills: Dict[str, float]):
    """
    Draws a premium vector radar chart representing candidate skills directly in the PDF.
    """
    N = len(skills)
    if N < 3:
        return

    skills_list = list(skills.items())

    # 1. Concentric ring grid lines (representing scores of 2, 4, 6, 8, 10)
    pdf.set_draw_color(220, 220, 220)
    pdf.set_line_width(0.15)
    for ring in range(1, 6):
        fraction = ring / 5.0 # 0.2, 0.4, 0.6, 0.8, 1.0
        ring_points = []
        for i in range(N):
            angle = -math.pi / 2 + (2 * math.pi * i) / N
            x = cx + radius * fraction * math.cos(angle)
            y = cy + radius * fraction * math.sin(angle)
            ring_points.append((x, y))
        
        for i in range(N):
            p1 = ring_points[i]
            p2 = ring_points[(i + 1) % N]
            pdf.line(p1[0], p1[1], p2[0], p2[1])

    # 2. Draw radial axis lines from center to outer vertices
    for i in range(N):
        angle = -math.pi / 2 + (2 * math.pi * i) / N
        x_outer = cx + radius * math.cos(angle)
        y_outer = cy + radius * math.sin(angle)
        pdf.line(cx, cy, x_outer, y_outer)

    # 3. Compute score points
    score_points = []
    for i in range(N):
        skill_name, score = skills_list[i]
        score = max(0.0, min(10.0, float(score)))
        fraction = score / 10.0
        angle = -math.pi / 2 + (2 * math.pi * i) / N
        x = cx + radius * fraction * math.cos(angle)
        y = cy + radius * fraction * math.sin(angle)
        score_points.append((x, y))

    # 4. Fill and stroke the score polygon
    pdf.set_draw_color(124, 58, 237) # Vedrix Purple
    pdf.set_line_width(0.5)
    pdf.set_fill_color(237, 233, 254) # Very light purple
    
    if hasattr(pdf, "polygon"):
        try:
            # Draw translucent filled polygon when supported by the installed FPDF build.
            with pdf.local_context(fill_opacity=0.35, stroke_opacity=1.0):
                pdf.polygon(score_points, style="FD")
        except Exception:
            # Some FPDF builds expose polygon but not opacity contexts.
            pdf.polygon(score_points, style="FD")
    else:
        # Portable fallback for older FPDF builds without polygon primitives.
        for i, point in enumerate(score_points):
            next_point = score_points[(i + 1) % len(score_points)]
            pdf.line(point[0], point[1], next_point[0], next_point[1])

    # 5. Draw small circular markers (ellipses) at each vertex
    pdf.set_fill_color(124, 58, 237)
    for x, y in score_points:
        pdf.ellipse(x - 1, y - 1, 2, 2, style="FD")

    # 6. Label each axis
    pdf.set_font("helvetica", "B", 8)
    pdf.set_text_color(75, 85, 99) # Dark grey-slate
    for i in range(N):
        skill_name, score = skills_list[i]
        angle = -math.pi / 2 + (2 * math.pi * i) / N
        
        # Position label outside outer radius
        label_dist = radius + 6
        lx = cx + label_dist * math.cos(angle)
        ly = cy + label_dist * math.sin(angle)
        
        label_text = _clean_unicode(f"{skill_name}: {score:.1f}")
        text_w = pdf.get_string_width(label_text)
        
        # Calculate alignment adjustments
        cos_val = math.cos(angle)
        sin_val = math.sin(angle)
        
        if abs(cos_val) < 0.1: # Top/Bottom center
            adj_lx = lx - (text_w / 2)
            adj_ly = ly + 2.5 if sin_val > 0 else ly - 1
        elif cos_val > 0: # Right half
            adj_lx = lx
            adj_ly = ly + 0.8
        else: # Left half
            adj_lx = lx - text_w
            adj_ly = ly + 0.8
            
        pdf.text(adj_lx, adj_ly, label_text)


def _pdf_output_bytes(pdf: FPDF) -> bytes:
    """Return PDF output as bytes across supported PyFPDF/fpdf2 versions."""
    output = pdf.output(dest="S")
    if isinstance(output, str):
        return output.encode("latin-1")
    return bytes(output)


def generate_interview_pdf(
    candidate_name: str,
    job_role: str,
    report: Dict[str, Any],
    transcript: List[Dict[str, str]],
    skill_matrix: Optional[Dict[str, Any]] = None,
) -> bytes:
    """
    Generates a high-fidelity PDF interview report.
    """
    class PDF(FPDF):
        def header(self):
            self.set_font("helvetica", "B", 15)
            self.set_text_color(124, 58, 237) # Vedrix Purple
            self.cell(0, 10, "Vedrix AI - Candidate Evaluation Report", border=False, align="C", ln=1)
            self.set_draw_color(124, 58, 237)
            self.line(10, 20, 200, 20)
            self.ln(10)

        def footer(self):
            self.set_y(-15)
            self.set_font("helvetica", "I", 8)
            self.set_text_color(128, 128, 128)
            self.cell(0, 10, f"Page {self.page_no()}/{{nb}} - Generated by Vedrix AI Platform", align="C")

    pdf = PDF()
    pdf.add_page()
    
    # Hero Info
    pdf.set_font("helvetica", "B", 12)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(40, 8, "Candidate:")
    pdf.set_font("helvetica", "", 12)
    pdf.cell(0, 8, _clean_unicode(candidate_name), ln=1)

    pdf.set_font("helvetica", "B", 12)
    pdf.cell(40, 8, "Role:")
    pdf.set_font("helvetica", "", 12)
    pdf.cell(0, 8, _clean_unicode(job_role), ln=1)

    pdf.set_font("helvetica", "B", 12)
    pdf.cell(40, 8, "Score:")
    pdf.set_font("helvetica", "B", 14)
    pdf.set_text_color(52, 211, 153) # Greenish
    pdf.cell(0, 8, f"{report.get('overall_score', 'N/A')} / 10.0", ln=1)
    
    pdf.set_font("helvetica", "B", 12)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(40, 8, "Decision:")
    pdf.set_font("helvetica", "B", 12)
    pdf.cell(0, 8, _clean_unicode(str(report.get('hire_recommendation', 'N/A')).upper()), ln=1)
    pdf.ln(10)

    # Score Breakdown
    pdf.set_font("helvetica", "B", 14)
    pdf.set_text_color(124, 58, 237)
    pdf.cell(0, 10, "Score Breakdown", border="B", ln=1)
    pdf.ln(3)
    pdf.set_font("helvetica", "B", 11)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(60, 8, "Technical Accuracy:")
    pdf.set_font("helvetica", "", 11)
    pdf.cell(0, 8, str(report.get('technical_accuracy', 'N/A')), ln=1)
    
    pdf.set_font("helvetica", "B", 11)
    pdf.cell(60, 8, "Communication Clarity:")
    pdf.set_font("helvetica", "", 11)
    pdf.cell(0, 8, str(report.get('communication_clarity', 'N/A')), ln=1)
    
    pdf.set_font("helvetica", "B", 11)
    pdf.cell(60, 8, "Depth of Knowledge:")
    pdf.set_font("helvetica", "", 11)
    pdf.cell(0, 8, str(report.get('depth_of_knowledge', 'N/A')), ln=1)
    pdf.ln(8)

    # ── Skill Radar Chart Section ──
    pdf.set_font("helvetica", "B", 14)
    pdf.set_text_color(124, 58, 237)
    pdf.cell(0, 10, "Candidate Skill Profile", border="B", ln=1)
    pdf.ln(5)
    
    # Process skills dictionary
    skills = {}
    if report:
        if report.get("technical_accuracy") is not None:
            try:
                skills["Technical Accuracy"] = float(report["technical_accuracy"])
            except (ValueError, TypeError):
                pass
        if report.get("communication_clarity") is not None:
            try:
                skills["Communication"] = float(report["communication_clarity"])
            except (ValueError, TypeError):
                pass
        if report.get("depth_of_knowledge") is not None:
            try:
                skills["Depth of Knowledge"] = float(report["depth_of_knowledge"])
            except (ValueError, TypeError):
                pass

    if skill_matrix:
        if isinstance(skill_matrix, str):
            try:
                skill_matrix = json.loads(skill_matrix)
            except Exception:
                skill_matrix = {}
        if isinstance(skill_matrix, dict):
            for k, v in skill_matrix.items():
                if v is not None:
                    try:
                        skills[str(k).capitalize()] = float(v)
                    except (ValueError, TypeError):
                        pass

    # Extract core and other skills to build up to 8 dimensions
    core_skills = ["Technical Accuracy", "Communication", "Depth of Knowledge"]
    other_skills = {k: v for k, v in skills.items() if k not in core_skills}
    # Take top 5 others
    top_others = dict(sorted(other_skills.items(), key=lambda x: x[1], reverse=True)[:5])
    
    final_skills = {}
    for cs in core_skills:
        if cs in skills:
            final_skills[cs] = skills[cs]
    for k, v in top_others.items():
        final_skills[k] = v

    if len(final_skills) >= 3:
        # Draw radar chart centered dynamically below the section title
        cx = 105.0
        cy = pdf.get_y() + 32.0
        _draw_radar_chart(pdf, cx=cx, cy=cy, radius=25.0, skills=final_skills)
        # Advance the PDF y cursor past the chart area
        pdf.set_y(cy + 25.0 + 12.0)
    else:
        # Tabular breakdown
        pdf.set_font("helvetica", "B", 10)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(100, 8, "Skill / Competency", border=1)
        pdf.cell(40, 8, "Score", border=1, align="C", ln=1)
        pdf.set_font("helvetica", "", 10)
        for skill_name, score in final_skills.items():
            pdf.cell(100, 8, _clean_unicode(skill_name), border=1)
            pdf.cell(40, 8, f"{score:.1f} / 10.0", border=1, align="C", ln=1)
        pdf.ln(5)

    pdf.add_page() # Executive Summary starts on Page 2

    # Executive Summary
    pdf.set_font("helvetica", "B", 14)
    pdf.set_text_color(124, 58, 237)
    pdf.cell(0, 10, "Executive Summary", border="B", ln=1)
    pdf.ln(3)
    pdf.set_font("helvetica", "I", 11)
    pdf.set_text_color(50, 50, 50)
    pdf.multi_cell(0, 6, _clean_unicode(str(report.get('summary', 'No summary available.'))))
    pdf.ln(8)

    # Strengths
    pdf.set_font("helvetica", "B", 14)
    pdf.set_text_color(124, 58, 237)
    pdf.cell(0, 10, "Key Strengths", border="B", ln=1)
    pdf.ln(3)
    pdf.set_font("helvetica", "", 11)
    pdf.set_text_color(0, 0, 0)
    for s in report.get("strengths", []):
        pdf.cell(5, 6, "-")
        pdf.multi_cell(0, 6, _clean_unicode(str(s)))
    pdf.ln(5)

    # Weaknesses
    pdf.set_font("helvetica", "B", 14)
    pdf.set_text_color(124, 58, 237)
    pdf.cell(0, 10, "Areas for Improvement", border="B", ln=1)
    pdf.ln(3)
    pdf.set_font("helvetica", "", 11)
    pdf.set_text_color(0, 0, 0)
    for w in report.get("weaknesses", []):
        pdf.cell(5, 6, "-")
        pdf.multi_cell(0, 6, _clean_unicode(str(w)))
    pdf.ln(5)

    # Transcript
    pdf.add_page()
    pdf.set_font("helvetica", "B", 14)
    pdf.set_text_color(124, 58, 237)
    pdf.cell(0, 10, "Interview Transcript", border="B", ln=1)
    pdf.ln(5)
    
    for m in transcript:
        role = str(m.get("role", "?")).upper()
        content = str(m.get("content", ""))
        
        pdf.set_font("helvetica", "B", 10)
        if role == "ASSISTANT":
            pdf.set_text_color(124, 58, 237)
            role_text = "[AI INTERVIEWER]"
        else:
            pdf.set_text_color(30, 30, 30)
            role_text = "[CANDIDATE]"
            
        pdf.cell(0, 6, role_text, ln=1)
        
        pdf.set_font("helvetica", "", 10)
        pdf.set_text_color(50, 50, 50)
        
        pdf.multi_cell(0, 5, _clean_unicode(content))
        pdf.ln(4)

    return _pdf_output_bytes(pdf)


def generate_certificate(
    candidate_name: str,
    job_role: str,
    overall_score: float,
    date_completed: str,
) -> bytes:
    """
    Generates a completion certificate PDF.
    """
    from datetime import datetime

    class CertificatePDF(FPDF):
        def header(self):
            # Decorative border
            self.set_draw_color(124, 58, 237)
            self.set_line_width(2)
            self.rect(10, 10, 190, 277)
            self.set_line_width(0.5)
            self.rect(15, 15, 180, 267)

            # Logo area
            self.set_font("helvetica", "B", 36)
            self.set_text_color(124, 58, 237)
            self.cell(0, 40, "VEDRIX", align="C", ln=1)
            self.set_font("helvetica", "", 14)
            self.set_text_color(100, 100, 100)
            self.cell(0, 10, "AI Interview Platform", align="C", ln=1)
            self.ln(20)

    pdf = CertificatePDF()
    pdf.add_page()

    # Certificate Title
    pdf.set_font("helvetica", "B", 32)
    pdf.set_text_color(50, 50, 50)
    pdf.cell(0, 20, "Certificate of Completion", align="C", ln=1)
    pdf.ln(10)

    # Subtitle
    pdf.set_font("helvetica", "", 14)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 10, "This is to certify that", align="C", ln=1)
    pdf.ln(15)

    # Candidate Name
    pdf.set_font("helvetica", "B", 28)
    pdf.set_text_color(124, 58, 237)
    pdf.cell(0, 15, candidate_name, align="C", ln=1)
    pdf.ln(15)

    # Achievement text
    pdf.set_font("helvetica", "", 14)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 10, "has successfully completed the AI-powered interview", align="C", ln=1)
    pdf.ln(10)

    # Job Role
    pdf.set_font("helvetica", "B", 18)
    pdf.set_text_color(50, 50, 50)
    pdf.cell(0, 12, f"for the role of {job_role or 'General Candidate'}", align="C", ln=1)
    pdf.ln(15)

    # Score
    pdf.set_font("helvetica", "", 14)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 10, "with an overall performance score of", align="C", ln=1)
    pdf.ln(8)

    pdf.set_font("helvetica", "B", 48)
    if overall_score >= 80:
        pdf.set_text_color(34, 197, 94)  # Green
    elif overall_score >= 60:
        pdf.set_text_color(251, 191, 36)  # Amber
    else:
        pdf.set_text_color(239, 68, 68)  # Red

    pdf.cell(0, 25, f"{overall_score:.1f}%", align="C", ln=1)
    pdf.ln(20)

    # Date
    pdf.set_font("helvetica", "", 12)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 8, f"Date of Completion: {date_completed}", align="C", ln=1)
    pdf.ln(25)

    # Signatures
    pdf.set_font("helvetica", "", 12)
    pdf.set_text_color(50, 50, 50)

    pdf.cell(85, 10, "_______________________", align="L")
    pdf.cell(0, 10, "_______________________", align="R", ln=1)

    pdf.set_font("helvetica", "B", 10)
    pdf.cell(85, 8, "Vedrix AI Platform", align="L")
    pdf.cell(0, 8, "Candidate", align="R", ln=1)

    return _pdf_output_bytes(pdf)


def generate_certificate_png(
    candidate_name: str,
    job_role: str,
    overall_score: float,
    date_completed: str,
    verification_token: str = "",
) -> bytes:
    """
    Generates a high-resolution PNG certificate image suitable for social sharing.
    Uses Pillow to render directly. Resolution: 1200x800.
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
        import io
    except ImportError:
        # Fallback: return empty PNG if Pillow not available
        import io
        img = Image.new('RGB', (1200, 800), color=(2, 6, 23))
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        return buffer.getvalue()

    # Certificate dimensions (LinkedIn optimal share image)
    width, height = 1200, 800

    # Create image with dark background
    img = Image.new('RGB', (width, height), color=(2, 6, 23))  # #020617
    draw = ImageDraw.Draw(img)

    try:
        font_title = ImageFont.truetype("arial.ttf", 48)
        font_subtitle = ImageFont.truetype("arial.ttf", 24)
        font_name = ImageFont.truetype("arial.ttf", 56)
        font_score = ImageFont.truetype("arial.ttf", 72)
        font_body = ImageFont.truetype("arial.ttf", 20)
        font_small = ImageFont.truetype("arial.ttf", 16)
        font_bold = ImageFont.truetype("arialbd.ttf", 20)
    except (IOError, OSError):
        font_title = ImageFont.load_default()
        font_subtitle = ImageFont.load_default()
        font_name = ImageFont.load_default()
        font_score = ImageFont.load_default()
        font_body = ImageFont.load_default()
        font_small = ImageFont.load_default()
        font_bold = ImageFont.load_default()

    # Decorative border
    draw.rectangle([20, 20, width - 20, height - 20], outline=(124, 58, 237), width=4)
    draw.rectangle([30, 30, width - 30, height - 30], outline=(124, 58, 237), width=2)

    # Top accent line
    draw.rectangle([100, 50, width - 100, 54], fill=(124, 58, 237))

    # VEDRIX logo text
    draw.text((width // 2 - 120, 70), "VEDRIX", fill=(124, 58, 237), font=font_title)
    draw.text((width // 2 - 100, 125), "AI Interview Platform", fill=(100, 100, 100), font=font_subtitle)

    # Certificate title
    draw.text((width // 2 - 180, 200), "Certificate of Completion", fill=(255, 255, 255), font=font_title)

    # "This is to certify that"
    draw.text((width // 2 - 120, 280), "This is to certify that", fill=(148, 163, 184), font=font_body)

    # Candidate name
    name_bbox = draw.textbbox((0, 0), candidate_name, font=font_name)
    name_width = name_bbox[2] - name_bbox[0]
    draw.text((width // 2 - name_width // 2, 320), candidate_name, fill=(167, 139, 250), font=font_name)

    # Achievement text
    draw.text((width // 2 - 180, 410), "has successfully completed the AI-powered interview", fill=(148, 163, 184), font=font_body)

    # Job role
    role_text = f"for the role of {job_role or 'General Candidate'}"
    role_bbox = draw.textbbox((0, 0), role_text, font=font_bold)
    role_width = role_bbox[2] - role_bbox[0]
    draw.text((width // 2 - role_width // 2, 445), role_text, fill=(255, 255, 255), font=font_bold)

    # Score label
    draw.text((width // 2 - 120, 510), "with an overall performance score of", fill=(148, 163, 184), font=font_body)

    # Score value with color based on performance
    if overall_score >= 80:
        score_color = (34, 197, 94)  # Green
    elif overall_score >= 60:
        score_color = (251, 191, 36)  # Amber
    else:
        score_color = (239, 68, 68)  # Red

    score_text = f"{overall_score:.1f}%"
    score_bbox = draw.textbbox((0, 0), score_text, font=font_score)
    score_width = score_bbox[2] - score_bbox[0]
    draw.text((width // 2 - score_width // 2, 545), score_text, fill=score_color, font=font_score)

    # Date
    draw.text((width // 2 - 100, 650), f"Date: {date_completed}", fill=(100, 100, 100), font=font_small)

    # Verification token (if provided)
    if verification_token:
        verify_text = f"Verify at: vedrix.ai/verify/{verification_token}"
        verify_bbox = draw.textbbox((0, 0), verify_text, font=font_small)
        verify_width = verify_bbox[2] - verify_bbox[0]
        draw.text((width // 2 - verify_width // 2, 680), verify_text, fill=(124, 58, 237), font=font_small)

    # Bottom accent line
    draw.rectangle([100, height - 60, width - 100, height - 56], fill=(124, 58, 237))

    # Save as PNG
    buffer = io.BytesIO()
    img.save(buffer, format='PNG', quality=95)
    return buffer.getvalue()
