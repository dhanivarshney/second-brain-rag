import os
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.vectorstores import Chroma

DB_DIR = "db"
UPLOAD_DIR = "uploads"

def load_file(file_path):
    """File extension ke hisaab se sahi loader use karo"""
    if file_path.endswith(".pdf"):
        loader = PyPDFLoader(file_path)
    elif file_path.endswith(".docx"):
        loader = Docx2txtLoader(file_path)
    elif file_path.endswith(".txt"):
        loader = TextLoader(file_path, encoding="utf-8")
    else:
        raise ValueError(f"Unsupported file type: {file_path}")
    return loader.load()

def chunk_documents(documents, chunk_size=1000, chunk_overlap=150):
    """Documents ko chhote chunks me todo"""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )
    return splitter.split_documents(documents)

def get_embeddings():
    """Ollama local embedding model"""
    return OllamaEmbeddings(model="nomic-embed-text")

def ingest_file(file_path):
    """
    Ek file lo, load karo, chunk karo, embed karo, 
    aur chromadb me store karo. Ye function app.py se call hoga.
    """
    docs = load_file(file_path)
    chunks = chunk_documents(docs)

    embeddings = get_embeddings()

    vectordb = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=DB_DIR
    )
    vectordb.persist()

    return len(chunks)

def get_vectorstore():
    """Existing chromadb load karo (query ke time use hoga)"""
    embeddings = get_embeddings()
    return Chroma(
        persist_directory=DB_DIR,
        embedding_function=embeddings
    )

if __name__ == "__main__":
    # Testing ke liye - sample_docs folder me koi file daal ke test karo
    test_file = "sample_docs/test.pdf"
    if os.path.exists(test_file):
        count = ingest_file(test_file)
        print(f"Ingested {count} chunks from {test_file}")
    else:
        print("Test file nahi mila, sample_docs/ me daal ke try karo")