import os
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.vectorstores import Chroma
import fitz  # pymupdf
import pytesseract
from PIL import Image
import io

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def load_pdf_with_ocr(file_path):
    """Scanned PDF se OCR ke through text nikalo"""
    from langchain_core.documents import Document
    
    doc = fitz.open(file_path)
    documents = []
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        
        # Pehle normal text try karo
        text = page.get_text().strip()
        
        # Agar text khali hai, to OCR karo
        if not text:
            pix = page.get_pixmap(dpi=200)
            img_data = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_data))
            text = pytesseract.image_to_string(img)
        
        if text.strip():
            documents.append(Document(
                page_content=text,
                metadata={"source": file_path, "page": page_num}
            ))
    
    doc.close()
    return documents

DB_DIR = "db"
UPLOAD_DIR = "uploads"

def load_file(file_path):
    if file_path.endswith(".pdf"):
        return load_pdf_with_ocr(file_path)
    elif file_path.endswith(".docx"):
        loader = Docx2txtLoader(file_path)
        return loader.load()
    elif file_path.endswith(".txt"):
        loader = TextLoader(file_path, encoding="utf-8")
        return loader.load()
    else:
        raise ValueError(f"Unsupported file type: {file_path}")

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