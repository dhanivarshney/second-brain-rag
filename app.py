import os
from html import escape

import streamlit as st
import streamlit.components.v1 as components

import auth

st.set_page_config(page_title="Second Brain | AI document intelligence", page_icon="🧠", layout="wide", initial_sidebar_state="expanded")
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


def inject_styles():
    st.markdown("""<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Manrope:wght@400;500;600;700;800&display=swap');
    :root { --ink:#eaf5ff; --muted:#94a8bd; --line:rgba(175,217,255,.14); --cyan:#70e5ff; }
    .stApp { background:#060b16; color:var(--ink); font-family:Manrope,sans-serif; }
    .stApp::before,.stApp::after { display:none; }
    #MainMenu, footer, header { visibility:hidden; }.block-container { max-width:1240px; padding-top:2.1rem; padding-bottom:3rem; }
    [data-testid="stSidebar"] { background:rgba(5,11,23,.93)!important; border-right:1px solid var(--line); } [data-testid="stSidebar"] > div:first-child { padding-top:1.5rem; }
    .stButton > button { border-radius:12px!important; font-family:Manrope,sans-serif!important; font-weight:700!important; min-height:43px; border:1px solid rgba(150,200,255,.18)!important; background:rgba(255,255,255,.035)!important; color:#dcecff!important; transition:.2s ease!important; }
    .stButton > button:hover { transform:translateY(-1px); border-color:rgba(112,229,255,.68)!important; color:white!important; background:rgba(112,229,255,.09)!important; box-shadow:0 9px 30px rgba(0,0,0,.22); }
    .stButton > button[kind="primary"] { background:linear-gradient(110deg,#75e8ff,#9194ff)!important; border:0!important; color:#07101e!important; box-shadow:0 10px 26px rgba(102,178,255,.23)!important; }
    .stTextInput input { border-radius:11px!important; background:rgba(255,255,255,.045)!important; border:1px solid var(--line)!important; color:white!important; }.stTextInput label,.stFileUploader label { color:#b8c8dc!important; font-weight:600!important; }
    [data-testid="stFileUploaderDropzone"] { border:1px dashed rgba(112,229,255,.45)!important; border-radius:16px!important; background:rgba(89,144,255,.045)!important; padding:1.1rem!important; } [data-testid="stChatMessage"] { border:1px solid var(--line); background:rgba(12,22,40,.6); border-radius:18px; }
    .brand-lockup { display:flex; align-items:center; gap:11px; padding:0 0 1.7rem; }.brand-mark { width:34px;height:34px;border-radius:11px;position:relative;background:conic-gradient(from 180deg,#70e5ff,#7a72ff,#d298ff,#70e5ff);box-shadow:0 0 22px rgba(112,229,255,.32); }.brand-mark:after{content:"";position:absolute;inset:7px;border-radius:8px;background:#081323}.brand-mark:before{content:"✦";position:absolute;z-index:1;inset:5px;text-align:center;color:#dffbff;font-size:17px}.eyebrow{color:#74e4ff;font:500 .67rem 'DM Mono',monospace;letter-spacing:.17em;text-transform:uppercase}.brand-name{color:white;font-size:.92rem;font-weight:800;letter-spacing:.05em}.nav-caption{color:#6d849d;font:500 .68rem 'DM Mono',monospace;letter-spacing:.11em;margin:1.15rem 0 .48rem}
    .page-kicker { color:#77e5ff;font:500 .74rem 'DM Mono',monospace;letter-spacing:.15em;text-transform:uppercase}.page-title{font-size:clamp(1.8rem,4vw,2.55rem);letter-spacing:-.055em;margin:.35rem 0 .5rem;color:#f5f9ff}.page-subtitle{color:var(--muted);max-width:670px;line-height:1.7;margin-bottom:1.7rem}.glass-card{background:linear-gradient(145deg,rgba(21,34,59,.72),rgba(8,16,31,.72));border:1px solid var(--line);border-radius:22px;padding:1.35rem;box-shadow:inset 0 1px rgba(255,255,255,.035),0 18px 55px rgba(0,0,0,.15)}.metric-label{color:#9bb0c9;font:500 .68rem 'DM Mono',monospace;letter-spacing:.12em}.metric-value{font-size:1.8rem;font-weight:800;letter-spacing:-.06em;color:white;margin-top:.35rem}.metric-hint{color:#70e5ff;font-size:.76rem;margin-top:.2rem}.file-row{padding:.84rem .1rem;border-bottom:1px solid rgba(175,217,255,.1)}.file-name{color:#e8f4ff;font-weight:700;font-size:.91rem}.file-meta{color:#8298b1;font-size:.75rem;margin-top:3px}.source-chip{display:inline-block;margin:3px 5px 0 0;padding:3px 8px;color:#8deaff;background:rgba(112,229,255,.08);border:1px solid rgba(112,229,255,.18);border-radius:999px;font-size:.7rem}.empty-state{text-align:center;padding:3.2rem 1rem;color:#9cb0c6}.brain-visual{margin:0 auto 1rem;color:#b7f5ff;font-size:4.4rem;line-height:1;filter:drop-shadow(0 0 18px rgba(112,229,255,.68));animation:float 3.5s ease-in-out infinite}
    .boot-wrap{min-height:calc(100dvh - 10rem);display:flex;align-items:center;justify-content:center;text-align:center;overflow:hidden;padding:2rem 1rem;position:relative;isolation:isolate;background:radial-gradient(circle at 50% 42%,#1c3974 0%,#101d3e 30%,#070d1c 70%);border:1px solid rgba(112,229,255,.12);border-radius:28px}.boot-stage{position:relative;z-index:2;width:min(100%,900px);padding:3rem 1rem}.boot-stage:before{content:"";position:absolute;inset:7% 16%;z-index:-1;background:radial-gradient(ellipse,rgba(91,122,255,.5),transparent 65%);filter:blur(14px);animation:glow-shift 6s ease-in-out infinite}.boot-brain{width:170px;height:170px;margin:0 auto 2.5rem;display:grid;place-items:center;font-size:7.4rem;line-height:1;position:relative;z-index:2;filter:drop-shadow(0 0 26px rgba(112,229,255,.72));animation:pulse 3s ease-in-out infinite}.boot-brain:before,.boot-brain:after{content:"";position:absolute;inset:-10px;border:1px solid rgba(119,226,255,.65);border-radius:50%;animation:orbit 6s linear infinite}.boot-brain:after{inset:-31px;border-color:rgba(159,140,255,.45);animation-direction:reverse;animation-duration:9s}.neural-dot{position:absolute;z-index:2;width:7px;height:7px;border-radius:50%;background:#94f0ff;box-shadow:0 0 16px #70e5ff;animation:drift 4s ease-in-out infinite}.dot-one{top:17%;left:12%}.dot-two{top:27%;right:12%;animation-delay:-1.4s}.dot-three{bottom:21%;left:19%;animation-delay:-2.5s}.dot-four{bottom:28%;right:17%;animation-delay:-.7s}.boot-title{position:relative;z-index:2;font-size:clamp(3.45rem,10vw,7.7rem);font-weight:800;line-height:.92;letter-spacing:-.1em;color:#fff;margin:0;text-shadow:0 0 40px rgba(120,229,255,.42);animation:wordmark-in .9s cubic-bezier(.2,.8,.2,1) both}.boot-title span{display:block;color:#a9f4ff;font-size:clamp(.72rem,1.3vw,1rem);font-family:'DM Mono',monospace;letter-spacing:.52em;margin:.85rem 0 0 .52em;text-transform:uppercase}.boot-copy{position:relative;z-index:2;max-width:550px;margin:1.25rem auto 2.35rem;color:#d0e2f6;font-size:clamp(.94rem,2.2vw,1.1rem);line-height:1.7;animation:fade-up .8s .3s both}.auth-panel{margin-top:7vh;padding:2rem;border-radius:26px;background:linear-gradient(145deg,rgba(17,30,56,.86),rgba(8,15,29,.86));border:1px solid rgba(151,209,255,.18);box-shadow:0 30px 90px rgba(0,0,0,.33)}.auth-art{min-height:460px;padding:2.5rem;border-radius:26px;overflow:hidden;position:relative;background:radial-gradient(circle at 65% 42%,rgba(112,229,255,.25),transparent 18%),linear-gradient(135deg,#172b58,#0b1024 70%);border:1px solid rgba(153,203,255,.14)}.auth-art:after{content:"";position:absolute;width:260px;height:260px;border-radius:50%;border:1px solid rgba(117,234,255,.33);right:-70px;bottom:-70px;box-shadow:0 0 0 26px rgba(117,234,255,.045),0 0 0 52px rgba(117,234,255,.035)}.auth-brain{position:absolute;right:78px;bottom:78px;font-size:6rem;line-height:1;filter:drop-shadow(0 0 20px rgba(112,229,255,.72));animation:float 4s ease-in-out infinite}.status-line{display:flex;gap:9px;align-items:center;color:#97afc8;font-size:.8rem;margin-top:1.2rem}.status-dot{width:7px;height:7px;border-radius:50%;background:#79f3c1;box-shadow:0 0 12px #79f3c1}@keyframes pulse{50%{transform:scale(1.07)}}@keyframes orbit{to{transform:rotate(360deg)}}@keyframes float{50%{transform:translateY(-11px)}}@keyframes drift{50%{transform:translateY(-18px) scale(1.45);opacity:.45}}@keyframes glow-shift{50%{transform:scale(1.13);opacity:.55}}@keyframes wordmark-in{from{opacity:0;transform:translateY(22px);letter-spacing:-.03em}to{opacity:1;transform:translateY(0);letter-spacing:-.1em}}@keyframes fade-up{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:translateY(0)}}@media(max-width:760px){.block-container{padding:1.2rem .9rem 2rem}.boot-wrap{min-height:calc(100dvh - 7rem);padding:1rem .2rem}.boot-stage{padding:2rem 0}.boot-brain{width:128px;height:128px;font-size:5.6rem;margin-bottom:2rem}.boot-title{font-size:clamp(3.3rem,17vw,5.2rem)}.boot-title span{letter-spacing:.34em;margin-left:.34em}.dot-one{left:4%}.dot-two{right:4%}.auth-art{min-height:270px}}
    </style>""", unsafe_allow_html=True)


