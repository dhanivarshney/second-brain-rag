import hashlib
import io
import json
import math
import os
import re
import tempfile

import fitz
import pytesseract
from langchain_community.document_loaders import Docx2txtLoader, TextLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from PIL import Image

DB_DIR = "db"
UPLOAD_DIR = "uploads"
INDEX_FILE = os.path.join(DB_DIR, "second_brain_index.json")
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


class LocalHashEmbeddings:
    """Fast local keyword embeddings with no server or model dependency."""

    dimensions = 384

    def _embed(self, text):
        vector = [0.0] * self.dimensions
        for token in re.findall(r"[\w']+", text.lower()):
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimensions
            vector[index] += 1.0 if digest[4] % 2 else -1.0
        magnitude = math.sqrt(sum(value * value for value in vector))
        return [value / magnitude for value in vector] if magnitude else vector

    def embed_documents(self, texts):
        return [self._embed(text) for text in texts]

    def embed_query(self, text):
        return self._embed(text)


def load_pdf_with_ocr(file_path):
    try:
        pdf = fitz.open(file_path)
    except Exception as error:
        raise ValueError(f"Could not open PDF file: {error}") from error

    documents = []
    for page_number, page in enumerate(pdf):
        try:
            text = page.get_text().strip()
            if not text:
                pixmap = page.get_pixmap(dpi=180)
                text = pytesseract.image_to_string(Image.open(io.BytesIO(pixmap.tobytes("png"))))
            if text.strip():
                documents.append(Document(page_content=text, metadata={"source": file_path, "page": page_number}))
        except Exception:
            continue
    pdf.close()
    if not documents:
        raise ValueError("No readable text could be extracted from this PDF.")
    return documents


def load_file(file_path):
    extension = os.path.splitext(file_path)[1].lower()
    if extension == ".pdf":
        return load_pdf_with_ocr(file_path)
    if extension == ".docx":
        return Docx2txtLoader(file_path).load()
    if extension == ".txt":
        return TextLoader(file_path, encoding="utf-8").load()
    raise ValueError(f"Unsupported file type: {file_path}")


def chunk_documents(documents, chunk_size=1000, chunk_overlap=150):
    return RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap).split_documents(documents)


def _emit_progress(callback, stage, percentage):
    if callback:
        callback(stage, percentage)


def _load_index():
    if not os.path.exists(INDEX_FILE):
        return []
    try:
        with open(INDEX_FILE, "r", encoding="utf-8") as index_file:
            data = json.load(index_file)
        return data if isinstance(data, list) else []
    except (OSError, json.JSONDecodeError):
        return []


def _save_index(records):
    os.makedirs(DB_DIR, exist_ok=True)
    descriptor, temporary_path = tempfile.mkstemp(prefix="second_brain_", suffix=".json", dir=DB_DIR)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as index_file:
            json.dump(records, index_file, ensure_ascii=False, separators=(",", ":"))
        os.replace(temporary_path, INDEX_FILE)
    finally:
        if os.path.exists(temporary_path):
            os.remove(temporary_path)


def remove_file_from_index(file_path):
    records = _load_index()
    _save_index([record for record in records if record.get("metadata", {}).get("source") != file_path])


def get_indexed_file_names():
    return sorted({
        os.path.basename(record["metadata"]["source"])
        for record in _load_index()
        if record.get("metadata", {}).get("source")
    })


class LocalVectorStore:
    def __init__(self):
        self.embeddings = LocalHashEmbeddings()

    def similarity_search(self, query, k=8):
        query_vector = self.embeddings.embed_query(query)
        scored = []
        for record in _load_index():
            vector = record.get("embedding", [])
            if len(vector) == len(query_vector):
                scored.append((sum(left * right for left, right in zip(query_vector, vector)), record))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [Document(page_content=record["text"], metadata=record["metadata"]) for _, record in scored[:k]]


def ingest_file(file_path, progress_callback=None):
    """Extract, embed, and persist a file without depending on Chroma services."""
    _emit_progress(progress_callback, "reading document", 12)
    documents = load_file(file_path)
    _emit_progress(progress_callback, "extracting text", 35)
    chunks = chunk_documents(documents)
    if not chunks:
        raise ValueError("No readable text chunks were created from this file.")
    for chunk in chunks:
        chunk.metadata["source"] = file_path

    _emit_progress(progress_callback, "preparing local search index", 50)
    embeddings = LocalHashEmbeddings()
    records = [record for record in _load_index() if record.get("metadata", {}).get("source") != file_path]
    total_chunks, batch_size = len(chunks), 48
    for start in range(0, total_chunks, batch_size):
        batch = chunks[start:start + batch_size]
        vectors = embeddings.embed_documents([chunk.page_content for chunk in batch])
        records.extend({"text": chunk.page_content, "metadata": chunk.metadata, "embedding": vector} for chunk, vector in zip(batch, vectors))
        completed = min(start + len(batch), total_chunks)
        _emit_progress(progress_callback, f"indexing {completed:,} of {total_chunks:,} knowledge chunks", 55 + int((completed / total_chunks) * 40))

    _emit_progress(progress_callback, "saving your local search index", 97)
    _save_index(records)
    _emit_progress(progress_callback, "finalizing local index", 99)
    return total_chunks


def get_vectorstore():
    return LocalVectorStore()
