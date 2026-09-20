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


STOP_WORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
    "any", "are", "aren't", "as", "at", "be", "because", "been", "before", "being",
    "below", "between", "both", "but", "by", "can", "can't", "cannot", "could",
    "couldn't", "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down",
    "during", "each", "few", "for", "from", "further", "had", "hadn't", "has",
    "hasn't", "have", "haven't", "having", "he", "he'd", "he'll", "he's", "her",
    "here", "here's", "hers", "herself", "him", "himself", "his", "how", "how's",
    "i", "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is", "isn't", "it",
    "it's", "its", "itself", "let's", "me", "more", "most", "mustn't", "my",
    "myself", "no", "nor", "not", "of", "off", "on", "once", "only", "or",
    "other", "ought", "our", "ours", "ourselves", "out", "over", "own", "same",
    "shan't", "she", "she'd", "she'll", "she's", "should", "shouldn't", "so",
    "some", "such", "than", "that", "that's", "the", "their", "theirs", "them",
    "themselves", "then", "there", "there's", "these", "they", "they'd", "they'll",
    "they're", "they've", "this", "those", "through", "to", "too", "under",
    "until", "up", "very", "was", "wasn't", "we", "we'd", "we'll", "we're",
    "we've", "were", "weren't", "what", "what's", "when", "when's", "where",
    "where's", "which", "while", "who", "who's", "whom", "why", "why's", "with",
    "won't", "would", "wouldn't", "you", "you'd", "you'll", "you're", "you've",
    "your", "yours", "yourself", "yourselves", "tell", "explain", "describe",
    "bta", "de", "kya", "hai", "me", "se", "ko", "ka", "ki", "ke"
}


class LocalVectorStore:
    def __init__(self):
        self.embeddings = LocalHashEmbeddings()

    def similarity_search(self, query, k=8, doc_filter=None):
        query_vector = self.embeddings.embed_query(query)
        q_tokens = [
            w for w in re.findall(r"[\w']+", query.lower())
            if w not in STOP_WORDS and len(w) > 1
        ]
        query_lower = query.lower()
        records = _load_index()

        # Handle document filtering
        target_docs = None
        if doc_filter:
            if isinstance(doc_filter, str):
                target_docs = {os.path.basename(doc_filter).lower()}
            elif isinstance(doc_filter, (list, set, tuple)):
                target_docs = {os.path.basename(d).lower() for d in doc_filter}

        scored = []
        for record in records:
            source_path = record.get("metadata", {}).get("source", "")
            base_name = os.path.basename(source_path).lower()
            if target_docs and base_name not in target_docs:
                continue

            vector = record.get("embedding", [])
            # Cosine component
            vector_score = sum(left * right for left, right in zip(query_vector, vector)) if len(vector) == len(query_vector) else 0.0

            # Keyword & phrase match component (BM25-style frequency + position bonus)
            text_lower = record["text"].lower()
            kw_score = 0.0
            matched_terms = 0
            for token in q_tokens:
                if token in text_lower:
                    matched_terms += 1
                    count = text_lower.count(token)
                    kw_score += 2.0 + min(count * 0.4, 3.0)

            # Bonus if multiple query tokens co-occur
            if len(q_tokens) >= 2 and matched_terms >= 2:
                kw_score += (matched_terms / len(q_tokens)) * 3.0

            # Bonus for exact phrase matching
            if len(query_lower) > 5 and query_lower in text_lower:
                kw_score += 4.0

            total_score = vector_score + kw_score
            scored.append((total_score, record, base_name))

        scored.sort(key=lambda item: item[0], reverse=True)

        # Multi-document balancing: If querying across all documents, prevent one single large document from crowding out others
        if not target_docs and len(scored) > k:
            doc_groups = {}
            for item in scored:
                doc_groups.setdefault(item[2], []).append(item)

            if len(doc_groups) > 1:
                # Interleave top chunks from distinct matching documents
                balanced = []
                # Allow max k//2 from any single document unless others are exhausted
                per_doc_limit = max(2, (k // len(doc_groups)) + 2)
                doc_counts = {doc: 0 for doc in doc_groups}

                for item in scored:
                    doc = item[2]
                    if doc_counts[doc] < per_doc_limit:
                        balanced.append(item)
                        doc_counts[doc] += 1
                    if len(balanced) >= k:
                        break

                # Fill remaining if needed
                if len(balanced) < k:
                    seen = set(id(item[1]) for item in balanced)
                    for item in scored:
                        if id(item[1]) not in seen:
                            balanced.append(item)
                            if len(balanced) >= k:
                                break
                scored = balanced

        return [Document(page_content=record["text"], metadata=record["metadata"]) for _, record, _ in scored[:k]]

    def get_document_chunks(self, doc_name):
        """Retrieve all text chunks belonging to a specific document."""
        target = os.path.basename(doc_name).lower()
        records = _load_index()
        docs = []
        for record in records:
            source = record.get("metadata", {}).get("source", "")
            if os.path.basename(source).lower() == target:
                docs.append(Document(page_content=record["text"], metadata=record["metadata"]))
        docs.sort(key=lambda d: d.metadata.get("page", 0))
        return docs

    def get_indexed_documents_summary(self):
        """Return information about all indexed documents."""
        records = _load_index()
        summary = {}
        for record in records:
            source = record.get("metadata", {}).get("source", "")
            if not source:
                continue
            name = os.path.basename(source)
            if name not in summary:
                summary[name] = {"source": source, "chunks": 0, "pages": set()}
            summary[name]["chunks"] += 1
            page = record.get("metadata", {}).get("page")
            if isinstance(page, int):
                summary[name]["pages"].add(page)

        return [
            {
                "name": name,
                "source": data["source"],
                "chunks": data["chunks"],
                "page_count": len(data["pages"]) if data["pages"] else 1
            }
            for name, data in summary.items()
        ]


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
