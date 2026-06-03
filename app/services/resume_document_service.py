import uuid
from typing import Optional, Dict, List
from app.database.db import get_db


def row_to_dict(row) -> Optional[Dict]:
    return dict(row) if row else None


def create_resume_document(
    user_id: str,
    title: str,
    resume_text: str,
    cover_letter_text: Optional[str] = None,
    template: str = "default",
    pdf_filename: Optional[str] = None,
) -> Dict:
    """Create a persistent saved resume document for an authenticated user."""
    document_id = str(uuid.uuid4())

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO resume_documents (
                document_id,
                user_id,
                title,
                resume_text,
                cover_letter_text,
                template,
                pdf_filename
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                document_id,
                user_id,
                title,
                resume_text,
                cover_letter_text or "",
                template or "default",
                pdf_filename,
            ),
        )
        conn.commit()

    return get_resume_document(user_id=user_id, document_id=document_id)


def list_resume_documents(user_id: str) -> List[Dict]:
    """Return all saved resume documents for a user, newest first."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                document_id,
                user_id,
                title,
                template,
                pdf_filename,
                created_at,
                updated_at
            FROM resume_documents
            WHERE user_id = ?
            ORDER BY updated_at DESC, created_at DESC
            """,
            (user_id,),
        )
        return [dict(row) for row in cursor.fetchall()]


def get_resume_document(user_id: str, document_id: str) -> Optional[Dict]:
    """Return one saved resume document belonging to the user."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM resume_documents
            WHERE user_id = ? AND document_id = ?
            """,
            (user_id, document_id),
        )
        return row_to_dict(cursor.fetchone())


def update_resume_document(
    user_id: str,
    document_id: str,
    title: Optional[str] = None,
    resume_text: Optional[str] = None,
    cover_letter_text: Optional[str] = None,
    template: Optional[str] = None,
    pdf_filename: Optional[str] = None,
) -> Optional[Dict]:
    """Update editable saved resume fields."""
    existing = get_resume_document(user_id=user_id, document_id=document_id)
    if not existing:
        return None
    create_resume_version(existing)

    new_title = title if title is not None else existing["title"]
    new_resume_text = resume_text if resume_text is not None else existing["resume_text"]
    new_cover_letter_text = cover_letter_text if cover_letter_text is not None else existing.get("cover_letter_text", "")
    new_template = template if template is not None else existing.get("template", "default")
    new_pdf_filename = pdf_filename if pdf_filename is not None else existing.get("pdf_filename")

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE resume_documents
            SET title = ?,
                resume_text = ?,
                cover_letter_text = ?,
                template = ?,
                pdf_filename = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ? AND document_id = ?
            """,
            (
                new_title,
                new_resume_text,
                new_cover_letter_text,
                new_template,
                new_pdf_filename,
                user_id,
                document_id,
            ),
        )
        conn.commit()

    return get_resume_document(user_id=user_id, document_id=document_id)


def duplicate_resume_document(user_id: str, document_id: str) -> Optional[Dict]:
    """Duplicate a saved resume for the same user."""
    existing = get_resume_document(user_id=user_id, document_id=document_id)
    if not existing:
        return None

    return create_resume_document(
        user_id=user_id,
        title=f"{existing['title']} Copy",
        resume_text=existing["resume_text"],
        cover_letter_text=existing.get("cover_letter_text", ""),
        template=existing.get("template", "default"),
        pdf_filename=None,
    )


def delete_resume_document(user_id: str, document_id: str) -> bool:
    """Delete a saved resume document owned by the user."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            DELETE FROM resume_documents
            WHERE user_id = ? AND document_id = ?
            """,
            (user_id, document_id),
        )
        conn.commit()
        return cursor.rowcount > 0
        
def create_resume_version(existing_resume):
