from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet

def generate_resume_pdf(resume_text, template_name="default"):

def generate_resume_pdf(resume_text: str, cover_letter: str = "") -> bytes:
    """Generate a clean ATS-friendly PDF resume."""

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40,
    )

    styles = getSampleStyleSheet()
    normal_style = styles["BodyText"]
    heading_style = styles["Heading2"]

    elements = []

    for line in resume_text.split("\n"):
        cleaned = line.strip()

        if not cleaned:
            elements.append(Spacer(1, 8))
            continue

        if cleaned.isupper() or cleaned.startswith("##"):
            heading_text = cleaned.replace("##", "").strip()
            elements.append(Paragraph(heading_text, heading_style))
        else:
            safe_line = cleaned.replace("&", "&amp;")
            elements.append(Paragraph(safe_line, normal_style))

    if cover_letter:
        elements.append(PageBreak())
        elements.append(Paragraph("Cover Letter", heading_style))

        for line in cover_letter.split("\n"):
            cleaned = line.strip()
            if not cleaned:
                elements.append(Spacer(1, 8))
                continue

            safe_line = cleaned.replace("&", "&amp;")
            elements.append(Paragraph(safe_line, normal_style))

    doc.build(elements)

    pdf_data = buffer.getvalue()
    buffer.close()

    return pdf_data