def init_state():
    for key, value in {"boot_complete": False, "authenticated": False, "current_view": "Workspace", "chat_history": []}.items():
        if key not in st.session_state: st.session_state[key] = value
    if "files_ingested" not in st.session_state:
        # Never query Chroma on first paint. A large/locked vector index can
        # delay the entire splash screen before the user sees anything.
        st.session_state.files_ingested = sorted(
            item for item in os.listdir(UPLOAD_DIR)
            if os.path.isfile(os.path.join(UPLOAD_DIR, item))
        )


def brand_lockup():
    st.markdown("<div class='brand-lockup'><div class='brand-mark'></div><div><div class='brand-name'>SECOND BRAIN</div><div class='eyebrow'>Document intelligence</div></div></div>", unsafe_allow_html=True)


def page_heading(kicker, title, subtitle):
    st.markdown(f"<div class='page-kicker'>{escape(kicker)}</div><h1 class='page-title'>{escape(title)}</h1><div class='page-subtitle'>{escape(subtitle)}</div>", unsafe_allow_html=True)


def render_pdf_page(file_path, page_number, caption):
    """Render one PDF page with PyMuPDF; this needs no optional Streamlit plugin."""
    import fitz
    document = fitz.open(file_path)
    try:
        pixmap = document[page_number].get_pixmap(matrix=fitz.Matrix(1.35, 1.35), alpha=False)
        st.image(pixmap.tobytes("png"), caption=caption, use_container_width=True)
    finally:
        document.close()


