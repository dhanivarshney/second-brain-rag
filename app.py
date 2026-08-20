import streamlit as st
import os
import base64
from ingest import ingest_file
from rag_chain import ask_question
from utils import reset_database, clear_uploads

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

st.set_page_config(
    page_title="Second Brain — Offline RAG Assistant",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------- Custom CSS ----------
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(180deg, #0a0e1a 0%, #0d1220 100%);
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    .main-header {
        text-align: center;
        padding: 1.5rem 0 1rem 0;
    }
    .main-header h1 {
        font-size: 2.6rem;
        font-weight: 800;
        background: linear-gradient(90deg, #4f8cff, #7c3aed, #22d3ee);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .main-header p {
        color: #94a3b8;
        font-size: 1rem;
        letter-spacing: 0.3px;
    }

    .badge-row {
        display: flex;
        justify-content: center;
        gap: 0.6rem;
        margin-bottom: 1.5rem;
        flex-wrap: wrap;
    }
    .badge {
        background: rgba(79, 140, 255, 0.1);
        border: 1px solid rgba(79, 140, 255, 0.3);
        color: #7dd3fc;
        padding: 0.3rem 0.9rem;
        border-radius: 20px;
        font-size: 0.78rem;
        font-weight: 500;
    }

    section[data-testid="stSidebar"] {
        background: #0d1220;
        border-right: 1px solid rgba(255,255,255,0.06);
    }
    section[data-testid="stSidebar"] h2, 
    section[data-testid="stSidebar"] h3 {
        color: #e2e8f0;
    }

    .file-card {
        background: rgba(34, 211, 238, 0.06);
        border: 1px solid rgba(34, 211, 238, 0.2);
        border-radius: 10px;
        padding: 0.5rem 0.8rem;
        margin-bottom: 0.4rem;
        color: #cbd5e1;
        font-size: 0.85rem;
    }

    .privacy-box {
        background: rgba(34, 197, 94, 0.08);
        border: 1px solid rgba(34, 197, 94, 0.25);
        border-radius: 10px;
        padding: 0.7rem;
        text-align: center;
        color: #86efac;
        font-size: 0.8rem;
        margin-top: 1rem;
    }

    div[data-testid="stChatMessage"] {
        border-radius: 14px;
        padding: 0.3rem 0.6rem;
    }

    .stButton button {
        border-radius: 8px;
        border: 1px solid rgba(239, 68, 68, 0.4);
        color: #fca5a5;
        background: rgba(239, 68, 68, 0.08);
        font-weight: 500;
    }
    .stButton button:hover {
        border-color: #ef4444;
        color: #ef4444;
        background: rgba(239, 68, 68, 0.15);
    }
</style>
""", unsafe_allow_html=True)

# ---------- Header ----------
st.markdown("""
<div class="main-header">
    <h1>🧠 Second Brain</h1>
    <p>Your Private, Offline AI Document & Note Assistant</p>
</div>
<div class="badge-row">
    <span class="badge">🔒 100% Offline</span>
    <span class="badge">⚡ Local LLM</span>
    <span class="badge">📄 Multi-format</span>
    <span class="badge">🔍 Source Cited</span>
</div>
""", unsafe_allow_html=True)

# ---------- Session state ----------
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "files_ingested" not in st.session_state:
    # Uploads folder me jo bhi files already hain unhe list me daalo
    if os.path.exists(UPLOAD_DIR):
        st.session_state.files_ingested = os.listdir(UPLOAD_DIR)
    else:
        st.session_state.files_ingested = []

if "viewing_file" not in st.session_state:
    st.session_state.viewing_file = None

# ---------- Helper: file preview ----------
def show_pdf(file_path):
    with open(file_path, "rb") as f:
        base64_pdf = base64.b64encode(f.read()).decode('utf-8')
    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="650" style="border-radius:10px; border:1px solid rgba(255,255,255,0.1);"></iframe>'
    st.markdown(pdf_display, unsafe_allow_html=True)

def show_text_file(file_path):
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    st.text_area("File content", content, height=500, label_visibility="collapsed")

def show_docx_file(file_path):
    import docx2txt
    text = docx2txt.process(file_path)
    st.text_area("File content", text, height=500, label_visibility="collapsed")

# ---------- Sidebar ----------
with st.sidebar:
    st.markdown("### 📁 Knowledge Base")
    st.caption("Upload your files to start chatting")

    uploaded_files = st.file_uploader(
        "Drop PDF, DOCX or TXT",
        type=["pdf", "docx", "txt"],
        accept_multiple_files=True,
        label_visibility="collapsed"
    )

    if uploaded_files:
        for file in uploaded_files:
            if file.name not in st.session_state.files_ingested:
                file_path = os.path.join(UPLOAD_DIR, file.name)
                with open(file_path, "wb") as f:
                    f.write(file.getbuffer())

                with st.spinner(f"Reading {file.name}..."):
                    chunk_count = ingest_file(file_path)

                st.session_state.files_ingested.append(file.name)
                st.toast(f"✅ {file.name} indexed ({chunk_count} chunks)")

    st.divider()
    st.markdown("### 📚 Indexed Files")
    if st.session_state.files_ingested:
        for f in st.session_state.files_ingested:
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.markdown(f'<div class="file-card">📄 {f}</div>', unsafe_allow_html=True)
            with col2:
                if st.button("👁️", key=f"view_{f}", help="Preview file"):
                    st.session_state.viewing_file = f
                    st.rerun()
            with col3:
                if st.button("🗑️", key=f"del_{f}", help="Remove file"):
                    file_path = os.path.join(UPLOAD_DIR, f)
                    if os.path.exists(file_path):
                        os.remove(file_path)
                    st.session_state.files_ingested.remove(f)
                    if st.session_state.viewing_file == f:
                        st.session_state.viewing_file = None
                    st.rerun()
    else:
        st.caption("No documents yet — upload something above")

    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Files", len(st.session_state.files_ingested))
    with col2:
        st.metric("Messages", len(st.session_state.chat_history))

    st.divider()
    if st.button("🗑️ Clear All Data", use_container_width=True):
        reset_database()
        clear_uploads()
        st.session_state.files_ingested = []
        st.session_state.chat_history = []
        st.session_state.viewing_file = None
        st.rerun()

    st.markdown("""
    <div class="privacy-box">
        🔐 Your data never leaves this device.<br>No internet. No cloud. No leaks.
    </div>
    """, unsafe_allow_html=True)

# ---------- File preview panel ----------
if st.session_state.viewing_file:
    file_path = os.path.join(UPLOAD_DIR, st.session_state.viewing_file)

    header_col1, header_col2 = st.columns([5, 1])
    with header_col1:
        st.markdown(f"### 📄 Previewing: {st.session_state.viewing_file}")
    with header_col2:
        if st.button("✖️ Close", use_container_width=True):
            st.session_state.viewing_file = None
            st.rerun()

    if os.path.exists(file_path):
        if file_path.endswith(".pdf"):
            show_pdf(file_path)
        elif file_path.endswith(".txt"):
            show_text_file(file_path)
        elif file_path.endswith(".docx"):
            show_docx_file(file_path)
    else:
        st.error("File not found on disk.")

    st.divider()

# ---------- Main chat area ----------
if not st.session_state.chat_history and not st.session_state.viewing_file:
    st.markdown("""
    <div style="text-align:center; padding: 3rem 1rem; color:#64748b;">
        <h3 style="color:#94a3b8;">👋 Start a conversation</h3>
        <p>Upload a document from the sidebar, then ask anything about it.</p>
    </div>
    """, unsafe_allow_html=True)

for msg in st.session_state.chat_history:
    avatar = "🧑‍💻" if msg["role"] == "user" else "🧠"
    with st.chat_message(msg["role"], avatar=avatar):
        st.write(msg["content"])
        if msg["role"] == "assistant" and msg.get("sources"):
            with st.expander("📌 View Sources"):
                for src in msg["sources"]:
                    st.markdown(f"- `{src}`")

user_query = st.chat_input("Ask something about your documents...")

if user_query:
    st.session_state.chat_history.append({"role": "user", "content": user_query})
    with st.chat_message("user", avatar="🧑‍💻"):
        st.write(user_query)

    with st.chat_message("assistant", avatar="🧠"):
        with st.spinner("Thinking through your documents..."):
            result = ask_question(user_query, chat_history=st.session_state.chat_history)
            st.write(result["answer"])
            if result["sources"]:
             with st.expander("📌 View Sources"):
              for src in result["sources"]:
            # src format: "uploads/filename.pdf (page 2)"
               filename = src.split(" (page")[0].split("\\")[-1].split("/")[-1]
               if st.button(f"📄 {src}", key=f"src_{filename}_{src}"):
                 st.session_state.viewing_file = filename
                 st.rerun()
    st.session_state.chat_history.append({
        "role": "assistant",
        "content": result["answer"],
        "sources": result["sources"]
    })