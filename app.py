import os
import json
from datetime import date, datetime, timedelta
from html import escape

import streamlit as st
import streamlit.components.v1 as components

import auth
import db_manager
import competencies
from competencies import (
    COMPETENCY_DOMAINS,
    DOMAIN_STATISTICAL,
    DOMAIN_TECHNICAL,
    DOMAIN_DIGITAL_GOV,
    DOMAIN_BEHAVIOURAL,
    get_all_competencies,
    get_skills_by_domain,
    get_competency_meta,
    map_text_to_competencies,
)
from igot_service import igot_service
from utils import (
    clear_uploads,
    get_available_documents,
    get_file_size_mb,
    get_kb_analytics,
    reset_database,
)

st.set_page_config(
    page_title="Second Brain | AI Skill Intelligence & Personalized Learning Platform (SIH26101)",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


def inject_styles():
    st.markdown("""<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Manrope:wght@400;500;600;700;800&display=swap');
    :root {
        --ink: #eaf5ff;
        --muted: #94a8bd;
        --line: rgba(175,217,255,.14);
        --cyan: #70e5ff;
        --purple: #a78bfa;
        --gold: #f6ad55;
        --green: #79f3c1;
        --red: #ff8787;
        --accent-glow: rgba(112, 229, 255, 0.25);
    }
    .stApp { background: #060b16; color: var(--ink); font-family: Manrope, sans-serif; }
    .stApp::before, .stApp::after { display: none; }
    #MainMenu, footer, header { visibility: hidden; }
    .block-container { max-width: 1260px; padding-top: 1.8rem; padding-bottom: 3.5rem; }
    [data-testid="stSidebar"] { background: rgba(5,11,23,.95)!important; border-right: 1px solid var(--line); }
    [data-testid="stSidebar"] > div:first-child { padding-top: 1.2rem; }

    /* Button styles */
    .stButton > button {
        border-radius: 12px!important;
        font-family: Manrope, sans-serif!important;
        font-weight: 700!important;
        min-height: 40px;
        border: 1px solid rgba(150,200,255,.18)!important;
        background: rgba(255,255,255,.035)!important;
        color: #dcecff!important;
        transition: .2s ease!important;
    }
    .stButton > button:hover {
        transform: translateY(-1px);
        border-color: rgba(112,229,255,.68)!important;
        color: white!important;
        background: rgba(112,229,255,.12)!important;
        box-shadow: 0 8px 24px rgba(0,0,0,.25);
    }
    .stButton > button[kind="primary"] {
        background: linear-gradient(110deg,#75e8ff,#9194ff)!important;
        border: 0!important;
        color: #07101e!important;
        box-shadow: 0 8px 22px rgba(102,178,255,.28)!important;
    }

    /* Inputs */
    .stTextInput input, .stTextArea textarea, .stSelectbox select {
        border-radius: 11px!important;
        background: rgba(255,255,255,.045)!important;
        border: 1px solid var(--line)!important;
        color: white!important;
    }
    .stTextInput label, .stTextArea label, .stSelectbox label, .stFileUploader label, .stRadio label {
        color: #b8c8dc!important;
        font-weight: 600!important;
    }
    [data-testid="stFileUploaderDropzone"] {
        border: 1px dashed rgba(112,229,255,.45)!important;
        border-radius: 16px!important;
        background: rgba(89,144,255,.045)!important;
        padding: 1.1rem!important;
    }
    [data-testid="stChatMessage"] {
        border: 1px solid var(--line);
        background: rgba(12,22,40,.65);
        border-radius: 18px;
    }

    /* Typography & brand */
    .brand-lockup { display: flex; align-items: center; gap: 11px; padding: 0 0 1.2rem; }
    .brand-mark {
        width: 34px; height: 34px; border-radius: 11px; position: relative;
        background: conic-gradient(from 180deg,#70e5ff,#7a72ff,#d298ff,#70e5ff);
        box-shadow: 0 0 22px rgba(112,229,255,.32);
    }
    .brand-mark:after { content: ""; position: absolute; inset: 7px; border-radius: 8px; background: #081323; }
    .brand-mark:before { content: "✦"; position: absolute; z-index: 1; inset: 5px; text-align: center; color: #dffbff; font-size: 17px; }
    .eyebrow { color: #74e4ff; font: 600 .68rem 'DM Mono', monospace; letter-spacing: .16em; text-transform: uppercase; }
    .brand-name { color: white; font-size: .95rem; font-weight: 800; letter-spacing: .05em; }
    .nav-caption { color: #6d849d; font: 600 .68rem 'DM Mono', monospace; letter-spacing: .12em; margin: 1.1rem 0 .4rem; text-transform: uppercase; }

    .page-kicker { color: #77e5ff; font: 600 .74rem 'DM Mono', monospace; letter-spacing: .15em; text-transform: uppercase; }
    .page-title { font-size: clamp(1.8rem, 3.5vw, 2.45rem); letter-spacing: -.05em; margin: .3rem 0 .4rem; color: #f5f9ff; font-weight: 800; }
    .page-subtitle { color: var(--muted); max-width: 720px; line-height: 1.6; margin-bottom: 1.6rem; font-size: .95rem; }

    /* Glass card container */
    .glass-card {
        background: linear-gradient(145deg, rgba(21,34,59,.72), rgba(8,16,31,.72));
        border: 1px solid var(--line);
        border-radius: 20px;
        padding: 1.35rem;
        box-shadow: inset 0 1px rgba(255,255,255,.035), 0 16px 45px rgba(0,0,0,.18);
        margin-bottom: 1rem;
    }
    .metric-label { color: #9bb0c9; font: 600 .68rem 'DM Mono', monospace; letter-spacing: .12em; text-transform: uppercase; }
    .metric-value { font-size: 1.95rem; font-weight: 800; letter-spacing: -.06em; color: white; margin-top: .25rem; }
    .metric-hint { color: #70e5ff; font-size: .78rem; margin-top: .2rem; }

    /* Custom Badges */
    .badge-doc {
        display: inline-block; padding: 3px 9px; border-radius: 999px;
        background: rgba(112, 229, 255, 0.12); color: #70e5ff;
        border: 1px solid rgba(112, 229, 255, 0.28); font-size: .74rem; font-weight: 600;
    }
    .badge-memory {
        display: inline-block; padding: 3px 9px; border-radius: 999px;
        background: rgba(167, 139, 250, 0.14); color: #c4b5fd;
        border: 1px solid rgba(167, 139, 250, 0.32); font-size: .74rem; font-weight: 600;
    }
    .badge-igot {
        display: inline-block; padding: 3px 10px; border-radius: 999px;
        background: rgba(167, 139, 250, 0.2); color: #ddd6fe;
        border: 1px solid rgba(167, 139, 250, 0.45); font-size: .75rem; font-weight: 700;
    }
    .badge-gov {
        display: inline-block; padding: 3px 9px; border-radius: 999px;
        background: rgba(246, 173, 85, 0.18); color: #fbd38d;
        border: 1px solid rgba(246, 173, 85, 0.4); font-size: .75rem; font-weight: 700;
    }
    .badge-high-gap {
        display: inline-block; padding: 3px 9px; border-radius: 999px;
        background: rgba(255, 107, 107, 0.2); color: #ff8787;
        border: 1px solid rgba(255, 107, 107, 0.45); font-size: .75rem; font-weight: 700;
    }
    .badge-med-gap {
        display: inline-block; padding: 3px 9px; border-radius: 999px;
        background: rgba(246, 173, 85, 0.2); color: #fbd38d;
        border: 1px solid rgba(246, 173, 85, 0.45); font-size: .75rem; font-weight: 700;
    }
    .badge-ok {
        display: inline-block; padding: 3px 9px; border-radius: 999px;
        background: rgba(121, 243, 193, 0.16); color: #79f3c1;
        border: 1px solid rgba(121, 243, 193, 0.38); font-size: .75rem; font-weight: 700;
    }
    .badge-weak {
        display: inline-block; padding: 4px 10px; border-radius: 999px;
        background: rgba(255, 107, 107, 0.15); color: #ff8787;
        border: 1px solid rgba(255, 107, 107, 0.35); font-size: .76rem; font-weight: 600; margin: 3px 4px 3px 0;
    }

    .source-chip {
        display: inline-block; margin: 3px 6px 3px 0; padding: 3px 9px;
        color: #8deaff; background: rgba(112,229,255,.08);
        border: 1px solid rgba(112,229,255,.2); border-radius: 999px; font-size: .73rem;
    }
    .empty-state { text-align: center; padding: 2.8rem 1rem; color: #9cb0c6; }
    .brain-visual { margin: 0 auto .8rem; color: #b7f5ff; font-size: 3.8rem; filter: drop-shadow(0 0 16px rgba(112,229,255,.68)); }
    .file-row { padding: .75rem .1rem; border-bottom: 1px solid rgba(175,217,255,.1); }
    .file-name { color: #e8f4ff; font-weight: 700; font-size: .91rem; }
    .file-meta { color: #8298b1; font-size: .76rem; margin-top: 3px; }

    /* Quiz Card */
    .quiz-question-box {
        background: rgba(16, 28, 52, 0.6);
        border: 1px solid var(--line);
        border-radius: 16px;
        padding: 1.2rem;
        margin-bottom: 1.2rem;
    }
    .quiz-question-title {
        color: #f1f7ff;
        font-weight: 700;
        font-size: 1.05rem;
        margin-bottom: .8rem;
    }
    .score-banner {
        text-align: center;
        padding: 1.8rem;
        border-radius: 20px;
        background: linear-gradient(135deg, rgba(28,57,116,.7), rgba(15,28,56,.7));
        border: 1px solid rgba(112,229,255,.35);
        margin-bottom: 1.5rem;
    }
    </style>""", unsafe_allow_html=True)


def init_state():
    defaults = {
        "boot_complete": False,
        "authenticated": False,
        "current_user": None,
        "current_view": "Dashboard",
        "app_role": "Learner View",
        "chat_history": [],
        "active_quiz": [],
        "quiz_submitted": False,
        "quiz_score": 0,
        "user_answers": {},
        "quiz_weak_topics": [],
        "quiz_topic_prefill": "",
        "open_pdf": None,
        # SIH26101 state
        "diagnostic_quiz": [],
        "diagnostic_answers": {},
        "diagnostic_submitted": False,
        "diagnostic_results": {},
        "last_adaptive_update": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    if "files_ingested" not in st.session_state:
        st.session_state.files_ingested = get_available_documents()


def brand_lockup():
    st.markdown(
        "<div class='brand-lockup'><div class='brand-mark'></div>"
        "<div><div class='brand-name'>SECOND BRAIN</div>"
        "<div class='eyebrow'>Skill Intelligence · SIH26101</div></div></div>",
        unsafe_allow_html=True
    )


def page_heading(kicker, title, subtitle):
    st.markdown(
        f"<div class='page-kicker'>{escape(kicker)}</div>"
        f"<h1 class='page-title'>{escape(title)}</h1>"
        f"<div class='page-subtitle'>{escape(subtitle)}</div>",
        unsafe_allow_html=True
    )


def render_pdf_page(file_path, page_number, caption):
    """Render one PDF page with PyMuPDF."""
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
            st.download_button(
                "Download PDF", pdf_file.read(),
                file_name=os.path.basename(file_path),
                mime="application/pdf",
                key=f"download_{os.path.basename(file_path)}"
            )
    except Exception as error:
        st.error(f"Could not display this PDF: {error}")


def render_searched_pages(source_details, key):
    """Show document pages cited for an answer with expandable preview."""
    source_details = [d for d in source_details if d.get("source")]
    if not source_details:
        return
    with st.expander(f"📚 Sources & Citations ({len(source_details)})", expanded=False):
        pdf_pages = [
            d for d in source_details
            if d.get("source", "").lower().endswith(".pdf")
            and isinstance(d.get("page"), int)
            and os.path.exists(d.get("source", ""))
        ]
        if not pdf_pages:
            for detail in source_details:
                st.write(f"• {detail.get('label', 'Document excerpt')}")
            return

        st.caption("Click a source to inspect verified evidence and preview the original page:")
        selected_key = f"{key}_selected_page"
        cols = st.columns(min(3, len(pdf_pages)))
        for idx, detail in enumerate(pdf_pages):
            page_id = f"{detail['source']}::{detail['page']}"
            with cols[idx % len(cols)]:
                if st.button(detail["label"], key=f"{key}_btn_{idx}", use_container_width=True):
                    st.session_state[selected_key] = page_id

        selected_id = st.session_state.get(selected_key)
        selected = next((d for d in pdf_pages if f"{d['source']}::{d['page']}" == selected_id), None)
        if selected:
            for quote in selected.get("evidence", []):
                st.caption("Verbatim Quote Verified:")
                st.code(quote, language=None)
            try:
                render_pdf_page(selected["source"], selected["page"], selected["label"])
            except Exception as e:
                st.warning(f"Preview unavailable: {e}")


def render_boot():
    if st.query_params.get("enter") == "1":
        st.session_state.boot_complete = True
        st.query_params.clear()
        st.rerun()

    components.html("""
    <!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
    <style>
    *{box-sizing:border-box}body{margin:0;background:#070d1c;color:#f6fbff;font-family:Arial,sans-serif;overflow:hidden}.stage{min-height:640px;padding:40px 24px;display:grid;place-items:center;text-align:center;position:relative;isolation:isolate;background:radial-gradient(circle at 50% 42%,#1d3d7c 0%,#111f42 31%,#070d1c 72%)}.stage:before{content:"";position:absolute;inset:0;opacity:.38;background-image:linear-gradient(rgba(149,220,255,.1) 1px,transparent 1px),linear-gradient(90deg,rgba(149,220,255,.1) 1px,transparent 1px);background-size:48px 48px;mask-image:radial-gradient(circle,black,transparent 70%);z-index:-1}.halo{width:160px;height:160px;display:grid;place-items:center;margin:0 auto 24px;position:relative;font-size:105px;line-height:1;filter:drop-shadow(0 0 25px rgba(104,231,255,.8));animation:pulse 3s ease-in-out infinite}.halo:before,.halo:after{content:"";position:absolute;border:1px solid rgba(139,238,255,.7);border-radius:50%;inset:-8px;animation:spin 6s linear infinite}.halo:after{inset:-30px;border-color:rgba(188,150,255,.45);animation-direction:reverse;animation-duration:9s}.kicker{font:700 11px monospace;letter-spacing:.22em;color:#8cecff;text-transform:uppercase}.title{margin:15px 0 0;font-size:clamp(48px,8vw,108px);line-height:.9;letter-spacing:-.09em;font-weight:900;text-shadow:0 0 42px rgba(125,230,255,.38)}.tagline{margin:18px 0 28px;color:#c4d7ec;font-size:clamp(15px,2vw,18px);line-height:1.6;max-width:580px}@keyframes pulse{50%{transform:scale(1.07)}}@keyframes spin{to{transform:rotate(360deg)}}
    </style></head><body><main class="stage"><section><div class="halo">🧠</div><div class="kicker">Smart India Hackathon 2026 · Problem SIH26101</div><h1 class="title">SECOND BRAIN</h1><p class="tagline">AI-Powered Skill Intelligence &amp; Personalized Learning Platform<br>Capacity Building in India's Official Statistical System</p></section></main></body></html>
    """, height=560, scrolling=False)
    _, entry_col, _ = st.columns([1.2, 1, 1.2])
    with entry_col:
        if st.button("Enter your workspace  →", type="primary", use_container_width=True, key="splash_entry"):
            st.session_state.boot_complete = True
            st.rerun()


def render_auth():
    left, right = st.columns([1.08, .92], gap="large")
    with left:
        st.markdown(
            """<div class='glass-card' style='padding:2.5rem;min-height:430px;'>
            <div class='eyebrow'>Smart India Hackathon 2026 · SIH26101</div>
            <h1 style='font-size:2.2rem;letter-spacing:-.06em;margin-top:.8rem'>Capacity Building for India's Statistical Cadre.</h1>
            <p style='color:#a7bbd2;line-height:1.7'>AI-enabled platform identifying competency gaps, generating document-grounded MCQs, and recommending personalized learning through the iGOT Karmayogi ecosystem.</p>
            <div style='margin-top:1.5rem;'>
                <span class='badge-gov'>MoSPI Official Statistical System</span> &nbsp;
                <span class='badge-igot'>iGOT Karmayogi API-Ready</span>
            </div>
            <div style='font-size:5rem;margin-top:1.5rem'>🧠</div>
            </div>""",
            unsafe_allow_html=True
        )
    with right:
        st.markdown("<div class='glass-card' style='padding:2rem;'>", unsafe_allow_html=True)
        brand_lockup()
        st.markdown("<h2 style='margin:0;letter-spacing:-.05em'>Officer Sign In</h2><p style='color:#95aac1;margin:6px 0 1.2rem'>Access your competency workspace</p>", unsafe_allow_html=True)
        sign_in, register = st.tabs(["Sign in", "Create account"])
        with sign_in:
            username = st.text_input("Username", key="login_user", placeholder="e.g. rahul_sharma or dhani")
            password = st.text_input("Password", key="login_pwd", type="password", placeholder="Your password")
            if st.button("Access Workspace", type="primary", use_container_width=True):
                if auth.verify_user(username.strip(), password):
                    st.session_state.authenticated = True
                    st.session_state.current_user = username.strip()
                    st.session_state.current_view = "Dashboard"
                    # Initialize profile & competencies
                    db_manager.get_or_create_learner_profile(username.strip())
                    st.rerun()
                st.error("Invalid username or password.")
        with register:
            new_username = st.text_input("Choose a username", key="register_user")
            new_password = st.text_input("Create a password", key="register_password", type="password")
            if st.button("Create Account", type="primary", use_container_width=True):
                if len(new_username.strip()) < 3 or len(new_password) < 6:
                    st.error("Username must be 3+ characters and password 6+ characters.")
                elif auth.create_user(new_username.strip(), new_password):
                    db_manager.get_or_create_learner_profile(new_username.strip())
                    st.success("Account created successfully! Please sign in.")
                else:
                    st.error("That username already exists.")
        st.markdown("<div style='color:#8ca5be;font-size:.8rem;margin-top:1.2rem'>🔒 Private &amp; Offline Document Intelligence Layer</div></div>", unsafe_allow_html=True)


def render_sidebar():
    with st.sidebar:
        brand_lockup()

        # SIH26101 Role Switcher
        st.markdown("<div class='nav-caption'>Platform View Perspective</div>", unsafe_allow_html=True)
        role = st.selectbox(
            "Select Perspective:",
            ["Learner View", "Trainer / Content Creator", "Admin & Ministry Analytics"],
            key="app_role_select",
            label_visibility="collapsed"
        )
        st.session_state.app_role = role

        if role == "Learner View":
            st.markdown("<div class='nav-caption'>Skill Intelligence (SIH26101)</div>", unsafe_allow_html=True)
            learner_views = [
                ("🏠  Learner Dashboard", "Dashboard"),
                ("👤  Competency Profile", "Profile"),
                ("📝  Diagnostic Assessment", "Diagnostic"),
                ("🎯  Skill-Gap Analysis", "SkillGaps"),
                ("🚀  Learning Path (iGOT)", "LearningPath"),
                ("🧪  AI Practice Quizzes", "QuizMode"),
            ]
            for label, v in learner_views:
                if st.button(label, key=f"nav_l_{v}", use_container_width=True):
                    st.session_state.current_view = v
                    st.rerun()

            st.markdown("<div class='nav-caption'>Document Intelligence</div>", unsafe_allow_html=True)
            doc_views = [
                ("💬  Ask Second Brain", "Ask"),
                ("📍  Where Did I Learn This?", "WhereLearned"),
                ("🎓  Teach Me Mode", "TeachMe"),
                ("🎯  Exam Mode", "ExamMode"),
                ("📝  Smart Notes", "SmartNotes"),
                ("⚖  Compare Documents", "Compare"),
                ("🧠  My Memory", "Memory"),
                ("🗺  Knowledge Map", "KnowledgeMap"),
                ("📅  Study Planner", "StudyPlanner"),
            ]
            for label, v in doc_views:
                if st.button(label, key=f"nav_d_{v}", use_container_width=True):
                    st.session_state.current_view = v
                    st.rerun()

        elif role == "Trainer / Content Creator":
            st.markdown("<div class='nav-caption'>Trainer &amp; Curriculum Studio</div>", unsafe_allow_html=True)
            trainer_views = [
                ("📚  Training Materials (Vault)", "Vault"),
                ("🔍  Topic & Competency Extractor", "DocCompetencies"),
                ("❓  AI Assessment Generator", "QuestionGen"),
                ("📊  Learner Cohort Analytics", "Admin"),
            ]
            for label, v in trainer_views:
                if st.button(label, key=f"nav_t_{v}", use_container_width=True):
                    st.session_state.current_view = v
                    st.rerun()

        else:  # Admin & Ministry Analytics
            st.markdown("<div class='nav-caption'>Ministry &amp; System Analytics</div>", unsafe_allow_html=True)
            admin_views = [
                ("📈  Institutional Analytics", "Admin"),
                ("🏛  Competency Framework", "Framework"),
                ("🔗  iGOT Karmayogi Connector", "LearningPath"),
            ]
            for label, v in admin_views:
                if st.button(label, key=f"nav_a_{v}", use_container_width=True):
                    st.session_state.current_view = v
                    st.rerun()

        st.markdown("<div class='nav-caption'>Vault &amp; Management</div>", unsafe_allow_html=True)
        if st.button("📚  My Documents (Vault)", key="nav_vault_btn", use_container_width=True):
            st.session_state.current_view = "Vault"
            st.rerun()
        if st.button("⚙  Workspace Settings", key="nav_Settings", use_container_width=True):
            st.session_state.current_view = "Settings"
            st.rerun()

        st.divider()
        user = st.session_state.current_user or "Officer"
        st.caption(f"LOGGED IN AS  ·  {user.upper()}")
        if st.button("Log out", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.current_user = None
            st.session_state.current_view = "Dashboard"
            st.rerun()


# ==================== VIEW 1: LEARNER DASHBOARD (P0 / FEATURE 11 & 15) ====================

def render_dashboard():
    user = st.session_state.current_user
    profile = db_manager.get_or_create_learner_profile(user)
    comp_data = db_manager.get_learner_competencies(user)
    gaps = db_manager.get_skill_gaps(user)
    metrics = db_manager.get_dashboard_metrics(user)
    analytics = get_kb_analytics()

    page_heading(
        "Official Statistical System · Skill Intelligence (SIH26101)",
        f"Learner Dashboard: {profile['full_name']}",
        f"Designation: {profile['designation']} · {profile['department']} | Real-time competency tracking and personalized iGOT learning."
    )

    # Before -> After Adaptive Competency Update Banner (Step 12-13 of demo flow!)
    last_up = st.session_state.get("last_adaptive_update")
    if last_up:
        st.markdown(
            f"""<div class='glass-card' style='border-color:rgba(121,243,193,.6);background:linear-gradient(135deg,rgba(16,48,32,.7),rgba(10,24,20,.7));'>
            <div style='display:flex;justify-content:space-between;align-items:center;'>
                <span class='badge-ok'>🚀 Adaptive Competency Update Active</span>
                <span style='color:#79f3c1;font-size:.8rem;'>Adaptive Scoring Formula Applied</span>
            </div>
            <h3 style='margin:.4rem 0 .2rem;color:#79f3c1;'>Skill Demonstrated: {escape(last_up['skill'])}</h3>
            <p style='color:#e6fffa;font-size:1.15rem;margin:0;'>
                Competency Progression: <strong>{last_up['before_score']}%</strong> ➔ <strong style='color:#79f3c1;'>{last_up['after_score']}%</strong>
                <span style='color:#79f3c1;font-size:.9rem;'> (+{last_up['improvement']}% improvement verified)</span>
            </p>
            </div>""",
            unsafe_allow_html=True
        )

    # 4 Core Hero Metric Cards
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(
            f"<div class='glass-card'><div class='metric-label'>OVERALL COMPETENCY</div>"
            f"<div class='metric-value'>{comp_data['overall_score']}%</div>"
            f"<div class='metric-hint'>Systemic Readiness Index</div></div>",
            unsafe_allow_html=True
        )
    with c2:
        st.markdown(
            f"<div class='glass-card'><div class='metric-label'>HIGH PRIORITY GAPS</div>"
            f"<div class='metric-value' style='color:#ff8787;'>{len([g for g in gaps if g['priority'] == 'High Priority'])}</div>"
            f"<div class='metric-hint'>Critical training areas</div></div>",
            unsafe_allow_html=True
        )
    with c3:
        st.markdown(
            f"<div class='glass-card'><div class='metric-label'>QUIZZES COMPLETED</div>"
            f"<div class='metric-value'>{metrics['quizzes_completed']}</div>"
            f"<div class='metric-hint'>Avg Score: {metrics['avg_quiz_score']}%</div></div>",
            unsafe_allow_html=True
        )
    with c4:
        st.markdown(
            f"<div class='glass-card'><div class='metric-label'>CURRICULUM VAULT</div>"
            f"<div class='metric-value'>{analytics['total_files']}</div>"
            f"<div class='metric-hint'>{analytics['total_size_mb']} MB grounded notes</div></div>",
            unsafe_allow_html=True
        )

    # Domain Scores Breakdown
    st.markdown("<div class='glass-card'><div class='eyebrow'>4 Major Competency Domains (SIH26101)</div><h3 style='margin:.4rem 0 .8rem;'>Domain Proficiency Indices</h3>", unsafe_allow_html=True)
    d_cols = st.columns(4)
    domain_icons = {
        DOMAIN_STATISTICAL: "📊",
        DOMAIN_TECHNICAL: "💻",
        DOMAIN_DIGITAL_GOV: "🛡️",
        DOMAIN_BEHAVIOURAL: "🤝"
    }
    for idx, d_name in enumerate(COMPETENCY_DOMAINS):
        d_info = comp_data["domain_scores"].get(d_name, {"score": 50, "target": 70, "gap": 20})
        with d_cols[idx]:
            icon = domain_icons.get(d_name, "📌")
            score_color = "#79f3c1" if d_info["score"] >= d_info["target"] else ("#fbd38d" if d_info["gap"] < 25 else "#ff8787")
            st.markdown(
                f"<div style='background:rgba(255,255,255,0.03);padding:12px;border-radius:14px;border:1px solid rgba(175,217,255,.1);'>"
                f"<div style='font-size:.78rem;color:#8da5be;'>{icon} {d_name}</div>"
                f"<div style='font-size:1.6rem;font-weight:800;color:{score_color};margin:4px 0;'>{d_info['score']}%</div>"
                f"<div style='font-size:.72rem;color:#70e5ff;'>Target: {d_info['target']}% | Gap: {d_info['gap']}%</div>"
                f"</div>",
                unsafe_allow_html=True
            )
            st.progress(d_info["score"] / 100.0)
    st.markdown("</div>", unsafe_allow_html=True)

    col_left, col_right = st.columns([1.1, 0.9], gap="large")

    with col_left:
        # Top Skill Gaps Alert
        st.markdown("<div class='glass-card'><div class='eyebrow'>Skill-Gap Engine</div><h3 style='margin:.4rem 0 .8rem;'>Top Identified Skill Gaps</h3>", unsafe_allow_html=True)
        high_gaps = [g for g in gaps if g["priority"] in ["High Priority", "Medium Priority"]][:4]
        if high_gaps:
            for g in high_gaps:
                badge_class = "badge-high-gap" if g["priority"] == "High Priority" else "badge-med-gap"
                st.markdown(
                    f"""<div style='background:rgba(255,255,255,0.025);padding:10px 14px;border-radius:12px;margin-bottom:8px;border:1px solid rgba(175,217,255,.08);'>
                    <div style='display:flex;justify-content:space-between;align-items:center;'>
                        <strong style='color:#eaf5ff;'>{escape(g['skill'])}</strong>
                        <span class='{badge_class}'>{g['priority']} (Gap: {g['gap']}%)</span>
                    </div>
                    <div style='font-size:.82rem;color:#94a8bd;margin-top:4px;'>
                        Current: <strong style='color:#f87171;'>{g['current_score']}%</strong> | Benchmark Target: <strong>{g['target_score']}%</strong>
                    </div>
                    <div style='font-size:.78rem;color:#c0d2e5;margin-top:2px;'>{escape(g['reason'])}</div>
                    </div>""",
                    unsafe_allow_html=True
                )
            if st.button("Explore Full Skill Gap Analysis →", type="primary", use_container_width=True):
                st.session_state.current_view = "SkillGaps"
                st.rerun()
        else:
            st.success("All competencies are currently satisfactory! Take an assessment to benchmark new domains.")

        st.markdown("</div>", unsafe_allow_html=True)

    with col_right:
        # iGOT Karmayogi Recommended Path
        st.markdown(
            "<div class='glass-card'><div style='display:flex;justify-content:space-between;align-items:center;'>"
            "<div class='eyebrow'>Personalized Learning</div><span class='badge-igot'>iGOT Karmayogi API-Ready</span>"
            "</div><h3 style='margin:.4rem 0 .8rem;'>Recommended iGOT Courses</h3>",
            unsafe_allow_html=True
        )
        recs = igot_service.recommendCourses(gaps, limit=2)
        if recs:
            for r in recs:
                st.markdown(
                    f"""<div style='background:rgba(167,139,250,0.08);padding:10px 14px;border-radius:12px;margin-bottom:8px;border:1px solid rgba(167,139,250,0.25);'>
                    <div style='display:flex;justify-content:space-between;align-items:center;'>
                        <strong style='color:#f5f3ff;'>{escape(r['course_title'])}</strong>
                        <span class='badge-igot'>{escape(r['badge'])}</span>
                    </div>
                    <div style='font-size:.78rem;color:#c4b5fd;margin-top:3px;'>⏱ {r['duration_hours']} Hours · {r['level']} · {escape(r['provider'])}</div>
                    <div style='font-size:.78rem;color:#e2e8f0;margin-top:4px;'>{escape(r['reason'])}</div>
                    </div>""",
                    unsafe_allow_html=True
                )
            if st.button("Open Personalized Learning Path →", use_container_width=True):
                st.session_state.current_view = "LearningPath"
                st.rerun()

        # Quick Action Buttons
        st.markdown("<div style='height:.4rem;'></div>", unsafe_allow_html=True)
        q1, q2 = st.columns(2)
        with q1:
            if st.button("📝 Diagnostic Test", use_container_width=True):
                st.session_state.current_view = "Diagnostic"
                st.rerun()
        with q2:
            if st.button("🧪 AI Practice Quiz", use_container_width=True):
                st.session_state.current_view = "QuizMode"
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)


# ==================== VIEW 2: LEARNER COMPETENCY PROFILE (P0) ====================

def render_learner_profile():
    user = st.session_state.current_user
    profile = db_manager.get_or_create_learner_profile(user)
    comp_data = db_manager.get_learner_competencies(user)

    page_heading(
        "Learner Intelligence Profile (SIH26101)",
        f"Competency Profile: {profile['full_name']}",
        "Official Statistical Cadre background, competency scores, and role-based benchmark targets."
    )

    tab_profile, tab_matrix = st.tabs(["👤 Profile & Cadre Details", "📊 Competency Matrix & Benchmarks"])

    with tab_profile:
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        with st.form("profile_form"):
            c1, c2 = st.columns(2)
            with c1:
                name_val = st.text_input("Full Name:", value=profile["full_name"])
                desig_val = st.selectbox(
                    "Designation / Cadre Role:",
                    ["Statistical Analyst", "Junior Statistical Officer (JSO)", "Senior Statistical Officer (SSO)",
                     "Assistant Director (ISS)", "Deputy Director (ISS)", "Data Scientist / Statistical Programmer"],
                    index=0 if profile["designation"] not in ["Statistical Analyst", "Junior Statistical Officer (JSO)", "Senior Statistical Officer (SSO)", "Assistant Director (ISS)", "Deputy Director (ISS)", "Data Scientist / Statistical Programmer"]
                    else ["Statistical Analyst", "Junior Statistical Officer (JSO)", "Senior Statistical Officer (SSO)", "Assistant Director (ISS)", "Deputy Director (ISS)", "Data Scientist / Statistical Programmer"].index(profile["designation"])
                )
                dept_val = st.text_input("Department / Division:", value=profile["department"])
                role_val = st.text_input("Primary Job Responsibility:", value=profile["job_role"])
            with c2:
                qual_val = st.text_input("Educational Qualification:", value=profile["qualification"])
                exp_val = st.number_input("Experience in Official Statistics (Years):", min_value=0, max_value=40, value=int(profile["experience_years"]))
                train_val = st.text_area("Previous Inductions / Courses Completed:", value=profile["previous_training"], height=105)

            saved = st.form_submit_button("Save Profile Changes", type="primary")
            if saved:
                db_manager.update_learner_profile(user, name_val.strip(), desig_val, dept_val.strip(), role_val.strip(), qual_val.strip(), exp_val, train_val.strip())
                st.success("Learner profile updated successfully!")
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    with tab_matrix:
        st.markdown(
            f"<div class='glass-card'>"
            f"<div style='display:flex;justify-content:space-between;align-items:center;'>"
            f"<div><h3>Overall Competency Score: {comp_data['overall_score']}%</h3>"
            f"<p style='color:#94a8bd;font-size:.85rem;margin:0;'>Target Benchmark across all statistical cadres: 70%+</p></div>"
            f"<span class='badge-gov'>MoSPI Official Statistical Framework</span>"
            f"</div></div>",
            unsafe_allow_html=True
        )

        for d_name in COMPETENCY_DOMAINS:
            skills = [s for s in comp_data["skills"] if s["domain"] == d_name]
            if not skills:
                continue
            with st.expander(f"📁 {d_name} ({len(skills)} Skills)", expanded=True):
                for s in skills:
                    col_info, col_bar = st.columns([1.5, 2.5])
                    with col_info:
                        st.markdown(f"**{s['skill']}**")
                        badge_style = "badge-ok" if s["score"] >= s["target_score"] else ("badge-med-gap" if s["gap"] < 25 else "badge-high-gap")
                        st.markdown(f"<span class='{badge_style}'>Score: {s['score']}% / Target: {s['target_score']}%</span>", unsafe_allow_html=True)
                    with col_bar:
                        st.progress(s["score"] / 100.0, text=f"{s['score']}% (Benchmark: {s['target_score']}%)")
                        if s["previous_score"] is not None and s["previous_score"] != s["score"]:
                            st.caption(f"Historical progress: {s['previous_score']}% ➔ {s['score']}%")


# ==================== VIEW 3: DIAGNOSTIC COMPETENCY ASSESSMENT (P0) ====================

def render_diagnostic_assessment():
    from rag_chain import generate_competency_assessment
    user = st.session_state.current_user
    profile = db_manager.get_or_create_learner_profile(user)

    page_heading(
        "Competency Diagnostic Assessment",
        "Official Statistical Competency Assessment",
        "Diagnostic evaluation across statistical methodology, data processing, digital governance, and professional ethics."
    )

    if not st.session_state.diagnostic_quiz:
        st.markdown(
            "<div class='glass-card'>"
            "<div class='eyebrow'>Diagnostic Assessment Configuration</div>"
            "<h3 style='margin:.4rem 0;'>Benchmark Your Statistical Competencies</h3>"
            "<p style='color:#94a8bd;line-height:1.6;'>This assessment tests your knowledge against national standards. Your submission will immediately identify your high-priority skill gaps and generate your personalized learning recommendations.</p>",
            unsafe_allow_html=True
        )
        c1, c2 = st.columns([2, 1])
        with c1:
            scope = st.selectbox("Assessment Scope:", ["All 4 Domains (Comprehensive Diagnostic)"] + COMPETENCY_DOMAINS)
            domain_filter = None if scope.startswith("All 4") else scope
        with c2:
            q_count = st.select_slider("Assessment Length:", options=[4, 8, 12], value=8)

        if st.button("Begin Competency Assessment", type="primary"):
            with st.spinner("Preparing standardized official statistics assessment questions…"):
                questions = generate_competency_assessment(domain=domain_filter, count=q_count, learner_role=profile["designation"])

            if not questions:
                st.error("Could not load assessment questions. Please try again.")
                return

            st.session_state.diagnostic_quiz = questions
            st.session_state.diagnostic_submitted = False
            st.session_state.diagnostic_answers = {}
            st.session_state.diagnostic_results = {}
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    else:
        questions = st.session_state.diagnostic_quiz

        if not st.session_state.diagnostic_submitted:
            st.markdown(f"<div class='eyebrow'>Active Competency Assessment ({len(questions)} Questions)</div>", unsafe_allow_html=True)
            with st.form("diagnostic_form"):
                for idx, q in enumerate(questions):
                    st.markdown(
                        f"<div class='quiz-question-box'>"
                        f"<div style='display:flex;justify-content:space-between;margin-bottom:6px;'>"
                        f"<span class='badge-doc'>{escape(q.get('domain', 'Statistical Competency'))}</span>"
                        f"<span style='color:#8da5be;font-size:.76rem;'>Skill: {escape(q.get('skill', 'Core'))}</span>"
                        f"</div>"
                        f"<div class='quiz-question-title'>Q{idx+1}. {escape(q.get('question', ''))}</div>",
                        unsafe_allow_html=True
                    )
                    options = q.get("options", ["A", "B", "C", "D"])
                    ans = st.radio(
                        f"Answer for Q{idx+1}:",
                        options,
                        key=f"diag_q_{idx}",
                        index=None,
                        label_visibility="collapsed"
                    )
                    st.markdown("</div>", unsafe_allow_html=True)
                    st.session_state.diagnostic_answers[idx] = ans

                submitted = st.form_submit_button("Submit Assessment & Calculate Competency Scores", type="primary")
                if submitted:
                    total_correct = 0
                    domain_counts = {}
                    domain_correct = {}
                    skill_counts = {}
                    skill_correct = {}

                    for idx, q in enumerate(questions):
                        user_ans = st.session_state.diagnostic_answers.get(idx)
                        correct_idx = q.get("answer_index", 0)
                        correct_text = q.get("options", [])[correct_idx] if q.get("options") and correct_idx < len(q.get("options")) else ""
                        is_corr = (user_ans == correct_text)

                        if is_corr:
                            total_correct += 1

                        dom = q.get("domain", DOMAIN_STATISTICAL)
                        domain_counts[dom] = domain_counts.get(dom, 0) + 1
                        if is_corr:
                            domain_correct[dom] = domain_correct.get(dom, 0) + 1

                        sk = q.get("skill", "General Statistics")
                        skill_counts[sk] = skill_counts.get(sk, 0) + 1
                        if is_corr:
                            skill_correct[sk] = skill_correct.get(sk, 0) + 1

                    overall_pct = round((total_correct / len(questions)) * 100)
                    domain_scores = {
                        d: round((domain_correct.get(d, 0) / count) * 100)
                        for d, count in domain_counts.items()
                    }
                    skill_scores = {
                        s: round((skill_correct.get(s, 0) / count) * 100)
                        for s, count in skill_counts.items()
                    }

                    # Persist assessment and adaptively update profile
                    db_manager.save_assessment_result(user, "Diagnostic Assessment", overall_pct, domain_scores, skill_scores)

                    st.session_state.diagnostic_submitted = True
                    st.session_state.diagnostic_results = {
                        "overall_score": overall_pct,
                        "domain_scores": domain_scores,
                        "skill_scores": skill_scores,
                        "total_correct": total_correct,
                        "total_questions": len(questions)
                    }
                    st.rerun()

        else:
            # Assessment Results Report
            res = st.session_state.diagnostic_results
            st.markdown(
                f"<div class='score-banner'>"
                f"<div class='eyebrow'>Diagnostic Assessment Completed</div>"
                f"<h1 style='font-size:3.2rem;margin:.4rem 0;color:#70e5ff;'>{res['overall_score']}%</h1>"
                f"<div style='font-size:1.05rem;color:#e8f4ff;'>Correct: <strong>{res['total_correct']} of {res['total_questions']}</strong> questions</div>"
                f"<div style='margin-top:6px;'><span class='badge-ok'>Learner Competency Profile Automatically Updated</span></div>"
                f"</div>",
                unsafe_allow_html=True
            )

            c_dom, c_sk = st.columns(2)
            with c_dom:
                st.markdown("<div class='glass-card'><h4>Domain-Wise Breakdown</h4>", unsafe_allow_html=True)
                for d, s in res["domain_scores"].items():
                    st.markdown(f"**{d}:** {s}%")
                    st.progress(s / 100.0)
                st.markdown("</div>", unsafe_allow_html=True)

            with c_sk:
                st.markdown("<div class='glass-card'><h4>Skill-Wise Performance</h4>", unsafe_allow_html=True)
                for sk, s in res["skill_scores"].items():
                    badge = "badge-ok" if s >= 70 else ("badge-med-gap" if s >= 50 else "badge-high-gap")
                    st.markdown(f"<div style='margin-bottom:6px;'>{escape(sk)}: <span class='{badge}'>{s}%</span></div>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)

            # Question Review
            st.markdown("### Answer Review & Official Explanations:")
            for idx, q in enumerate(questions):
                user_ans = st.session_state.diagnostic_answers.get(idx)
                correct_idx = q.get("answer_index", 0)
                options = q.get("options", [])
                correct_text = options[correct_idx] if correct_idx < len(options) else ""
                is_correct = (user_ans == correct_text)

                card_border = "rgba(121,243,193,.4)" if is_correct else "rgba(255,107,107,.4)"
                status_badge = "✅ Correct" if is_correct else "❌ Incorrect"
                st.markdown(
                    f"<div class='glass-card' style='border-color:{card_border};'>"
                    f"<div style='display:flex;justify-content:space-between;'>"
                    f"<strong>Q{idx+1}. {escape(q.get('question', ''))}</strong>"
                    f"<span>{status_badge}</span></div>"
                    f"<div style='margin-top:.7rem;font-size:.88rem;'>"
                    f"Your answer: <code style='color:{'#79f3c1' if is_correct else '#ff8787'}'>{escape(str(user_ans))}</code><br>"
                    f"Official answer: <code style='color:#79f3c1'>{escape(correct_text)}</code></div>"
                    f"<div style='margin-top:.7rem;color:#b2c7dc;font-size:.85rem;background:rgba(0,0,0,.25);padding:8px 12px;border-radius:10px;'>"
                    f"<strong>Official Rationale:</strong> {escape(q.get('explanation', ''))}<br>"
                    f"<span style='color:#70e5ff;font-size:.76rem;'>Reference: {escape(q.get('source', 'Official Statistical Guidelines'))}</span></div>"
                    f"</div>",
                    unsafe_allow_html=True
                )

            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                if st.button("🎯 Proceed to Skill-Gap Analysis & Learning Path →", type="primary", use_container_width=True):
                    st.session_state.current_view = "SkillGaps"
                    st.rerun()
            with col_btn2:
                if st.button("Retake Assessment", use_container_width=True):
                    st.session_state.diagnostic_quiz = []
                    st.session_state.diagnostic_submitted = False
                    st.rerun()


# ==================== VIEW 4: SKILL-GAP ANALYSIS (P0 / FEATURE 7) ====================

def render_skill_gaps():
    from rag_chain import generate_skill_gap_feedback
    user = st.session_state.current_user
    profile = db_manager.get_or_create_learner_profile(user)
    gaps = db_manager.get_skill_gaps(user)

    page_heading(
        "AI Skill-Gap Intelligence (SIH26101)",
        "Competency Gap Analysis",
        "Targeted gap analysis comparing current demonstrated proficiency against role-specific benchmarks."
    )

    high_gaps = [g for g in gaps if g["priority"] == "High Priority"]
    med_gaps = [g for g in gaps if g["priority"] == "Medium Priority"]
    sat_skills = [g for g in gaps if g["priority"] == "Satisfactory"]

    # Summary Cards
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(
            f"<div class='glass-card' style='border-color:rgba(255,107,107,.4);'><div class='metric-label'>HIGH PRIORITY GAPS</div>"
            f"<div class='metric-value' style='color:#ff8787;'>{len(high_gaps)}</div>"
            f"<div class='metric-hint'>Critical training required</div></div>",
            unsafe_allow_html=True
        )
    with c2:
        st.markdown(
            f"<div class='glass-card' style='border-color:rgba(246,173,85,.4);'><div class='metric-label'>MEDIUM PRIORITY GAPS</div>"
            f"<div class='metric-value' style='color:#fbd38d;'>{len(med_gaps)}</div>"
            f"<div class='metric-hint'>Refresher courses needed</div></div>",
            unsafe_allow_html=True
        )
    with c3:
        st.markdown(
            f"<div class='glass-card' style='border-color:rgba(121,243,193,.4);'><div class='metric-label'>SATISFACTORY SKILLS</div>"
            f"<div class='metric-value' style='color:#79f3c1;'>{len(sat_skills)}</div>"
            f"<div class='metric-hint'>Meeting benchmark targets</div></div>",
            unsafe_allow_html=True
        )

    tab_high, tab_med, tab_sat, tab_ai = st.tabs(["🚨 High Priority Gaps", "⚠️ Medium Priority Gaps", "✅ Satisfactory Skills", "🤖 AI Diagnostic Report"])

    with tab_high:
        if not high_gaps:
            st.success("No high-priority skill gaps identified!")
        for g in high_gaps:
            with st.container():
                st.markdown(
                    f"""<div class='glass-card' style='border-color:rgba(255,107,107,.4);'>
                    <div style='display:flex;justify-content:space-between;align-items:center;'>
                        <h4 style='color:#ff8787;margin:0;'>{escape(g['skill'])}</h4>
                        <span class='badge-high-gap'>Gap: {g['gap']}%</span>
                    </div>
                    <div style='font-size:.82rem;color:#8da5be;margin:4px 0 8px;'>Domain: {escape(g['domain'])}</div>
                    <div style='font-size:1.05rem;color:#f1f5f9;'>
                        Current Score: <strong style='color:#ff8787;'>{g['current_score']}%</strong> &nbsp;|&nbsp;
                        Target Benchmark: <strong>{g['target_score']}%</strong>
                    </div>
                    <p style='color:#cbd5e1;font-size:.88rem;margin:8px 0;'><strong>Why this is a gap:</strong> {escape(g['reason'])}</p>
                    </div>""",
                    unsafe_allow_html=True
                )
                b1, b2 = st.columns([1, 1])
                with b1:
                    if st.button(f"🚀 Find iGOT Courses for {g['skill']}", key=f"rec_{g['skill']}"):
                        st.session_state.current_view = "LearningPath"
                        st.rerun()
                with b2:
                    if st.button(f"🧪 Take Practice Quiz on {g['skill']}", key=f"quiz_{g['skill']}"):
                        st.session_state.quiz_topic_prefill = g['skill']
                        st.session_state.current_view = "QuizMode"
                        st.rerun()

    with tab_med:
        if not med_gaps:
            st.info("No medium-priority gaps.")
        for g in med_gaps:
            st.markdown(
                f"""<div class='glass-card' style='border-color:rgba(246,173,85,.35);'>
                <div style='display:flex;justify-content:space-between;'>
                    <h4 style='color:#fbd38d;margin:0;'>{escape(g['skill'])}</h4>
                    <span class='badge-med-gap'>Gap: {g['gap']}%</span>
                </div>
                <div style='font-size:.9rem;color:#e2e8f0;margin:6px 0;'>Current: {g['current_score']}% / Target: {g['target_score']}%</div>
                <div style='font-size:.82rem;color:#94a8bd;'>{escape(g['reason'])}</div>
                </div>""",
                unsafe_allow_html=True
            )

    with tab_sat:
        for g in sat_skills:
            st.markdown(
                f"""<div class='glass-card' style='border-color:rgba(121,243,193,.3);'>
                <div style='display:flex;justify-content:space-between;'>
                    <h4 style='color:#79f3c1;margin:0;'>{escape(g['skill'])}</h4>
                    <span class='badge-ok'>Score: {g['current_score']}% (Target: {g['target_score']}%)</span>
                </div>
                <div style='font-size:.82rem;color:#94a8bd;margin-top:4px;'>Proficient competency maintained.</div>
                </div>""",
                unsafe_allow_html=True
            )

    with tab_ai:
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        if st.button("Generate Official AI Pedagogical Diagnostic Report", type="primary"):
            with st.spinner("Compiling academic competency diagnostic report…"):
                feedback = generate_skill_gap_feedback(profile, gaps)
            st.markdown(feedback)
        else:
            st.caption("Click to generate an AI-synthesized competency audit report based on your profile and verified skill gaps.")
        st.markdown("</div>", unsafe_allow_html=True)


# ==================== VIEW 5: PERSONALIZED LEARNING PATH (P0 / FEATURE 8 & 17) ====================

def render_learning_path():
    user = st.session_state.current_user
    profile = db_manager.get_or_create_learner_profile(user)
    gaps = db_manager.get_skill_gaps(user)

    page_heading(
        "iGOT Karmayogi Ecosystem Integration (SIH26101)",
        "Personalized Learning Path",
        "AI-curated learning curriculum mapped to your identified competency gaps, integrated with the iGOT Karmayogi ecosystem."
    )

    # API-Ready Disclaimer
    st.markdown(
        "<div class='glass-card' style='border-color:rgba(167,139,250,.4);background:rgba(26,19,51,.5);'>"
        "<div style='display:flex;justify-content:space-between;align-items:center;'>"
        "<span class='badge-igot'>iGOT Karmayogi Integration · API-Ready Prototype</span>"
        "<span style='color:#c4b5fd;font-size:.78rem;'>MoSPI / NASA Training Connector</span>"
        "</div>"
        "<p style='color:#e2e8f0;font-size:.88rem;margin:8px 0 0;line-height:1.6;'>"
        "<strong>Architectural Note:</strong> Demonstrates automated skill-gap-to-curriculum mapping under problem statement SIH26101. "
        "In production, this connector interfaces with live Karmayogi Bharat REST endpoints using OAuth2 token authorization."
        "</p></div>",
        unsafe_allow_html=True
    )

    tab_recommended, tab_catalogue = st.tabs(["🎯 My Personalized iGOT Path", "🔍 Search iGOT Course Catalogue"])

    with tab_recommended:
        recs = igot_service.recommendCourses(gaps, limit=6)
        if not recs:
            st.info("No urgent gaps found! Explore the general course catalogue.")
        else:
            st.markdown(f"### Curated Courses for {profile['full_name']} ({profile['designation']}):")
            for idx, r in enumerate(recs):
                with st.container():
                    st.markdown(
                        f"""<div class='glass-card'>
                        <div style='display:flex;justify-content:space-between;align-items:center;'>
                            <span class='badge-doc'>{escape(r['domain'])}</span>
                            <span class='badge-igot'>{escape(r['badge'])}</span>
                        </div>
                        <h3 style='margin:.5rem 0 .2rem;color:#f5f3ff;'>{escape(r['course_title'])}</h3>
                        <div style='color:#c4b5fd;font-size:.82rem;'>🏛 {escape(r['provider'])} · ⏱ {r['duration_hours']} Hours · Level: {escape(r['level'])}</div>
                        <p style='color:#cbd5e1;font-size:.9rem;line-height:1.6;margin:.6rem 0;'>{escape(r['summary'])}</p>
                        <div style='background:rgba(255,255,255,0.03);padding:8px 12px;border-radius:10px;font-size:.82rem;color:#79f3c1;'>
                            <strong>Why Recommended:</strong> {escape(r['reason'])}
                        </div>
                        </div>""",
                        unsafe_allow_html=True
                    )
                    c_btn, _ = st.columns([1.5, 3])
                    with c_btn:
                        if st.button(f"Start Learning on iGOT (API Ready)", key=f"enroll_{r['course_id']}_{idx}", type="primary"):
                            st.success(f"Enrolled in '{r['course_title']}'! Course link dispatched via iGOT API connector.")

    with tab_catalogue:
        search_query = st.text_input("Search iGOT Course Catalogue:", placeholder="e.g. Sampling, Python, National Accounts, Cybersecurity...")
        domain_filter = st.selectbox("Filter Domain:", ["All Domains"] + COMPETENCY_DOMAINS)
        dom_arg = None if domain_filter == "All Domains" else domain_filter

        results = igot_service.searchCourses(search_query.strip())
        if dom_arg:
            results = [c for c in results if c["domain"] == dom_arg]

        st.markdown(f"**Found {len(results)} Courses:**")
        for c in results:
            st.markdown(
                f"""<div class='glass-card'>
                <div style='display:flex;justify-content:space-between;'>
                    <strong style='color:#f1f5f9;font-size:1.05rem;'>{escape(c['title'])}</strong>
                    <span class='badge-igot'>{c['duration_hours']} Hours</span>
                </div>
                <div style='color:#94a8bd;font-size:.8rem;margin:3px 0 6px;'>{escape(c['provider'])} · Level: {escape(c['level'])}</div>
                <div style='color:#cbd5e1;font-size:.86rem;'>{escape(c['summary'])}</div>
                <div style='font-size:.76rem;color:#70e5ff;margin-top:6px;'>Modules: {', '.join(escape(m) for m in c['modules'])}</div>
                </div>""",
                unsafe_allow_html=True
            )


# ==================== VIEW 6: DOCUMENT TOPIC & COMPETENCY EXTRACTOR (P0 / FEATURE 10 & 18) ====================

def render_document_competencies():
    from rag_chain import extract_document_competencies
    page_heading(
        "Curriculum & Document Intelligence (SIH26101)",
        "Document Topic & Competency Extractor",
        "Automated AI extraction of syllabus topics, competency domains, and statistical skills from uploaded learning materials."
    )

    docs = get_available_documents()
    if not docs:
        st.warning("No documents found in vault. Upload materials in My Documents first.")
        return

    c1, _ = st.columns([2, 1])
    with c1:
        selected_doc = st.selectbox("Select Learning Material Document:", docs)

    if st.button("Extract Topics & Map Competencies", type="primary"):
        with st.spinner(f"Analyzing '{selected_doc}' and extracting competency taxonomy…"):
            res = extract_document_competencies(selected_doc)

        st.markdown(f"<div class='glass-card' style='border-color:rgba(112,229,255,.4);'><div class='eyebrow'>Curriculum Extraction: {escape(selected_doc)}</div>", unsafe_allow_html=True)
        st.markdown(f"### 📄 {escape(selected_doc)}")
        st.markdown(f"<p style='color:#cbd5e1;font-size:.95rem;line-height:1.6;'>{escape(res.get('summary', ''))}</p>", unsafe_allow_html=True)

        st.markdown("#### 🎯 Mapped Competency Domains:")
        for dom in res.get("domains", []):
            st.markdown(f"<span class='badge-doc'>🏛 {escape(dom)}</span>", unsafe_allow_html=True)

        st.markdown("<div style='height:.6rem;'></div>", unsafe_allow_html=True)
        st.markdown("#### 🏷 Specific Competency Skills Identified:")
        for sk in res.get("skills", []):
            st.markdown(f"<span class='badge-ok'>✓ {escape(sk)}</span>", unsafe_allow_html=True)

        st.markdown("<div style='height:.6rem;'></div>", unsafe_allow_html=True)
        st.markdown("#### 📌 Key Curriculum Topics Detected:")
        for top in res.get("topics", []):
            st.markdown(f"• **{escape(top)}**")

        st.markdown("</div>", unsafe_allow_html=True)

        # Direct Action Button to generate Quiz
        if st.button("❓ Generate Grounded AI Quiz from this Document →", type="primary"):
            st.session_state.quiz_topic_prefill = res.get("topics", [""])[0]
            st.session_state.current_view = "QuizMode"
            st.rerun()


# ==================== VIEW 7: ADMIN & MINISTRY ANALYTICS DASHBOARD (P1 / FEATURE 16) ====================

def render_admin_dashboard():
    analytics = db_manager.get_admin_analytics()
    igot_status = igot_service.get_service_status()

    page_heading(
        "Ministry of Statistics & Programme Implementation (MoSPI)",
        "Institutional Capacity Building & Skill Analytics",
        "System-wide monitoring of learner competency profiles, nationwide skill gaps, and iGOT integration status."
    )

    # 4 Top Executive Metrics
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(
            f"<div class='glass-card'><div class='metric-label'>TOTAL REGISTERED LEARNERS</div>"
            f"<div class='metric-value'>{analytics['total_learners']}</div>"
            f"<div class='metric-hint'>Statistical Officers & Cadres</div></div>",
            unsafe_allow_html=True
        )
    with c2:
        st.markdown(
            f"<div class='glass-card'><div class='metric-label'>ACTIVE LEARNERS (30D)</div>"
            f"<div class='metric-value' style='color:#79f3c1;'>{analytics['active_learners']}</div>"
            f"<div class='metric-hint'>Engaged in learning platform</div></div>",
            unsafe_allow_html=True
        )
    with c3:
        st.markdown(
            f"<div class='glass-card'><div class='metric-label'>SYSTEM-WIDE COMPETENCY</div>"
            f"<div class='metric-value'>{analytics['avg_competency']}%</div>"
            f"<div class='metric-hint'>Nationwide Proficiency Index</div></div>",
            unsafe_allow_html=True
        )
    with c4:
        st.markdown(
            f"<div class='glass-card'><div class='metric-label'>TRAINING COMPLETION</div>"
            f"<div class='metric-value'>{analytics['training_completion_rate']}%</div>"
            f"<div class='metric-hint'>Official Modules Completed</div></div>",
            unsafe_allow_html=True
        )

    col_left, col_right = st.columns([1.1, 0.9], gap="large")

    with col_left:
        # Domain Competency Overview
        st.markdown("<div class='glass-card'><div class='eyebrow'>Cadre Proficiency</div><h3 style='margin:.4rem 0 .8rem;'>Domain Averages across National Cadre</h3>", unsafe_allow_html=True)
        for dom, avg in analytics["domain_averages"].items():
            st.markdown(f"**{dom}:** {avg}%")
            st.progress(avg / 100.0)
        st.markdown("</div>", unsafe_allow_html=True)

        # Top Institutional Skill Gaps
        st.markdown("<div class='glass-card'><div class='eyebrow'>Institutional Bottlenecks</div><h3 style='margin:.4rem 0 .8rem;'>Top Institutional Skill Gaps</h3>", unsafe_allow_html=True)
        for g in analytics["top_institutional_gaps"]:
            st.markdown(
                f"""<div style='background:rgba(255,255,255,0.025);padding:10px 14px;border-radius:10px;margin-bottom:6px;display:flex;justify-content:space-between;align-items:center;'>
                <div><strong>{escape(g['skill'])}</strong><div style='font-size:.78rem;color:#8da5be;'>Cadre Average: {g['avg_score']}%</div></div>
                <span class='badge-high-gap'>Average Gap: {g['gap']}%</span>
                </div>""",
                unsafe_allow_html=True
            )
        st.markdown("</div>", unsafe_allow_html=True)

    with col_right:
        # iGOT Connector Status Card
        st.markdown(
            f"""<div class='glass-card' style='border-color:rgba(167,139,250,.4);'>
            <div class='eyebrow'>iGOT Karmayogi Connector Health</div>
            <h3 style='margin:.4rem 0 .6rem;color:#c4b5fd;'>Ecosystem Integration</h3>
            <div style='font-size:.85rem;color:#e2e8f0;line-height:1.7;'>
                • <strong>Mode:</strong> {igot_status['mode']}<br>
                • <strong>Endpoint:</strong> <code style='font-size:.76rem;'>{igot_status['endpoint']}</code><br>
                • <strong>Catalogue Indexed:</strong> {igot_status['catalogue_count']} Capacity-Building Modules<br>
                • <strong>OAuth2 Layer:</strong> API-Ready Abstraction Layer Active<br>
                • <strong>Status:</strong> <span class='badge-ok'>CONNECTED &amp; ACTIVE</span>
            </div>
            <p style='color:#a78bfa;font-size:.76rem;margin-top:10px;'>{igot_status['disclaimer']}</p>
            </div>""",
            unsafe_allow_html=True
        )

        # Real-time Activity Stream
        st.markdown("<div class='glass-card'><div class='eyebrow'>Audit Trail</div><h3 style='margin:.4rem 0 .8rem;'>Recent Learning Activity</h3>", unsafe_allow_html=True)
        for act in analytics["activity_stream"]:
            st.markdown(
                f"<div style='font-size:.8rem;padding:4px 0;border-bottom:1px solid rgba(175,217,255,.07);'>"
                f"<span style='color:#70e5ff;'>{escape(act['username'])}</span>: {escape(act['detail'])} "
                f"<span style='color:#6d849d;font-size:.72rem;'>({escape(str(act['timestamp'])[:16])})</span>"
                f"</div>",
                unsafe_allow_html=True
            )
        st.markdown("</div>", unsafe_allow_html=True)


# ==================== VIEW 8: COMPETENCY FRAMEWORK TAXONOMY OVERVIEW ====================

def render_framework_overview():
    page_heading(
        "Official Statistical System Capacity Framework",
        "Competency Catalogue (SIH26101)",
        "Structured taxonomy of statistical, technical, digital governance, and managerial competencies for MoSPI civil service."
    )

    for d_name in COMPETENCY_DOMAINS:
        skills = get_skills_by_domain(d_name)
        with st.expander(f"🏛 {d_name} ({len(skills)} Competencies)", expanded=True):
            for sk in skills:
                meta = get_competency_meta(sk)
                st.markdown(
                    f"""<div style='background:rgba(255,255,255,0.02);padding:12px;border-radius:12px;margin-bottom:8px;border:1px solid rgba(175,217,255,.1);'>
                    <div style='display:flex;justify-content:space-between;'>
                        <strong style='color:#70e5ff;'>{escape(sk)}</strong>
                        <span class='badge-gov'>Standard Benchmark: {meta['default_target']}%</span>
                    </div>
                    <p style='color:#cbd5e1;font-size:.86rem;margin:6px 0;'>{escape(meta['description'])}</p>
                    <div style='font-size:.76rem;color:#8da5be;'><strong>Keywords:</strong> {', '.join(escape(k) for k in meta['keywords'])}</div>
                    </div>""",
                    unsafe_allow_html=True
                )


# ==================== VIEW 9: INTERACTIVE QUIZ MODE (P0 / FEATURE 6 & 13 & 14) ====================

def render_quiz_mode():
    from rag_chain import generate_quiz
    page_heading(
        "Grounded Assessment & Active Recall",
        "AI Quiz Assessment",
        "Generate document-grounded quizzes with source citations, instant feedback, and adaptive competency score updates."
    )

    docs = get_available_documents()
    prefill = st.session_state.get("quiz_topic_prefill", "")

    # Before -> After Adaptive Competency Update Banner
    last_up = st.session_state.get("last_adaptive_update")
    if last_up:
        st.markdown(
            f"""<div class='glass-card' style='border-color:rgba(121,243,193,.6);background:linear-gradient(135deg,rgba(16,48,32,.7),rgba(10,24,20,.7));'>
            <div class='eyebrow' style='color:#79f3c1;'>Adaptive Competency Update (SIH26101)</div>
            <h3 style='margin:.4rem 0 .2rem;color:#79f3c1;'>{escape(last_up['skill'])}</h3>
            <p style='color:#e6fffa;font-size:1.1rem;margin:0;'>
                Competency Progression: <strong>{last_up['before_score']}%</strong> ➔ <strong style='color:#79f3c1;'>{last_up['after_score']}%</strong>
                <span style='color:#79f3c1;font-size:.88rem;'> (+{last_up['improvement']}% improvement)</span>
            </p>
            </div>""",
            unsafe_allow_html=True
        )

    if prefill:
        st.info(f"🎯 Target Skill / Weak Area Selected: **{prefill}**")

    # Quiz Configuration
    if not st.session_state.active_quiz:
        c1, c2, c3 = st.columns([2, 1.2, 1])
        with c1:
            quiz_topic = st.text_input("Quiz Topic / Concept:", value=prefill, placeholder="e.g. Sampling, Cyber Crime, Credit Card Fraud, GDP")
        with c2:
            doc_choice = st.selectbox("Curriculum Document:", ["All Documents"] + docs)
            doc_filter = None if doc_choice == "All Documents" else doc_choice
        with c3:
            q_count = st.select_slider("Question Count:", options=[3, 5, 8, 10], value=5)

        c_dom, c_diff = st.columns(2)
        with c_dom:
            domain_choice = st.selectbox("Target Competency Domain:", ["Auto-Map Domain"] + COMPETENCY_DOMAINS)
            comp_domain = None if domain_choice == "Auto-Map Domain" else domain_choice
        with c_diff:
            diff_choice = st.selectbox("Difficulty Level:", ["Easy", "Medium", "Hard"], index=1)

        if st.button("Generate AI Assessment Quiz", type="primary"):
            with st.spinner("Generating document-grounded MCQs with source citations…"):
                quiz = generate_quiz(
                    quiz_topic.strip(),
                    count=q_count,
                    doc_filter=doc_filter,
                    competency_domain=comp_domain,
                    difficulty=diff_choice
                )

            if not quiz:
                st.error("Could not generate quiz. Please check document selection or specify a broader topic.")
                return

            st.session_state.active_quiz = quiz
            st.session_state.quiz_submitted = False
            st.session_state.quiz_score = 0
            st.session_state.user_answers = {}
            st.session_state.quiz_weak_topics = []
            st.session_state.quiz_topic_prefill = ""
            st.rerun()

    # Active Quiz Flow
    else:
        quiz = st.session_state.active_quiz
        st.markdown(f"<div class='eyebrow'>Interactive Quiz ({len(quiz)} Questions)</div>", unsafe_allow_html=True)

        if not st.session_state.quiz_submitted:
            with st.form("quiz_form"):
                for idx, q in enumerate(quiz):
                    st.markdown(
                        f"<div class='quiz-question-box'>"
                        f"<div style='display:flex;justify-content:space-between;margin-bottom:6px;'>"
                        f"<span class='badge-doc'>📄 {escape(q.get('source_doc', 'Vault'))} (Page {q.get('page', 1)})</span>"
                        f"<span style='color:#70e5ff;font-size:.76rem;'>{escape(q.get('domain', 'Statistical Competency'))}</span>"
                        f"</div>"
                        f"<div class='quiz-question-title'>Q{idx+1}. {escape(q.get('question', ''))}</div>",
                        unsafe_allow_html=True
                    )
                    options = q.get("options", ["A", "B", "C", "D"])
                    ans = st.radio(
                        f"Select answer for Q{idx+1}:",
                        options,
                        key=f"q_{idx}",
                        index=None,
                        label_visibility="collapsed"
                    )
                    st.markdown("</div>", unsafe_allow_html=True)
                    st.session_state.user_answers[idx] = ans

                submitted = st.form_submit_button("Submit Quiz & Update Competency Profile", type="primary")
                if submitted:
                    score = 0
                    weak_topics = []
                    for idx, q in enumerate(quiz):
                        user_ans = st.session_state.user_answers.get(idx)
                        correct_idx = q.get("answer_index", 0)
                        correct_text = q.get("options", [])[correct_idx] if q.get("options") and correct_idx < len(q.get("options")) else ""
                        if user_ans == correct_text:
                            score += 1
                        else:
                            t = q.get("topic", q.get("skill", "General"))
                            if t and t not in weak_topics:
                                weak_topics.append(t)

                    score_pct = round((score / len(quiz)) * 100)
                    st.session_state.quiz_submitted = True
                    st.session_state.quiz_score = score
                    st.session_state.quiz_weak_topics = weak_topics

                    # Save to database
                    user = st.session_state.current_user
                    topic_label = quiz[0].get("topic", "Quiz")
                    db_manager.save_quiz_result(user, topic_label, quiz[0].get("source_doc", "Vault"), score, len(quiz), weak_topics)

                    # SIH26101 Adaptive Competency Update!
                    matched = map_text_to_competencies(topic_label + " " + " ".join(q.get("topic", "") for q in quiz))
                    target_skill = matched[0]["skill"] if matched else "Descriptive & Inferential Statistics"
                    target_domain = matched[0]["domain"] if matched else DOMAIN_STATISTICAL

                    up_res = db_manager.update_skill_score_adaptive(user, target_skill, score_pct, domain=target_domain)
                    st.session_state.last_adaptive_update = up_res
                    st.rerun()

        # Results & Review Screen
        else:
            score = st.session_state.quiz_score
            total = len(quiz)
            percentage = round((score / total) * 100, 1)

            st.markdown(
                f"<div class='score-banner'>"
                f"<div class='eyebrow'>Quiz Completed</div>"
                f"<h1 style='font-size:3.2rem;margin:.4rem 0;color:#70e5ff;'>{score} / {total}</h1>"
                f"<div style='font-size:1.1rem;color:#e8f4ff;'>Demonstrated Accuracy: <strong>{percentage}%</strong></div>"
                f"</div>",
                unsafe_allow_html=True
            )

            # Adaptive progression banner on results screen
            if st.session_state.get("last_adaptive_update"):
                up = st.session_state.last_adaptive_update
                st.markdown(
                    f"""<div class='glass-card' style='border-color:rgba(121,243,193,.6);background:rgba(16,42,32,0.4);'>
                    <div style='display:flex;justify-content:space-between;align-items:center;'>
                        <span class='badge-ok'>Adaptive Competency Update (SIH26101)</span>
                        <span style='color:#79f3c1;font-size:.8rem;'>Formula: (Old × 0.60) + (Quiz × 0.40)</span>
                    </div>
                    <h3 style='margin:.4rem 0 .2rem;color:#79f3c1;'>Skill: {escape(up['skill'])}</h3>
                    <p style='color:#e6fffa;font-size:1.15rem;margin:0;'>
                        Profile Competency Adjusted: <strong>{up['before_score']}%</strong> ➔ <strong style='color:#79f3c1;'>{up['after_score']}%</strong>
                        <span style='color:#79f3c1;font-size:.9rem;'> (+{up['improvement']}% improvement verified)</span>
                    </p>
                    </div>""",
                    unsafe_allow_html=True
                )

            # Weak areas section
            weak = st.session_state.quiz_weak_topics
            if weak:
                st.markdown("<div class='glass-card'><div class='eyebrow'>Knowledge Gaps</div><h3 style='margin:.3rem 0 .7rem'>Weak Areas Detected:</h3>", unsafe_allow_html=True)
                chips = "".join(f"<span class='badge-weak'>⚠ {escape(w)}</span>" for w in weak)
                st.markdown(chips, unsafe_allow_html=True)
                st.markdown("<div style='height:.8rem'></div>", unsafe_allow_html=True)
                if st.button("🎯 Practice My Weak Areas Now", type="primary", use_container_width=True):
                    st.session_state.quiz_topic_prefill = ", ".join(weak)
                    st.session_state.active_quiz = []
                    st.session_state.quiz_submitted = False
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

            # Question by question review with grounded evidence
            st.markdown("### Answer Review & Grounded Evidence:")
            for idx, q in enumerate(quiz):
                user_ans = st.session_state.user_answers.get(idx)
                correct_idx = q.get("answer_index", 0)
                options = q.get("options", [])
                correct_text = options[correct_idx] if correct_idx < len(options) else ""
                is_correct = (user_ans == correct_text)

                card_border = "rgba(121,243,193,.4)" if is_correct else "rgba(255,107,107,.4)"
                status_badge = "✅ Correct" if is_correct else "❌ Incorrect"
                st.markdown(
                    f"<div class='glass-card' style='border-color:{card_border};'>"
                    f"<div style='display:flex;justify-content:space-between;'>"
                    f"<strong>Q{idx+1}. {escape(q.get('question', ''))}</strong>"
                    f"<span>{status_badge}</span></div>"
                    f"<div style='margin-top:.7rem;font-size:.88rem;'>"
                    f"Your answer: <code style='color:{'#79f3c1' if is_correct else '#ff8787'}'>{escape(str(user_ans))}</code><br>"
                    f"Correct answer: <code style='color:#79f3c1'>{escape(correct_text)}</code></div>"
                    f"<div style='margin-top:.7rem;color:#b2c7dc;font-size:.85rem;background:rgba(0,0,0,.25);padding:8px 12px;border-radius:10px;'>"
                    f"<strong>Explanation:</strong> {escape(q.get('explanation', ''))}<br>"
                    f"<span style='color:#70e5ff;font-size:.76rem;'>Source: 📄 {escape(q.get('source_doc', 'Document'))} (Page {q.get('page', 'N/A')})</span></div>"
                    f"</div>",
                    unsafe_allow_html=True
                )

            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("View Updated Dashboard →", type="primary", use_container_width=True):
                    st.session_state.current_view = "Dashboard"
                    st.rerun()
            with col_b:
                if st.button("Take Another Quiz", use_container_width=True):
                    st.session_state.active_quiz = []
                    st.session_state.quiz_submitted = False
                    st.rerun()


# ==================== VIEW 10: ASK SECOND BRAIN (FEATURE 1) ====================

def render_ask_brain():
    page_heading("Multi-Document RAG", "Ask Across Documents", "Query across all uploaded documents simultaneously. Verified citations and page previews are displayed automatically.")

    docs = get_available_documents()
    filter_col, info_col = st.columns([1, 1.2])
    with filter_col:
        doc_options = ["All Documents"] + docs
        selected_doc = st.selectbox("Search Scope:", doc_options, index=0)
        doc_filter = None if selected_doc == "All Documents" else selected_doc

    with info_col:
        st.markdown(
            f"<div style='margin-top:1.6rem;'><span class='badge-doc'>Scope: {selected_doc}</span> &nbsp;"
            f"<span style='color:#8ba3be;font-size:.84rem;'>{len(docs)} documents available in vault</span></div>",
            unsafe_allow_html=True
        )

    if not st.session_state.chat_history:
        st.markdown(
            "<div class='glass-card empty-state'><div class='brain-visual'>🧠</div>"
            "<h3 style='color:#f0f7ff;margin:0'>Ask anything about your documents</h3>"
            "<p>Example: 'What is the classification of cyber crime?' or 'Compare sampling techniques and census.'</p></div>",
            unsafe_allow_html=True
        )

    for message in st.session_state.chat_history:
        with st.chat_message(message["role"], avatar="🧠" if message["role"] == "assistant" else "👤"):
            st.markdown(message["content"])
            verified_details = [d for d in message.get("source_details", []) if d.get("evidence") or d.get("source")]
            if verified_details:
                st.markdown("".join(f"<span class='source-chip'>{escape(d['label'])}</span>" for d in verified_details), unsafe_allow_html=True)
                render_searched_pages(verified_details, key=f"history_{id(message)}")

    if prompt := st.chat_input("Ask anything across your knowledge base…"):
        from rag_chain import ask_question
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar="👤"):
            st.markdown(prompt)

        with st.chat_message("assistant", avatar="🧠"):
            with st.spinner("Searching documents and verifying citations…"):
                result = ask_question(
                    prompt,
                    chat_history=st.session_state.chat_history,
                    doc_filter=doc_filter,
                    username=st.session_state.current_user
                )
            st.markdown(result["answer"])
            if result.get("sources"):
                st.markdown("".join(f"<span class='source-chip'>{escape(s)}</span>" for s in result["sources"]), unsafe_allow_html=True)
            render_searched_pages(result.get("source_details", []), key=f"ans_{len(st.session_state.chat_history)}")

        st.session_state.chat_history.append({
            "role": "assistant",
            "content": result["answer"],
            "sources": result.get("sources", []),
            "source_details": result.get("source_details", [])
        })


# ==================== VIEW 11: WHERE DID I LEARN THIS? (FEATURE 2) ====================

def render_where_learned():
    from rag_chain import where_did_i_learn
    page_heading("Knowledge Origin Finder", "Where Did I Learn This?", "Search your notes, books, and lecture slides to find exact filenames, sections, and pages where a concept is taught.")

    docs = get_available_documents()
    c1, c2 = st.columns([2.2, 1])
    with c1:
        concept_query = st.text_input("Concept or Topic:", placeholder="e.g. Credit Card Fraud, Salami Attack, Stratified Sampling...")
    with c2:
        doc_choice = st.selectbox("Search In:", ["All Documents"] + docs)
        doc_filter = None if doc_choice == "All Documents" else doc_choice

    if st.button("Find Knowledge Origin", type="primary"):
        if not concept_query.strip():
            st.warning("Please enter a concept or topic.")
            return

        with st.spinner(f"Locating '{concept_query}' across your document vault…"):
            result = where_did_i_learn(concept_query.strip(), doc_filter=doc_filter)

        if not result.get("found") or not result.get("locations"):
            st.info(result.get("message", "No mentions found in uploaded materials."))
            return

        st.markdown(f"<div class='glass-card' style='border-color:rgba(112,229,255,.4)'><div class='eyebrow'>Search Summary</div><p style='font-size:1.05rem;color:#e8f4ff;margin:.3rem 0 0;'>{escape(result.get('summary', ''))}</p></div>", unsafe_allow_html=True)

        locations = result.get("locations", [])
        st.markdown(f"### Found in {len(locations)} Location(s):")
        for idx, loc in enumerate(locations):
            doc_name = loc.get("document", "Unknown")
            page_num = loc.get("page", "N/A")
            section = loc.get("section", "Section")
            snippet = loc.get("snippet", "")
            takeaway = loc.get("takeaway", "")

            with st.container():
                st.markdown(
                    f"""<div class='glass-card'>
                    <div style='display:flex;justify-content:space-between;align-items:center;'>
                        <span class='badge-doc'>📄 {escape(doc_name)}</span>
                        <span class='source-chip'>Page {escape(str(page_num))}</span>
                    </div>
                    <h4 style='color:#70e5ff;margin:.6rem 0 .3rem;'>📌 {escape(section)}</h4>
                    <p style='color:#c5d8ed;font-size:.9rem;line-height:1.6;font-style:italic;background:rgba(0,0,0,.25);padding:8px 12px;border-radius:10px;'>"{escape(snippet)}"</p>
                    <p style='color:#8ca5be;font-size:.85rem;margin:0;'><strong>Takeaway:</strong> {escape(takeaway)}</p>
                    </div>""",
                    unsafe_allow_html=True
                )
                file_path = os.path.join(UPLOAD_DIR, doc_name)
                if doc_name.lower().endswith(".pdf") and os.path.exists(file_path) and isinstance(page_num, int):
                    if st.checkbox(f"Preview {doc_name} — Page {page_num}", key=f"preview_loc_{idx}"):
                        render_pdf_page(file_path, page_num - 1, f"{doc_name} (Page {page_num})")


# ==================== VIEW 12: TEACH ME MODE (FEATURE 3) ====================

def render_teach_me():
    from rag_chain import teach_me
    page_heading("Pedagogical AI", "Teach Me Mode", "Beginner-friendly explanations that progressively become technical, grounded strictly in your curriculum.")

    docs = get_available_documents()
    col1, col2 = st.columns([2, 1])
    with col1:
        topic = st.text_input("What topic would you like me to teach?", placeholder="e.g. Sampling Errors, SQL Injection, Laspeyres Index")
    with col2:
        doc_choice = st.selectbox("Base on Document:", ["Auto-detect across all documents"] + docs)
        doc_filter = None if doc_choice == "Auto-detect across all documents" else doc_choice

    if st.button("Teach Me This Topic", type="primary"):
        if not topic.strip():
            st.warning("Please specify a topic.")
            return

        with st.spinner(f"Preparing a structured masterclass on '{topic}'…"):
            response = teach_me(topic.strip(), doc_filter=doc_filter)

        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.markdown(response)
        st.markdown("</div>", unsafe_allow_html=True)


# ==================== VIEW 13: EXAM MODE (FEATURE 4) ====================

def render_exam_mode():
    from rag_chain import generate_exam_answer
    page_heading("Exam Ready Answers", "Exam Mode", "Generate high-scoring, structured university answers tailored precisely for 2, 5, 7, or 10 marks.")

    docs = get_available_documents()
    c1, c2, c3 = st.columns([2, 1.2, 1])
    with c1:
        topic = st.text_input("Exam Question or Topic:", placeholder="e.g. Classification of Cyber Crime, Sampling vs Census, GVA Compilation")
    with c2:
        marks = st.radio("Target Marks:", [2, 5, 7, 10], index=2, horizontal=True)
    with c3:
        doc_choice = st.selectbox("Syllabus Source:", ["All Documents"] + docs)
        doc_filter = None if doc_choice == "All Documents" else doc_choice

    if st.button(f"Generate {marks}-Mark Exam Answer", type="primary"):
        if not topic.strip():
            st.warning("Please enter an exam question or topic.")
            return

        with st.spinner(f"Writing {marks}-mark university answer for '{topic}'…"):
            answer = generate_exam_answer(topic.strip(), marks=marks, doc_filter=doc_filter)

        st.markdown(f"<div class='glass-card'><div class='eyebrow'>Exam Response · {marks} Marks</div>", unsafe_allow_html=True)
        st.markdown(answer)
        st.markdown("</div>", unsafe_allow_html=True)


# ==================== VIEW 14: QUESTION GENERATOR (FEATURE 5) ====================

def render_question_generator():
    from rag_chain import generate_questions
    page_heading("Exam Prep & Question Paper Studio", "Automatic Question Generator", "Generate customized examination questions, test papers, or viva questions from your documents.")

    docs = get_available_documents()
    c1, c2, c3 = st.columns([1.5, 1.2, 1])
    with c1:
        topic = st.text_input("Topic or Unit Focus:", placeholder="e.g. Cyber Crime Unit 1, Sampling Methods")
    with c2:
        q_type = st.selectbox("Question Type:", ["MCQs", "2-mark questions", "5-mark questions", "7-mark questions", "Viva questions"])
    with c3:
        count = st.slider("Count:", min_value=3, max_value=12, value=5)

    doc_choice = st.selectbox("Target Document:", ["All Uploaded Documents"] + docs)
    doc_filter = None if doc_choice == "All Uploaded Documents" else doc_choice

    if st.button("Generate Questions", type="primary"):
        with st.spinner(f"Generating {count} {q_type}…"):
            output = generate_questions(topic.strip(), question_type=q_type, count=count, doc_filter=doc_filter)

        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.markdown(output)
        st.markdown("</div>", unsafe_allow_html=True)


# ==================== VIEW 15: SMART NOTES (FEATURE 7) ====================

def render_smart_notes():
    from rag_chain import generate_smart_notes
    page_heading("Document Intelligence", "Smart Notes", "Structured, high-yield academic summaries capturing key definitions, frameworks, examples, and exam questions.")

    docs = get_available_documents()
    if not docs:
        st.warning("No documents in your vault yet. Please upload files in My Documents first.")
        return

    c1, c2 = st.columns([1.5, 1])
    with c1:
        doc_choice = st.selectbox("Choose Document:", docs)
    with c2:
        topic_focus = st.text_input("Optional Topic Focus:", placeholder="Leave empty for full summary")

    if st.button("Generate Smart Notes", type="primary"):
        with st.spinner(f"Distilling notes for '{doc_choice}'…"):
            notes = generate_smart_notes(doc_choice, topic=topic_focus.strip() or None)

        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.markdown(notes)
        st.download_button(
            "Download Smart Notes (.md)",
            data=notes,
            file_name=f"Smart_Notes_{os.path.splitext(doc_choice)[0]}.md",
            mime="text/markdown"
        )
        st.markdown("</div>", unsafe_allow_html=True)


# ==================== VIEW 16: COMPARE DOCUMENTS (FEATURE 12) ====================

def render_compare():
    from rag_chain import compare_documents
    page_heading("Comparative Analysis", "Compare Documents", "Identify commonalities, sharp differences, unique concepts, and knowledge gaps between two documents.")

    docs = get_available_documents()
    if len(docs) < 2:
        st.warning("Please upload at least 2 documents in 'My Documents' to compare them.")
        return

    c1, c2, c3 = st.columns([1, 1, 1.2])
    with c1:
        doc_a = st.selectbox("Document A:", docs, index=0)
    with c2:
        doc_b = st.selectbox("Document B:", docs, index=min(1, len(docs)-1))
    with c3:
        topic = st.text_input("Comparison Focus (Optional):", placeholder="e.g. Architecture, Security Controls, Methodology")

    if st.button("Run Comparative Analysis", type="primary"):
        if doc_a == doc_b:
            st.warning("Please choose two different documents to compare.")
            return

        with st.spinner(f"Comparing '{doc_a}' vs '{doc_b}'…"):
            result = compare_documents(doc_a, doc_b, topic=topic.strip() or None)

        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.markdown(result)
        st.markdown("</div>", unsafe_allow_html=True)


# ==================== VIEW 17: PERSONAL MEMORY (FEATURE 9) ====================

def render_memory():
    user = st.session_state.current_user
    page_heading("Personal Knowledge Layer", "My Memory", "Save personal notes, formulas, and facts separate from uploaded documents. Search and recall them at any time.")

    tab_browse, tab_add = st.tabs(["📖 Browse & Recall Memories", "➕ Save New Memory"])

    with tab_add:
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        m_title = st.text_input("Title / Topic:", placeholder="e.g. Sampling Error Formula, DPDP Exemption Rule")
        m_content = st.text_area("Memory Content / Fact:", placeholder="Enter your note, definition, or key takeaway here...", height=120)
        m_tags = st.text_input("Tags (comma separated):", placeholder="e.g. statistics, formula, survey")

        if st.button("Save to My Memory", type="primary"):
            if not m_content.strip():
                st.warning("Please enter note content.")
            else:
                db_manager.save_memory(user, m_content, title=m_title, tags=m_tags)
                st.success(f"Saved to My Memory: '{m_title or 'Note'}'")
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    with tab_browse:
        search_query = st.text_input("Search My Memory:", placeholder="Filter by keyword, title, or tag...")
        memories = db_manager.get_memories(user, search_query=search_query)

        if not memories:
            st.markdown(
                "<div class='empty-state'><div class='brain-visual' style='font-size:3rem;'>🧠</div>"
                "<p>No personal memories found. Add one in the 'Save New Memory' tab!</p></div>",
                unsafe_allow_html=True
            )
        else:
            st.markdown(f"<span class='badge-memory'>Showing {len(memories)} Saved Memory Item(s)</span>", unsafe_allow_html=True)
            for mem in memories:
                with st.container():
                    c_text, c_del = st.columns([5, 1])
                    with c_text:
                        tag_html = f"<div style='font-size:.75rem;color:#70e5ff;'>🏷 Tags: {escape(mem['tags'])}</div>" if mem.get('tags') else ""
                        st.markdown(
                            f"<div class='glass-card' style='margin-bottom:.6rem;'>"
                            f"<div style='display:flex;justify-content:space-between;align-items:center;'>"
                            f"<span class='badge-memory'>🧠 {escape(mem['title'])}</span>"
                            f"<span style='color:#758da4;font-size:.75rem;'>{escape(str(mem['created_at'])[:16])}</span>"
                            f"</div>"
                            f"<p style='color:#e4f1ff;margin:.6rem 0;line-height:1.6;'>{escape(mem['content'])}</p>"
                            f"{tag_html}"
                            f"</div>",
                            unsafe_allow_html=True
                        )
                    with c_del:
                        if st.button("Delete", key=f"del_mem_{mem['id']}"):
                            db_manager.delete_memory(user, mem["id"])
                            st.toast("Memory deleted.")
                            st.rerun()


# ==================== VIEW 18: KNOWLEDGE MAP (FEATURE 8) ====================

def render_knowledge_map():
    from rag_chain import extract_concept_graph
    page_heading("Visual Concept Map", "Knowledge Map", "Extract important concepts and their interrelationships from your uploaded documents.")

    docs = get_available_documents()
    c1, c2 = st.columns([1.5, 1.2])
    with c1:
        doc_choice = st.selectbox("Select Document:", ["All Documents"] + docs)
        doc_filter = None if doc_choice == "All Documents" else doc_choice
    with c2:
        topic_focus = st.text_input("Focus Topic (Optional):", placeholder="e.g. Cyber Crime, Sampling")

    if st.button("Generate Concept Graph", type="primary"):
        with st.spinner("Extracting concepts and relationship ontology…"):
            graph_data = extract_concept_graph(doc_name=doc_filter, focus_topic=topic_focus.strip() or None)

        nodes = graph_data.get("nodes", [])
        edges = graph_data.get("edges", [])

        if not nodes:
            st.info("No concepts extracted. Please upload documents with rich textual content.")
            return

        st.markdown(f"### 🌐 Extracted {len(nodes)} Concepts & {len(edges)} Relationships:")

        mermaid_lines = ["graph TD"]
        mermaid_lines.append("classDef root fill:#1c3974,stroke:#70e5ff,stroke-width:2px,color:#fff;")
        mermaid_lines.append("classDef branch fill:#10254c,stroke:#9194ff,stroke-width:1.5px,color:#fff;")
        mermaid_lines.append("classDef leaf fill:#0c1933,stroke:#6688aa,stroke-width:1px,color:#dcecff;")

        clean_id_map = {}
        for idx, node in enumerate(nodes):
            safe_id = f"node_{idx}"
            label = node.get("label", "").replace('"', '').replace("'", "")
            category = node.get("category", "branch")
            clean_id_map[node.get("id", safe_id)] = (safe_id, label, category)
            mermaid_lines.append(f'{safe_id}["{label}"]:::{category}')

        for edge in edges:
            src = edge.get("source")
            tgt = edge.get("target")
            rel = edge.get("relationship", "relates_to").replace("_", " ")
            if src in clean_id_map and tgt in clean_id_map:
                src_id = clean_id_map[src][0]
                tgt_id = clean_id_map[tgt][0]
                mermaid_lines.append(f'{src_id} -->|{rel}| {tgt_id}')

        mermaid_code = "\n".join(mermaid_lines)
        st.markdown(f"```mermaid\n{mermaid_code}\n```")

        with st.expander("View Concept & Relationship Table"):
            t_col1, t_col2 = st.columns(2)
            with t_col1:
                st.markdown("**Identified Concepts:**")
                for n in nodes:
                    st.write(f"• **{n.get('label')}** ({n.get('category', 'concept')})")
            with t_col2:
                st.markdown("**Relationships:**")
                for e in edges:
                    st.write(f"• `{e.get('source')}` → *{e.get('relationship', '')}* → `{e.get('target')}`")


# ==================== VIEW 19: STUDY PLANNER (FEATURE 10) ====================

def render_study_planner():
    from rag_chain import generate_study_plan_schedule
    user = st.session_state.current_user
    page_heading("Exam Strategist", "Study Planner", "Analyze uploaded syllabus materials and generate an active day-by-day study schedule with milestone tracking.")

    latest_plan = db_manager.get_latest_study_plan(user)
    docs = get_available_documents()

    tab_active, tab_create = st.tabs(["📅 Current Study Plan", "⚡ Create New Plan"])

    with tab_create:
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        subject = st.text_input("Subject / Course Name:", placeholder="e.g. Statistical Inference, Cyber Security")
        exam_date = st.date_input("Target Exam Date:", min_value=date.today() + timedelta(days=1), value=date.today() + timedelta(days=7))
        daily_hours = st.slider("Available Study Hours Per Day:", min_value=1.0, max_value=10.0, value=3.0, step=0.5)
        selected_materials = st.multiselect("Select Course Documents from Vault:", docs, default=docs[:2] if len(docs) >= 2 else docs)

        if st.button("Generate AI Study Schedule", type="primary"):
            if not subject.strip():
                st.warning("Please enter a subject name.")
            else:
                with st.spinner(f"Crafting optimized study plan for '{subject}'…"):
                    schedule = generate_study_plan_schedule(subject.strip(), exam_date, daily_hours, doc_names=selected_materials)

                if schedule:
                    db_manager.save_study_plan(user, subject.strip(), exam_date, daily_hours, schedule)
                    st.success("Study plan created and saved!")
                    st.rerun()
                else:
                    st.error("Could not generate schedule. Please check document content or input.")
        st.markdown("</div>", unsafe_allow_html=True)

    with tab_active:
        if not latest_plan or not latest_plan.get("schedule"):
            st.markdown(
                "<div class='glass-card empty-state'><div class='brain-visual' style='font-size:3rem;'>📅</div>"
                "<p>No active study plan found. Create one in the 'Create New Plan' tab!</p></div>",
                unsafe_allow_html=True
            )
        else:
            schedule = latest_plan["schedule"]
            progress = latest_plan.get("progress", {})

            total_days = len(schedule)
            completed_count = sum(1 for v in progress.values() if v)
            percent = round((completed_count / total_days) * 100) if total_days > 0 else 0

            st.markdown(
                f"<div class='glass-card'>"
                f"<div class='eyebrow'>Active Schedule</div>"
                f"<h2 style='margin:.3rem 0 .2rem;'>{escape(latest_plan['subject'])}</h2>"
                f"<p style='color:#8ea7c1;font-size:.88rem;'>Target Exam Date: <strong>{latest_plan['exam_date']}</strong> &nbsp;|&nbsp; Daily Commitment: <strong>{latest_plan['daily_hours']} hrs/day</strong></p>"
                f"</div>",
                unsafe_allow_html=True
            )

            st.progress(percent / 100.0, text=f"Progress: {completed_count} of {total_days} Days Completed ({percent}%)")

            updated = False
            for idx, day_info in enumerate(schedule):
                day_num = day_info.get("day", idx + 1)
                title = day_info.get("title", f"Day {day_num}")
                milestone = day_info.get("milestone", "")
                tasks = day_info.get("tasks", [])

                is_checked = progress.get(str(idx), False)

                with st.container():
                    c_chk, c_body = st.columns([0.08, 0.92])
                    with c_chk:
                        chk = st.checkbox("", value=is_checked, key=f"plan_task_{idx}")
                        if chk != is_checked:
                            progress[str(idx)] = chk
                            updated = True
                    with c_body:
                        st.markdown(
                            f"<div style='background:rgba(255,255,255,0.03);padding:10px 14px;border-radius:12px;margin-bottom:8px;border:1px solid rgba(175,217,255,.1);'>"
                            f"<strong style='color:{'#79f3c1' if chk else '#e8f4ff'};'>Day {day_num}: {escape(title)}</strong>"
                            f"<div style='color:#70e5ff;font-size:.78rem;'>🎯 Milestone: {escape(milestone)}</div>"
                            f"<ul style='margin:6px 0 0;padding-left:20px;font-size:.84rem;color:#b2c8dc;'>"
                            + "".join(f"<li>{escape(t)}</li>" for t in tasks) +
                            f"</ul></div>",
                            unsafe_allow_html=True
                        )

            if updated:
                db_manager.update_plan_progress(latest_plan["id"], progress)
                st.rerun()


# ==================== VIEW 20: VAULT / MY DOCUMENTS ====================

def ingest_uploaded_files(uploaded_files, progress_area):
    from ingest import ingest_file
    outcomes = []
    for uploaded_file in uploaded_files:
        safe_name = os.path.basename(uploaded_file.name)
        if safe_name in st.session_state.files_ingested:
            outcomes.append(("skipped", safe_name, "Already indexed"))
            continue
        file_path = os.path.join(UPLOAD_DIR, safe_name)
        try:
            with open(file_path, "wb") as destination:
                destination.write(uploaded_file.getbuffer())
            progress_bar = progress_area.progress(0, text=f"Preparing {safe_name}…")

            def on_progress(stage, percentage):
                progress_bar.progress(min(max(int(percentage), 0), 100), text=f"{safe_name} · {stage}")

            chunk_count = ingest_file(file_path, progress_callback=on_progress)
            progress_bar.progress(100, text=f"{safe_name} · indexed successfully")
            st.session_state.files_ingested.append(safe_name)
            outcomes.append(("success", safe_name, f"{chunk_count} knowledge chunks indexed"))
        except Exception as error:
            if os.path.exists(file_path):
                os.remove(file_path)
            outcomes.append(("error", safe_name, str(error)))
    st.session_state.files_ingested.sort()
    return outcomes


def render_vault():
    from ingest import remove_file_from_index
    page_heading("Document Vault", "My Documents", "Upload PDFs, DOCX, and TXT files. Files are indexed locally and grounded for instant search.")

    upload_col, files_col = st.columns([0.9, 1.35], gap="large")
    with upload_col:
        st.markdown(
            "<div class='glass-card'><div class='eyebrow'>Add Knowledge</div>"
            "<h3 style='margin:.55rem 0 .3rem'>Drop Files into Vault</h3>"
            "<p style='color:#9badc4;font-size:.88rem;line-height:1.6'>Scanned or image-based PDFs will automatically invoke OCR.</p>",
            unsafe_allow_html=True
        )
        uploaded = st.file_uploader(
            "Choose files", type=["pdf", "docx", "txt"],
            accept_multiple_files=True, label_visibility="collapsed"
        )
        progress_area = st.empty()
        if uploaded:
            for state, name, detail in ingest_uploaded_files(uploaded, progress_area):
                if state == "success":
                    st.success(f"{name} — {detail}")
                elif state == "error":
                    st.error(f"{name} could not be indexed: {detail}")
                else:
                    st.info(f"{name} — {detail}")
        st.markdown("<p style='color:#7890aa;font-size:.75rem;margin:1.1rem 0 0'>Supported: PDF, DOCX, UTF-8 TXT · Files remain on this device.</p></div>", unsafe_allow_html=True)

    with files_col:
        st.markdown("<div class='glass-card'><div class='eyebrow'>Indexed Vault Files</div><h3 style='margin:.55rem 0 1rem'>Your Documents</h3>", unsafe_allow_html=True)
        if not st.session_state.files_ingested:
            st.markdown("<div class='empty-state' style='padding:2.2rem 1rem;'><div class='brain-visual' style='font-size:3rem;'>🧠</div><p>No indexed documents yet.</p></div>", unsafe_allow_html=True)

        for name in list(st.session_state.files_ingested):
            path = os.path.join(UPLOAD_DIR, name)
            size = f"{get_file_size_mb(path):.2f} MB" if os.path.exists(path) else "File unavailable"
            row, view_action, action = st.columns([4.2, 1, 1])
            with row:
                st.markdown(f"<div class='file-row'><div class='file-name'>◫ &nbsp;{escape(name)}</div><div class='file-meta'>{size} · Ready for search</div></div>", unsafe_allow_html=True)
            with view_action:
                if name.lower().endswith(".pdf") and st.button("View", key=f"view_{name}", help=f"Open {name} in the app"):
                    st.session_state.open_pdf = None if st.session_state.get("open_pdf") == name else name
            with action:
                if st.button("Remove", key=f"remove_{name}", help=f"Remove {name} from index"):
                    try:
                        remove_file_from_index(path)
                        if os.path.exists(path):
                            os.remove(path)
                        st.session_state.files_ingested.remove(name)
                        st.toast(f"Removed {name} from vault")
                        st.rerun()
                    except Exception as error:
                        st.error(f"Could not remove {name}: {error}")

            if st.session_state.get("open_pdf") == name and os.path.exists(path):
                st.markdown(f"<div style='height:.6rem'></div><div class='eyebrow'>Document Viewer · {escape(name)}</div>", unsafe_allow_html=True)
                render_pdf_document(path)
        st.markdown("</div>", unsafe_allow_html=True)


# ==================== VIEW 21: SETTINGS ====================

def render_settings():
    page_heading("Workspace Management", "Settings", "Manage conversation history or reset the knowledge base.")

    st.markdown("<div class='glass-card'><div class='eyebrow'>Conversation</div><h3 style='margin:.5rem 0 .3rem;'>Start a Fresh Chat</h3><p style='color:#9badc4'>Clear the active chat history while keeping all your documents and memories intact.</p>", unsafe_allow_html=True)
    if st.button("Clear Chat History"):
        st.session_state.chat_history = []
        st.success("Chat history cleared.")

    st.markdown("</div><div style='height:1rem;'></div><div class='glass-card' style='border-color:rgba(255,117,141,.3);'><div class='eyebrow' style='color:#ff9aab'>Danger Zone</div><h3 style='margin:.5rem 0 .3rem;'>Reset Knowledge Vault</h3><p style='color:#bca4ad'>Permanently delete every uploaded document and the local search index.</p>", unsafe_allow_html=True)
    confirm = st.checkbox("I understand this permanently clears my local vault.")
    if st.button("Reset All Knowledge", disabled=not confirm):
        reset_database()
        clear_uploads()
        st.session_state.files_ingested = []
        st.session_state.chat_history = []
        st.success("Local knowledge vault reset.")
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


# ==================== APP ROUTER ====================

inject_styles()
init_state()

if not st.session_state.boot_complete:
    render_boot()
elif not st.session_state.authenticated:
    render_auth()
else:
    render_sidebar()
    views = {
        # SIH26101 Core Views
        "Dashboard": render_dashboard,
        "Profile": render_learner_profile,
        "Diagnostic": render_diagnostic_assessment,
        "SkillGaps": render_skill_gaps,
        "LearningPath": render_learning_path,
        "DocCompetencies": render_document_competencies,
        "Admin": render_admin_dashboard,
        "Framework": render_framework_overview,
        # Second Brain Core Views
        "Ask": render_ask_brain,
        "WhereLearned": render_where_learned,
        "Memory": render_memory,
        "TeachMe": render_teach_me,
        "ExamMode": render_exam_mode,
        "QuizMode": render_quiz_mode,
        "QuestionGen": render_question_generator,
        "SmartNotes": render_smart_notes,
        "Compare": render_compare,
        "StudyPlanner": render_study_planner,
        "Vault": render_vault,
        "KnowledgeMap": render_knowledge_map,
        "Settings": render_settings,
    }
    view_func = views.get(st.session_state.current_view, render_dashboard)
    view_func()