def render_pdf_document(file_path):
    """Provide a lightweight, page-by-page PDF viewer."""
    try:
        import fitz
        document = fitz.open(file_path)
        page_count = len(document)
        document.close()
        if not page_count:
            st.warning("This PDF has no pages to display.")
            return
        page = st.number_input(
            "Page", min_value=1, max_value=page_count, value=1, step=1,
            key=f"pdf_viewer_page_{os.path.basename(file_path)}",
        )
        render_pdf_page(file_path, int(page) - 1, f"Page {page} of {page_count}")
        with open(file_path, "rb") as pdf_file:
            st.download_button("Download PDF", pdf_file.read(), file_name=os.path.basename(file_path), mime="application/pdf", key=f"download_{os.path.basename(file_path)}")
    except Exception as error:
        st.error(f"Could not display this PDF: {error}")


def render_searched_pages(source_details, key):
    """Show only the document pages the model cited for its answer."""
    source_details = [detail for detail in source_details if detail.get("evidence")]
    if not source_details:
        return
    with st.expander(f"PDF pages used for this answer ({len(source_details)})", expanded=False):
        st.caption("Each shown page includes a verified quote that was used as evidence for this response.")
        pdf_pages = [detail for detail in source_details if detail.get("source", "").lower().endswith(".pdf") and isinstance(detail.get("page"), int) and os.path.exists(detail.get("source", ""))]
        if not pdf_pages:
            for detail in source_details:
                st.write(f"• {detail.get('label', 'Document page')}")
            return
        st.caption("Click one page to open only that page.")
        selected_key = f"{key}_selected_page"
        button_columns = st.columns(min(3, len(pdf_pages)))
        for index, detail in enumerate(pdf_pages):
            page_identifier = f"{detail['source']}::{detail['page']}"
            with button_columns[index % len(button_columns)]:
                if st.button(detail["label"], key=f"{key}_open_{index}", use_container_width=True):
                    st.session_state[selected_key] = page_identifier
        selected_identifier = st.session_state.get(selected_key)
        selected = next((detail for detail in pdf_pages if f"{detail['source']}::{detail['page']}" == selected_identifier), None)
        if selected:
            try:
                for quote in selected.get("evidence", []):
                    st.caption("Verified evidence from this page")
                    st.code(quote, language=None)
                render_pdf_page(selected["source"], selected["page"], selected["label"])
            except Exception as error:
                st.warning(f"{selected['label']} could not be previewed: {error}")


