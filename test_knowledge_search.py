from app.database import SessionLocal
from app.knowledge import search_knowledge


db = SessionLocal()

try:
    results = search_knowledge(
        db=db,
        query="оперативная память RAM ROM",
        subject="informatics",
        limit=5
    )

    print()
    print("=" * 70)
    print("KNOWLEDGE SEARCH RESULTS")
    print("=" * 70)

    print(f"Found: {len(results)}")

    for i, chunk in enumerate(results, start=1):
        print()
        print(f"--- RESULT {i} ---")
        print(f"Book: {chunk.book_title}")
        print(f"Page: {chunk.page}")
        print(f"Chunk: {chunk.chunk_index}")
        print("Content:")
        print(chunk.content[:1000])

finally:
    db.close()