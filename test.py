from langchain_community.document_loaders import PyPDFLoader

loader = PyPDFLoader("uploads/mechanics.pdf")
docs = loader.load()

print(f"Total pages loaded: {len(docs)}")

for i in [0, 10, 30, 50, 100]:
    print(f"\n--- Page {i} content ---")
    content = docs[i].page_content.strip()
    if content:
        print(content[:300])
    else:
        print("(EMPTY - no text extracted)")