def render_boot():
    if st.query_params.get("enter") == "1":
        st.session_state.boot_complete = True
        st.query_params.clear()
        st.rerun()

    # Isolated component prevents Streamlit's own heading/button CSS from
    # interfering with the splash animation.
    components.html("""
    <!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
    <style>
    *{box-sizing:border-box}body{margin:0;background:#070d1c;color:#f6fbff;font-family:Arial,sans-serif;overflow:hidden}.stage{min-height:670px;padding:40px 24px;display:grid;place-items:center;text-align:center;position:relative;isolation:isolate;background:radial-gradient(circle at 50% 42%,#1d3d7c 0%,#111f42 31%,#070d1c 72%)}.stage:before{content:"";position:absolute;inset:0;opacity:.38;background-image:linear-gradient(rgba(149,220,255,.1) 1px,transparent 1px),linear-gradient(90deg,rgba(149,220,255,.1) 1px,transparent 1px);background-size:48px 48px;mask-image:radial-gradient(circle,black,transparent 70%);z-index:-1}.halo{width:178px;height:178px;display:grid;place-items:center;margin:0 auto 27px;position:relative;font-size:116px;line-height:1;filter:drop-shadow(0 0 25px rgba(104,231,255,.8));animation:pulse 3s ease-in-out infinite}.halo:before,.halo:after{content:"";position:absolute;border:1px solid rgba(139,238,255,.7);border-radius:50%;inset:-8px;animation:spin 6s linear infinite}.halo:after{inset:-33px;border-color:rgba(188,150,255,.45);animation-direction:reverse;animation-duration:9s}.dot{width:7px;height:7px;background:#a0f2ff;box-shadow:0 0 18px #70e5ff;border-radius:50%;position:absolute;animation:drift 4s ease-in-out infinite}.d1{top:21%;left:13%}.d2{top:28%;right:14%;animation-delay:-1.2s}.d3{bottom:22%;left:18%;animation-delay:-2.2s}.d4{bottom:26%;right:18%;animation-delay:-.6s}.kicker{font:700 11px monospace;letter-spacing:.22em;color:#8cecff;text-transform:uppercase}.title{margin:17px 0 0;font-size:clamp(52px,9vw,116px);line-height:.88;letter-spacing:-.09em;font-weight:900;text-shadow:0 0 42px rgba(125,230,255,.38);animation:rise .85s ease both}.tagline{margin:20px 0 28px;color:#c4d7ec;font-size:clamp(15px,2vw,18px);line-height:1.65;max-width:570px}.enter{display:inline-block;padding:15px 26px;border-radius:12px;text-decoration:none;color:#07111f;font-weight:800;background:linear-gradient(110deg,#77eaff,#a39cff);box-shadow:0 12px 33px rgba(101,189,255,.38);transition:.2s}.enter:hover{transform:translateY(-3px) scale(1.02);box-shadow:0 17px 42px rgba(101,189,255,.54)}@keyframes pulse{50%{transform:scale(1.07)}}@keyframes spin{to{transform:rotate(360deg)}}@keyframes drift{50%{transform:translateY(-18px) scale(1.5);opacity:.4}}@keyframes rise{from{opacity:0;transform:translateY(25px)}to{opacity:1;transform:translateY(0)}}@media(max-width:600px){.stage{min-height:calc(100vh - 24px);padding:30px 18px}.halo{width:134px;height:134px;font-size:88px;margin-bottom:24px}.title{font-size:clamp(50px,17vw,78px)}.d1{left:5%}.d2{right:5%}}
    </style></head><body><main class="stage"><i class="dot d1"></i><i class="dot d2"></i><i class="dot d3"></i><i class="dot d4"></i><section><div class="halo">🧠</div><div class="kicker">Your private knowledge layer</div><h1 class="title">SECOND BRAIN</h1><p class="tagline">Think deeper. Remember everything.<br>The AI-powered document and note assistant.</p></section></main></body></html>
    """, height=620, scrolling=False)
    _, entry_column, _ = st.columns([1.2, 1, 1.2])
    with entry_column:
        if st.button("Enter your workspace  →", type="primary", use_container_width=True, key="splash_entry"):
            st.session_state.boot_complete = True
            st.rerun()


