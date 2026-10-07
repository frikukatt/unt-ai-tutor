from app.database import SessionLocal
from app.knowledge_search import search_knowledge_relevant


db = SessionLocal()

try:
    results = search_knowledge_relevant(
        db=db,
        query="оперативная память RAM ROM",
        subject="informatics",
        limit=5
    )

    print()
    print("=" * 70)
    print("RELEVANT KNOWLEDGE SEARCH")
    print("=" * 70)

    print(f"Found: {len(results)}")

    for i, chunk in enumerate(results, start=1):
        print()
        print(f"--- RESULT {i} ---")
        print(f"Book: {chunk.book_title}")
        print(f"Page: {chunk.page}")
        print(f"Chunk: {chunk.chunk_index}")
        print()
        print(chunk.content[:1200])

finally:
    db.close()