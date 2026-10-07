from pathlib import Path

import pymupdf
import pytesseract
from PIL import Image
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import KnowledgeChunk


# =========================
# TESSERACT
# =========================

pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)


# =========================
# PATHS
# =========================

BASE_DIR = Path(__file__).resolve().parent.parent
BOOKS_DIR = BASE_DIR / "knowledge_books"


# =========================
# SETTINGS
# =========================

CHUNK_SIZE = 1200
CHUNK_OVERLAP = 200

# Если страница содержит меньше этого количества текста,
# считаем, что обычное извлечение текста не сработало
# и используем OCR.
MIN_TEXT_LENGTH = 80


# =========================
# PDF TEXT
# =========================

def extract_pdf_text(page) -> str:
    """
    Сначала пытаемся получить настоящий текст PDF.
    """

    text = page.get_text("text")

    return text.strip()


# =========================
# OCR
# =========================

def extract_ocr_text(page) -> str:
    """
    Рендерим PDF-страницу как изображение
    и распознаём казахский/русский/английский текст.
    """

    pix = page.get_pixmap(
        matrix=pymupdf.Matrix(2, 2),
        alpha=False
    )

    image = Image.frombytes(
        "RGB",
        [pix.width, pix.height],
        pix.samples
    )

    text = pytesseract.image_to_string(
        image,
        lang="kaz+rus+eng",
        config="--psm 6"
    )

    return text.strip()


# =========================
# PAGE TEXT
# =========================

def extract_page_text(page) -> str:
    """
    Используем обычный текст PDF.
    Если его практически нет — используем OCR.
    """

    text = extract_pdf_text(page)

    if len(text) >= MIN_TEXT_LENGTH:
        return text

    return extract_ocr_text(page)


# =========================
# CLEAN TEXT
# =========================

def clean_text(text: str) -> str:
    """
    Минимальная очистка OCR/текста.

    Не пытаемся агрессивно исправлять слова,
    чтобы не испортить содержимое учебника.
    """

    lines = []

    for line in text.splitlines():
        line = " ".join(line.split())

        if line:
            lines.append(line)

    return "\n".join(lines)


# =========================
# CHUNKING
# =========================

def split_into_chunks(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP
) -> list[str]:

    if not text:
        return []

    chunks = []

    start = 0

    while start < len(text):
        end = start + chunk_size

        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end >= len(text):
            break

        start = end - overlap

    return chunks


# =========================
# BOOK TITLE
# =========================

def get_book_title(pdf_path: Path) -> str:
    return pdf_path.stem


# =========================
# SAVE BOOK
# =========================

def process_pdf(
    pdf_path: Path,
    db: Session,
    subject: str = "informatics"
):
    print()
    print("=" * 60)
    print(f"Processing: {pdf_path.name}")
    print("=" * 60)

    pdf = pymupdf.open(pdf_path)

    saved_chunks = 0

    for page_number, page in enumerate(pdf):

        print(
            f"Page {page_number + 1}/{len(pdf)}",
            end=" -> "
        )

        text = extract_page_text(page)

        text = clean_text(text)

        if not text:
            print("no text")
            continue

        chunks = split_into_chunks(text)

        for chunk_index, chunk in enumerate(chunks):

            knowledge_chunk = KnowledgeChunk(
                subject=subject,
                book_title=get_book_title(pdf_path),
                chapter=None,
                page=page_number + 1,
                chunk_index=chunk_index,
                content=chunk,
                source_url=None
            )

            db.add(knowledge_chunk)

            saved_chunks += 1

        print(f"{len(chunks)} chunks")

    db.commit()

    pdf.close()

    print()
    print(f"Saved chunks: {saved_chunks}")

    return saved_chunks


# =========================
# SEARCH KNOWLEDGE
# =========================

def search_knowledge(
    db: Session,
    query: str,
    subject: str | None = None,
    limit: int = 5
):
    """
    Простой keyword search по базе знаний.

    Позже этот слой можно заменить/расширить
    embeddings + vector search.
    """

    words = [
        word.strip()
        for word in query.split()
        if len(word.strip()) >= 3
    ]

    if not words:
        return []

    db_query = db.query(KnowledgeChunk)

    if subject:
        db_query = db_query.filter(
            KnowledgeChunk.subject == subject
        )

    conditions = []

    for word in words:
        conditions.append(
            KnowledgeChunk.content.ilike(
                f"%{word}%"
            )
        )

    from sqlalchemy import or_

    db_query = db_query.filter(
        or_(*conditions)
    )

    return (
        db_query
        .order_by(KnowledgeChunk.id.desc())
        .limit(limit)
        .all()
    )


# =========================
# BUILD CONTEXT FOR AI
# =========================

def build_knowledge_context(
    db: Session,
    query: str,
    subject: str | None = None,
    limit: int = 5
) -> str:

    chunks = search_knowledge(
        db=db,
        query=query,
        subject=subject,
        limit=limit
    )

    if not chunks:
        return "Подходящих фрагментов учебных материалов не найдено."

    context_parts = []

    for chunk in chunks:

        context_parts.append(
            f"""
Источник: {chunk.book_title}
Страница: {chunk.page}

{chunk.content}
"""
        )

    return "\n---\n".join(context_parts)


# =========================
# IMPORT ALL BOOKS
# =========================

def import_all_books():

    if not BOOKS_DIR.exists():
        print(
            f"Knowledge directory not found: {BOOKS_DIR}"
        )
        return

    pdf_files = list(
        BOOKS_DIR.glob("*.pdf")
    )

    if not pdf_files:
        print("No PDF files found.")
        return

    db = SessionLocal()

    try:

        for pdf_path in pdf_files:

            process_pdf(
                pdf_path=pdf_path,
                db=db,
                subject="informatics"
            )

    finally:
        db.close()


# =========================
# MAIN
# =========================

if __name__ == "__main__":
    import_all_books()