def render_auth():
    left, right = st.columns([1.08, .92], gap="large")
    with left:
        st.markdown("""<div class='auth-art'><div class='eyebrow'>Your research, amplified</div><h1 style='max-width:420px;font-size:2.5rem;letter-spacing:-.07em;margin-top:1rem'>A calmer way to think with your documents.</h1><p style='max-width:390px;color:#a7bbd2;line-height:1.7'>Bring PDFs, notes and study material together. Ask naturally. Stay in control of your knowledge.</p><div class='auth-brain'>🧠</div></div>""", unsafe_allow_html=True)
    with right:
        st.markdown("<div class='auth-panel'>", unsafe_allow_html=True); brand_lockup()
        st.markdown("<h2 style='margin:0;letter-spacing:-.05em'>Welcome back</h2><p style='color:#95aac1;margin:7px 0 1.3rem'>Sign in to continue to your workspace.</p>", unsafe_allow_html=True)
        sign_in, register = st.tabs(["Sign in", "Create account"])
        with sign_in:
            username = st.text_input("Username", key="login_user", placeholder="Your identity")
            password = st.text_input("Password", key="login_pwd", type="password", placeholder="Your secure password")
            if st.button("Access workspace", type="primary", use_container_width=True):
                if auth.verify_user(username.strip(), password):
                    st.session_state.authenticated, st.session_state.current_user = True, username.strip(); st.rerun()
                st.error("That username or password does not match.")
        with register:
            new_username = st.text_input("Choose a username", key="register_user")
            new_password = st.text_input("Create a password", key="register_password", type="password")
            if st.button("Create secure workspace", type="primary", use_container_width=True):
                if len(new_username.strip()) < 3 or len(new_password) < 6: st.error("Use a username of 3+ characters and a password of 6+ characters.")
                elif auth.create_user(new_username.strip(), new_password): st.success("Account created. Sign in to enter your workspace.")
                else: st.error("That username is already in use.")
        st.markdown("<div class='status-line'><span class='status-dot'></span> Your source files stay on this device.</div></div>", unsafe_allow_html=True)


def render_sidebar():
    with st.sidebar:
        brand_lockup(); st.markdown("<div class='nav-caption'>Workspace</div>", unsafe_allow_html=True)
        for label, view in [("⌁  Ask your brain", "Workspace"), ("▣  Knowledge base", "Vault"), ("◌  System insights", "Insights")]:
            if st.button(label, key=f"nav_{view}", use_container_width=True): st.session_state.current_view = view; st.rerun()
        st.markdown("<div class='nav-caption'>Management</div>", unsafe_allow_html=True)
        if st.button("⚙  Workspace settings", key="nav_Core", use_container_width=True): st.session_state.current_view = "Core"; st.rerun()
        st.divider(); st.caption(f"SIGNED IN AS  ·  {st.session_state.current_user.upper()}")
        if st.button("Log out", use_container_width=True): st.session_state.authenticated = False; st.session_state.current_user = None; st.session_state.current_view = "Workspace"; st.rerun()


