from ingest import get_vectorstore

db = get_vectorstore()
results = db.similarity_search("classification bta de cyber crime ki", k=12)

for i, doc in enumerate(results):
    print(f"\n--- Chunk {i+1} (page {doc.metadata.get('page')}) ---")
    print(doc.page_content[:200])