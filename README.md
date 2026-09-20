# 🧠 Second Brain — AI Knowledge & Study Assistant

Apne PDFs, DOCX aur TXT documents ko ek private, searchable "second brain" me badlo.
Sawal poocho, exam answers banao, quiz do, notes aur study plan generate karo — sab kuch
**strictly aapke uploaded documents ke basis par**, verified page-level citations ke saath.

Local-first: files, search index aur aapka data aapki hi machine par rehta hai.
Sirf AI responses ke liye internet (Groq API) chahiye.

---

## ✨ Features

| Feature | Kya karta hai |
|---|---|
| 💬 **Ask Across Documents** | Saare documents par ek saath Q&A, verbatim quote verification + PDF page preview |
| 📍 **Where Did I Learn This?** | Concept kis document ke kis page/section me padhaya gaya hai, wo dhoondta hai |
| 🎓 **Teach Me Mode** | Beginner → technical, 7-part structured explanation |
| 🎯 **Exam Mode** | 2 / 5 / 7 / 10 marks ke hisaab se university-level exam answers |
| ❓ **Question Generator** | MCQs, 2/5/7-mark questions aur viva questions |
| 🧪 **Interactive Quiz** | Auto-scoring + explanations + weak topics detection aur re-practice |
| 📝 **Smart Notes** | Structured academic notes (definitions, mechanisms, high-yield questions) — Markdown download |
| 🗺 **Knowledge Map** | Concept graph (Mermaid diagram) — nodes, relationships, categories |
| ⚖ **Compare Documents** | Do documents ka side-by-side comparison table + unique/contrasting concepts |
| 📅 **Study Planner** | Exam date ke hisaab se day-by-day schedule + milestone checklist tracking |
| 🧠 **My Memory** | Documents se alag apne personal notes/formulas save, search aur delete karo |
| 🏠 **Dashboard** | Vault stats, questions asked, quiz accuracy, weak topics, study progress |
| 📚 **My Documents** | Upload, index, view (built-in PDF viewer) aur remove documents |

Unsupported/scanned PDFs par **OCR** automatically chal jaata hai.

---

## ⚡ Quick Start

**Prerequisites:** Python 3.10+, [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki) (scanned PDFs ke liye), aur [Groq API key](https://console.groq.com).

```bash
# 1. Project folder me jao (paths relative hain — yahin se run karna zaroori hai)
cd second-brain-rag

# 2. Virtual environment
python -m venv .venv
source .venv/Scripts/activate     # Windows (Git Bash)
# source .venv/bin/activate       # Linux / macOS

# 3. Dependencies
pip install -r requirements.txt

# 4. .env file banao (project root me)
#    GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxx

# 5. App run karo
streamlit run app.py
```

App khul jaayega: **http://localhost:8501** → splash screen → **Create account** → login → upload documents → poocho!

> 🍎 macOS / 🐧 Linux par OCR ke liye `ingest.py` me `pytesseract.pytesseract.tesseract_cmd`
> ka path `C:\Program Files\...` se apne system ke path me badalna hoga.

---

## 🛠 Tech Stack

| Layer | Technology |
|---|---|
| UI | Streamlit + custom CSS (dark glassmorphism theme) |
| LLM | Groq API — `openai/gpt-oss-120b` (`temperature=0`, strict JSON + grounding) |
| Retrieval | Custom local hybrid search — 384-dim hashed embeddings + keyword/phrase scoring (koi vector DB nahi) |
| Parsing | PyMuPDF (PDF + page rendering), pytesseract OCR, Docx2txt, TextLoader |
| Chunking | LangChain `RecursiveCharacterTextSplitter` (1000 chars / 150 overlap) |
| Storage | SQLite (`users.db`) + JSON vector index (`db/second_brain_index.json`) |
| Auth | SQLite + `bcrypt` password hashing |

---

## 📁 Project Structure

```
app.py          # Streamlit UI + view router (saare screens)
rag_chain.py    # Retrieval + LLM prompts + saare features ka AI logic
ingest.py       # File loading, OCR, chunking, embeddings, local JSON index
db_manager.py   # SQLite tables: memories, quiz_history, study_plans, activity_log
auth.py         # Users table + bcrypt hashing
utils.py        # File validation, analytics, reset helpers
test.py         # Manual retrieval smoke test
uploads/        # Aapke original documents
db/             # Local search index
users.db        # Accounts + saved memories/quiz/plans
```

---

## 🔒 Privacy & Grounding

- **Local-first:** documents, index aur account data device chhodte nahi (sirf LLM ke liye text excerpts bhejte hain).
- **Strict grounding:** agar answer documents me nahi hai, app bolta hai —
  *"I could not find this information in the uploaded document(s)."*
- **Citation verification:** model ka har quote original chunk se verbatim match karke verify hota hai;
  sirf tabhi page number dikhaya jaata hai.
- Extra knowledge ya invented page numbers ko model ko use karne se prompt level par roka gaya hai.

---

## 📖 Documentation

Poori project documentation — architecture, retrieval engine, database schema, setup, known limitations
aur troubleshooting — **[PROJECT_GUIDE.md](PROJECT_GUIDE.md)** me hai.

---

## 🐛 Common Issues

| Problem | Fix |
|---|---|
| `GROQ_API_KEY is not set in the .env file` | Project root me `.env` banao aur key daalo |
| Scanned PDF se text nahi nikla | Tesseract install karo / path sahi karo |
| "could not find this information" | Document **My Documents** me indexed hai check karo; query me topic-specific words use karo |
| App port busy | `streamlit run app.py --server.port 8502` |
| Reset ke baad bhi files bachi | App band karke `uploads/` aur `db/` manually delete karo (Windows file lock) |
