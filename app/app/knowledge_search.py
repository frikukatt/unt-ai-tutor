from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models import KnowledgeChunk


def search_knowledge_relevant(
    db: Session,
    query: str,
    subject: str | None = None,
    limit: int = 5
):
    """
    Ищет наиболее релевантные фрагменты Knowledge Base.

    В отличие от простого поиска:
    - учитывает отдельные слова запроса;
    - считает количество совпадений;
    - сортирует chunks по количеству совпавших слов;
    - дополнительно учитывает название книги.
    """

    words = [
        word.strip(".,:;!?()[]{}\"'").lower()
        for word in query.split()
        if len(word.strip(".,:;!?()[]{}\"'")) >= 3
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
            KnowledgeChunk.content.ilike(f"%{word}%")
        )

    db_query = db_query.filter(or_(*conditions))

    candidates = db_query.limit(100).all()

    scored = []

    for chunk in candidates:
        content_lower = chunk.content.lower()

        score = 0

        for word in words:
            if word in content_lower:
                score += 1

        if chunk.book_title:
            book_title_lower = chunk.book_title.lower()

            for word in words:
                if word in book_title_lower:
                    score += 1

        scored.append(
            (score, chunk)
        )

    scored.sort(
        key=lambda item: item[0],
        reverse=True
    )

    return [
        chunk
        for score, chunk in scored[:limit]
        if score > 0
    ]


def build_relevant_knowledge_context(
    db: Session,
    query: str,
    subject: str | None = None,
    limit: int = 5
) -> str:
    """
    Создаёт текстовый контекст из найденных материалов
    для передачи AI.
    """

    chunks = search_knowledge_relevant(
        db=db,
        query=query,
        subject=subject,
        limit=limit
    )

    if not chunks:
        return (
            "Релевантных фрагментов учебных материалов "
            "в базе знаний не найдено."
        )

    context_parts = []

    for index, chunk in enumerate(chunks, start=1):
        context_parts.append(
            f"""
Источник {index}:
Книга: {chunk.book_title}
Страница: {chunk.page}
Раздел: {chunk.chapter or "не указан"}

Материал:
{chunk.content}
"""
        )

    return "\n---\n".join(context_parts)