def render_workspace():
    page_heading("Your personal knowledge layer", "Ask your brain.", "Ground answers in the documents you trust, then follow your curiosity wherever it leads.")
    if not st.session_state.chat_history: st.markdown("<div class='glass-card empty-state'><div class='brain-visual'>🧠</div><h3 style='color:#f0f7ff;margin:0'>Your workspace is ready.</h3><p>Upload a document from Knowledge Base, then ask for a summary, explanation, comparison, or answer.</p></div>", unsafe_allow_html=True)
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"], avatar="🧠" if message["role"] == "assistant" else "👤"):
            st.markdown(message["content"])
            verified_details = [detail for detail in message.get("source_details", []) if detail.get("evidence")]
            if verified_details:
                st.markdown("".join(f"<span class='source-chip'>{escape(detail['label'])}</span>" for detail in verified_details), unsafe_allow_html=True)
                render_searched_pages(verified_details, key=f"history_{id(message)}")
    if prompt := st.chat_input("Ask anything about your knowledge base…"):
        # Load the AI pipeline only once the user actually sends a question.
        from rag_chain import ask_question
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar="👤"): st.markdown(prompt)
        with st.chat_message("assistant", avatar="🧠"):
            with st.spinner("Searching your knowledge and composing an answer…"): result = ask_question(prompt, chat_history=st.session_state.chat_history)
            st.markdown(result["answer"])
            if result.get("sources"): st.markdown("".join(f"<span class='source-chip'>{escape(source)}</span>" for source in result["sources"]), unsafe_allow_html=True)
            render_searched_pages(result.get("source_details", []), key=f"answer_{len(st.session_state.chat_history)}")
        st.session_state.chat_history.append({"role": "assistant", "content": result["answer"], "sources": result.get("sources", []), "source_details": result.get("source_details", [])})


def ingest_uploaded_files(uploaded_files, progress_area):
    # Import PDF/OCR/Chroma dependencies only on the upload screen.
    from ingest import ingest_file
    outcomes = []
    for uploaded_file in uploaded_files:
        safe_name = os.path.basename(uploaded_file.name)
        if safe_name in st.session_state.files_ingested: outcomes.append(("skipped", safe_name, "Already indexed")); continue
        file_path = os.path.join(UPLOAD_DIR, safe_name)
        try:
            with open(file_path, "wb") as destination: destination.write(uploaded_file.getbuffer())
            progress_bar = progress_area.progress(0, text=f"Preparing {safe_name}…")
            def on_progress(stage, percentage): progress_bar.progress(min(max(int(percentage), 0), 100), text=f"{safe_name} · {stage}")
            chunk_count = ingest_file(file_path, progress_callback=on_progress)
            progress_bar.progress(100, text=f"{safe_name} · indexed successfully")
            st.session_state.files_ingested.append(safe_name); outcomes.append(("success", safe_name, f"{chunk_count} knowledge chunks indexed"))
        except Exception as error:
            if os.path.exists(file_path): os.remove(file_path)
            outcomes.append(("error", safe_name, str(error)))
    st.session_state.files_ingested.sort(); return outcomes


def render_vault():
    from ingest import remove_file_from_index
    from utils import get_file_size_mb
    page_heading("Knowledge base", "Build your trusted context.", "Upload a PDF, DOCX or TXT file. We extract, segment and index it locally so your next question has real context.")
    upload_col, files_col = st.columns([.9, 1.35], gap="large")
    with upload_col:
        st.markdown("<div class='glass-card'><div class='eyebrow'>Add knowledge</div><h3 style='margin:.55rem 0 .3rem'>Drop files into your vault</h3><p style='color:#9badc4;font-size:.88rem;line-height:1.6'>Each file is processed once. Large or scanned PDFs may take longer because pages need OCR.</p>", unsafe_allow_html=True)
        uploaded = st.file_uploader("Choose files", type=["pdf", "docx", "txt"], accept_multiple_files=True, label_visibility="collapsed"); progress_area = st.empty()
        if uploaded:
            for state, name, detail in ingest_uploaded_files(uploaded, progress_area):
                if state == "success": st.success(f"{name} — {detail}")
                elif state == "error": st.error(f"{name} could not be indexed: {detail}")
                else: st.info(f"{name} — {detail}")
        st.markdown("<p style='color:#7890aa;font-size:.75rem;margin:1.1rem 0 0'>Supported: PDF, DOCX and UTF-8 TXT · Your raw files remain on this device.</p></div>", unsafe_allow_html=True)
    with files_col:
        st.markdown("<div class='glass-card'><div class='eyebrow'>Indexed documents</div><h3 style='margin:.55rem 0 1rem'>Your vault</h3>", unsafe_allow_html=True)
        if not st.session_state.files_ingested: st.markdown("<div class='empty-state' style='padding:2.2rem 1rem'><div class='brain-visual' style='font-size:3.3rem'>🧠</div><p style='margin:0'>No indexed documents yet.</p></div>", unsafe_allow_html=True)
        for name in list(st.session_state.files_ingested):
            path = os.path.join(UPLOAD_DIR, name); size = f"{get_file_size_mb(path):.2f} MB" if os.path.exists(path) else "File unavailable"
            row, view_action, action = st.columns([4.2, 1, 1])
            with row: st.markdown(f"<div class='file-row'><div class='file-name'>◫ &nbsp;{escape(name)}</div><div class='file-meta'>{size} · Ready for search</div></div>", unsafe_allow_html=True)
            with view_action:
                if name.lower().endswith(".pdf") and st.button("View", key=f"view_{name}", help=f"Open {name} in the app"):
                    st.session_state.open_pdf = None if st.session_state.get("open_pdf") == name else name
            with action:
                if st.button("Remove", key=f"remove_{name}", help=f"Remove {name} and its indexed chunks"):
                    try:
                        remove_file_from_index(path)
                        if os.path.exists(path): os.remove(path)
                        st.session_state.files_ingested.remove(name); st.toast(f"Removed {name} from the vault"); st.rerun()
                    except Exception as error: st.error(f"Could not remove {name}: {error}")
            if st.session_state.get("open_pdf") == name and os.path.exists(path):
                st.markdown(f"<div style='height:.6rem'></div><div class='eyebrow'>Document viewer · {escape(name)}</div>", unsafe_allow_html=True)
                render_pdf_document(path)
        st.markdown("</div>", unsafe_allow_html=True)


