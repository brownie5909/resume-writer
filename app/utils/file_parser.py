import os
from io import BytesIO

import PyPDF2
from docx import Document


async def extract_text_from_file(file):
    """
    Extract text from uploaded resume files.
    Supports PDF, DOCX, DOC, and TXT.
    """

    filename = file.filename.lower()

    try:
        content = await file.read()

        # PDF files
        if filename.endswith(".pdf"):
            return extract_pdf_text(content)

        # DOCX files
        elif filename.endswith(".docx"):
            return extract_docx_text(content)

        # TXT files
        elif filename.endswith(".txt"):
            return content.decode("utf-8", errors="ignore")

        # DOC files (basic fallback)
        elif filename.endswith(".doc"):
            return content.decode("utf-8", errors="ignore")

        else:
            raise ValueError("Unsupported file format")

    except Exception as e:
        raise Exception(f"File parsing failed: {str(e)}")


def extract_pdf_text(content):
    """Extract text from PDF"""

    text = ""

    pdf_reader = PyPDF2.PdfReader(BytesIO(content))

    for page in pdf_reader.pages:
        extracted = page.extract_text()
        if extracted:
            text += extracted + "\n"

    return text.strip()


def extract_docx_text(content):
    """Extract text from DOCX"""

    doc = Document(BytesIO(content))

    text = []

    for paragraph in doc.paragraphs:
        if paragraph.text.strip():
            text.append(paragraph.text)

    return "\n".join(text).strip()
