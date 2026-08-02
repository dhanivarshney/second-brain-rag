import os
import shutil

DB_DIR = "db"
UPLOAD_DIR = "uploads"

ALLOWED_EXTENSIONS = [".pdf", ".docx", ".txt"]

def is_valid_file(filename):
    """Check karo file type supported hai ya nahi"""
    ext = os.path.splitext(filename)[1].lower()
    return ext in ALLOWED_EXTENSIONS

def get_file_size_mb(file_path):
    """File size MB me return karo"""
    size_bytes = os.path.getsize(file_path)
    return round(size_bytes / (1024 * 1024), 2)

def reset_database():
    """
    ChromaDB clear karo. Windows lock ki wajah se kuch files delete
    nahi ho paayengi to unhe try/except se ignore karo.
    """
    if os.path.exists(DB_DIR):
        try:
            shutil.rmtree(DB_DIR)
        except Exception:
            pass
    os.makedirs(DB_DIR, exist_ok=True)
    return True

def clear_uploads():
    """Uploaded files delete karo (db se alag, sirf raw files)"""
    if os.path.exists(UPLOAD_DIR):
        try:
            shutil.rmtree(UPLOAD_DIR)
        except Exception:
            pass
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    return True

def list_uploaded_files():
    """Uploads folder me abhi kaunsi files hain"""
    if not os.path.exists(UPLOAD_DIR):
        return []
    return os.listdir(UPLOAD_DIR)

def format_source_label(source_path, page):
    """Sources ko clean UI-friendly format me dikhao"""
    filename = os.path.basename(source_path)
    if page != "N/A":
        return f"{filename} — Page {int(page) + 1}"
    return filename