def render_insights():
    from utils import get_kb_analytics
    stats = get_kb_analytics(); page_heading("System insights", "Your knowledge, at a glance.", "A quiet overview of the material currently available to your Second Brain.")
    labels = ["DOCUMENTS", "STORAGE", "SYSTEM", "INDEX"]; values = [str(stats["total_files"]), f"{stats['total_size_mb']} MB", stats["health"], f"{stats['integrity']}%"]; hints = ["Available to ask", "Local source files", "Knowledge service", "Index integrity"]
    for column, label, value, hint in zip(st.columns(4), labels, values, hints):
        with column: st.markdown(f"<div class='glass-card'><div class='metric-label'>{label}</div><div class='metric-value'>{value}</div><div class='metric-hint'>{hint}</div></div>", unsafe_allow_html=True)
    st.markdown("<div style='height:1rem'></div><div class='glass-card'><div class='eyebrow'>Privacy promise</div><h3 style='margin:.55rem 0'>Your document vault stays local.</h3><p style='color:#9badc4;margin:0;line-height:1.7'>Second Brain stores your uploaded files and vector index in this workspace. Only relevant context is sent when an AI answer is generated.</p></div>", unsafe_allow_html=True)


def render_settings():
    from utils import clear_uploads, reset_database
    page_heading("Workspace settings", "Stay in control.", "Manage your active conversation and, if needed, clear the local knowledge vault.")
    st.markdown("<div class='glass-card'><div class='eyebrow'>Conversation</div><h3 style='margin:.55rem 0'>Start a fresh chat</h3><p style='color:#9badc4'>Keep your documents, but remove the current conversation from this browser session.</p>", unsafe_allow_html=True)
    if st.button("Clear chat history"): st.session_state.chat_history = []; st.success("Chat history cleared.")
    st.markdown("</div><div style='height:1rem'></div><div class='glass-card' style='border-color:rgba(255,117,141,.3)'><div class='eyebrow' style='color:#ff9aab'>Danger zone</div><h3 style='margin:.55rem 0'>Reset the knowledge vault</h3><p style='color:#bca4ad'>This removes every uploaded document and its local vector index. This cannot be undone.</p>", unsafe_allow_html=True)
    confirm = st.checkbox("I understand this permanently removes my local vault.")
    if st.button("Reset all local knowledge", disabled=not confirm):
        reset_database(); clear_uploads(); st.session_state.files_ingested, st.session_state.chat_history = [], []; st.success("Local knowledge vault reset."); st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


inject_styles(); init_state()
if not st.session_state.boot_complete: render_boot()
elif not st.session_state.authenticated: render_auth()
else:
    render_sidebar()
    {"Workspace": render_workspace, "Vault": render_vault, "Insights": render_insights, "Core": render_settings}[st.session_state.current_view]()
