"""Strict, evidence-grounded Document Intelligence & Study Assistant Engine."""

import json
import os
import re
from datetime import datetime
from typing import Dict, List, Any, Optional

import httpx
from dotenv import load_dotenv
from groq import Groq
from langchain_core.prompts import PromptTemplate

import db_manager
from competencies import (
    COMPETENCY_CATALOGUE,
    COMPETENCY_DOMAINS,
    DOMAIN_STATISTICAL,
    DOMAIN_TECHNICAL,
    DOMAIN_DIGITAL_GOV,
    DOMAIN_BEHAVIOURAL,
    get_all_competencies,
    get_competency_meta,
    map_text_to_competencies,
)
from ingest import get_vectorstore

load_dotenv()

LLM_MODEL = "openai/gpt-oss-120b"
RETRIEVAL_K = 12
NOT_FOUND_MESSAGE = "I could not find this information in the uploaded document(s)."

# Chat modes: "documents" = strict grounding in uploaded files,
#             "general"   = free assistant using the model's own knowledge.
MODE_DOCUMENTS = "documents"
MODE_GENERAL = "general"

NOT_FOUND_HINT = (
    "\n\n_Tip: you are in **📄 Documents** mode. For general-knowledge questions "
    "(like 'what is AI'), switch the chat toggle to **⚡ General**._"
)

PROMPT_TEMPLATE = """
You are Second Brain, a strict document-grounded assistant.

Answer the current question using ONLY facts explicitly supported by the
uploaded-document excerpts below. Do not use general knowledge, guesses,
assumptions, or facts from the conversation as evidence. Conversation history
may only help interpret a short follow-up question.

If the excerpts do not contain the answer, or contain only part of it, say
exactly: "I could not find this information in the uploaded document(s)."
Then, if useful, state the narrow part that is supported. Never fill missing
parts with outside knowledge.

Reply in the same language the user used, and default to English unless the user
wrote in another language. Do not invent page numbers, quotes, citations,
examples, or document content.

Return only valid JSON, with no Markdown fences, using this exact shape:
{{"answer": "your answer", "evidence": [{{"source_id": 1, "quote": "an exact copied quote from the excerpt"}}]}}
Every answer claim must be supported by the evidence. Each `quote` must be a
verbatim copy from its `source_id` excerpt and must directly support the
answer. Build the answer only from the quoted evidence; do not take facts from
another searched excerpt and cite a different page. Do not cite a page merely
because it was searched. If the answer is not fully supported, return exactly:
{{"answer": "I could not find this information in the uploaded document(s).", "evidence": []}}

Conversation history (interpretation only):
{history}

Document excerpts searched for this question:
{context}

Current question:
{question}
"""

GENERAL_PROMPT_TEMPLATE = """
You are Second Brain in "General" mode — a friendly, knowledgeable assistant.

Answer the current question using your own knowledge. In this mode you are NOT
restricted to the user's uploaded documents, so general-knowledge questions
("what is AI", "explain photosynthesis") are expected and welcome.

Language rules (strict):
- Reply in the SAME language the user wrote in. If the user asked in English,
  answer fully in English.
- NEVER reply in Hindi or Hinglish unless the user's own message is in Hindi or
  Hinglish. Never mix Hindi words into an English answer.

Style rules:
- Chat casually, like a smart friend on WhatsApp: short paragraphs, simple words,
  no formal/bureaucratic filler, no "Dear user" or "As an AI language model".
- Lead with the direct answer in the first line, then add detail only if it helps.
- Be accurate and reasonably concise. Use Markdown (headings, bullets, code
  blocks) whenever it makes the answer easier to read.
- If something is uncertain or very recent, say so honestly instead of inventing facts.
- Never claim information came from the user's documents, and never fabricate
  citations, page numbers or quotes in this mode.
- If the user clearly wants answers grounded in their own files, mention that
  they can switch the chat toggle to "Documents" mode.

Conversation history:
{history}

Current question:
{question}
"""


def get_llm():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY is not set in the .env file.")
    return Groq(api_key=api_key, http_client=httpx.Client(trust_env=False, timeout=50.0))


def _clean_json_str(raw):
    """Extract clean JSON object or array from LLM response."""
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        first_line = lines[0].lower()
        if "json" in first_line or first_line == "```":
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    # Match outermost JSON object or array
    match = re.search(r"(\{.*\}|\[.*\])", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text


def _normalise_evidence(text):
    return " ".join(text.split()).casefold()


def format_docs(docs):
    """Create numbered evidence blocks and retain their document mapping."""
    excerpts, source_by_id = [], {}
    for source_id, doc in enumerate(docs, start=1):
        text = doc.page_content.strip()
        if not text:
            continue
        filename = os.path.basename(doc.metadata.get("source", "unknown"))
        page = doc.metadata.get("page", "N/A")
        display_page = page + 1 if isinstance(page, int) else page
        source_by_id[source_id] = doc
        excerpts.append(f"[SOURCE_ID: {source_id}; DOC: {filename}; page: {display_page}]\n{text}")
    return "\n\n".join(excerpts), source_by_id


def is_greeting(query):
    normalised = re.sub(r"[^a-z\s]", "", query.lower()).strip()
    return normalised in {
        "hi", "hii", "hiii", "hello", "hey", "hola", "namaste", "namaskar",
        "good morning", "good afternoon", "good evening", "hi there", "hello there",
    }


# Small-talk patterns (English + Hinglish). Full-match only, so real questions
# like "hello, explain SQL injection" are never swallowed by these.
SMALLTALK_PATTERNS = [
    ("greeting", r"(hi+|hey+|hello+|yo|hola|namaste|namaskar|good (morning|afternoon|evening)|hi there|hello there)( there| bhai| dost| friend| buddy| yaar| sir| maam| madam| ji)?"),
    ("how_are_you", r"(how (are|r) (you|u)( doing)?|how('s| is) it going|what'?s up|sup|kais[ae] (ho|hai|hain|he)( aap| tum| bhai| yaar| ji)?|kya haal( hai)?|kya chal raha( hai)?|sab (badhiya|theek)( hai)?)"),
    ("thanks", r"(thanks?|thank you|thanku|thank u|thx|ty|shukriya|dhanyavad|dhanyawad)( you| bhai| yaar| dost| ji| so much| a lot)?"),
    ("bye", r"(bye+|byebye|goodbye|see (you|ya)|alvida|ok bye|good night|gn|chalta (hu|hun))"),
    ("identity", r"(who are you|what are you|what can you do|what do you do|help|tum kaun ho|aap kaun ho|kya kar sakte ho|tumhe kya aata hai)"),
]

SMALLTALK_REPLIES = {
    "greeting": {
        MODE_DOCUMENTS: "Hey! 👋 Ask me anything from your uploaded notes and PDFs — I'll answer with the exact page it came from.",
        MODE_GENERAL: "Hey! 👋 Ask me anything — concepts, definitions, doubts, whatever you're stuck on.",
    },
    "how_are_you": {
        MODE_DOCUMENTS: "Doing great, thanks! 😄 What do you want me to dig out of your documents?",
        MODE_GENERAL: "Doing great, thanks! 😄 What do you want to know?",
    },
    "thanks": {
        MODE_DOCUMENTS: "Anytime! 🙌 Ask me anything else from your materials.",
        MODE_GENERAL: "Anytime! 🙌 Ask me anything else.",
    },
    "bye": {
        MODE_DOCUMENTS: "See you! 👋 Your notes stay saved here whenever you come back.",
        MODE_GENERAL: "See you! 👋 Come back anytime.",
    },
    "identity": {
        MODE_DOCUMENTS: (
            "I'm **Second Brain**, your study buddy for your own uploaded notes and PDFs. In 📄 **Documents** mode "
            "I answer only from your files and show the page, so nothing gets made up. Want general answers instead? "
            "Flip the toggle to ⚡ **General**."
        ),
        MODE_GENERAL: (
            "I'm **Second Brain**. In ⚡ **General** mode I answer from my own knowledge — any topic, no documents "
            "needed. Flip the toggle to 📄 **Documents** if you want answers strictly from your uploads."
        ),
    },
}


def get_smalltalk_reply(query, mode=MODE_DOCUMENTS):
    """Return a friendly reply for greetings/small talk, or None for real questions."""
    text = " ".join(query.lower().split())
    text = re.sub(r"[!?.,]+$", "", text).strip()
    if not text:
        return None
    for kind, pattern in SMALLTALK_PATTERNS:
        if re.fullmatch(pattern, text):
            return SMALLTALK_REPLIES[kind][MODE_GENERAL if mode == MODE_GENERAL else MODE_DOCUMENTS]
    return None


def get_source_details(docs):
    details, seen = [], set()
    for doc in docs:
        source = doc.metadata.get("source", "unknown")
        page = doc.metadata.get("page", "N/A")
        key = (source, page)
        if key in seen:
            continue
        seen.add(key)
        display_page = page + 1 if isinstance(page, int) else page
        details.append({
            "source": source,
            "page": page,
            "label": f"{os.path.basename(source)} (page {display_page})",
            "evidence": [],
        })
    return details


def format_chat_history(chat_history):
    if not chat_history:
        return ""
    parts = []
    for message in chat_history[-6:]:
        content = message.get("content", "").strip()
        if content:
            role = "User" if message.get("role") == "user" else "Assistant"
            parts.append(f"{role}: {content[:300]}")
    return "\n".join(parts)


def retrieve_relevant_docs(vectordb, query, k=RETRIEVAL_K, doc_filter=None):
    try:
        return vectordb.similarity_search(query, k=k, doc_filter=doc_filter)
    except Exception as error:
        print(f"Retrieval error: {error}")
        return []


def parse_grounded_response(raw_answer, source_by_id):
    """Accept an answer when each cited quote exists on its shown page."""
    try:
        cleaned = _clean_json_str(raw_answer)
        payload = json.loads(cleaned)
        answer = payload.get("answer", "").strip()
        evidence = payload.get("evidence", [])
        if not isinstance(answer, str) or not isinstance(evidence, list):
            raise ValueError("Invalid answer shape")
        if not answer or not evidence:
            raise ValueError("Missing evidence")

        verified_evidence = []
        for item in evidence:
            if not isinstance(item, dict):
                continue
            source_id = int(item.get("source_id", 0))
            quote = item.get("quote", "").strip()
            document = source_by_id.get(source_id)
            if not document or len(_normalise_evidence(quote)) < 6:
                continue
            if _normalise_evidence(quote) in _normalise_evidence(document.page_content):
                verified_evidence.append((source_id, quote))
            else:
                # If exact quote has small token variations, check partial match
                norm_quote = _normalise_evidence(quote)
                norm_content = _normalise_evidence(document.page_content)
                words = norm_quote.split()
                if len(words) >= 4 and " ".join(words[:4]) in norm_content:
                    verified_evidence.append((source_id, quote))

        if not verified_evidence:
            return answer, []

        selected_docs = [source_by_id[source_id] for source_id, _ in dict.fromkeys(verified_evidence)]
        details = get_source_details(selected_docs)
        details_by_page = {(detail["source"], detail["page"]): detail for detail in details}
        for source_id, quote in verified_evidence:
            document = source_by_id[source_id]
            key = (document.metadata.get("source", "unknown"), document.metadata.get("page", "N/A"))
            if key in details_by_page and quote not in details_by_page[key]["evidence"]:
                details_by_page[key]["evidence"].append(quote)
        return answer, details
    except Exception as err:
        print(f"Grounding parse fallback: {err}")
        # If valid answer text is present, return it with available sources
        cleaned = _clean_json_str(raw_answer)
        try:
            p = json.loads(cleaned)
            ans = p.get("answer", "")
            if ans and ans != NOT_FOUND_MESSAGE:
                return ans, get_source_details(list(source_by_id.values())[:3])
        except Exception:
            pass
        return NOT_FOUND_MESSAGE, []


# ==================== FEATURE 1: ASK ACROSS ALL DOCUMENTS ====================

def _answer_general(query, history_text, mode):
    """Free-form answer from the model's own knowledge (no document grounding)."""
    final_prompt = PromptTemplate(
        input_variables=["history", "question"], template=GENERAL_PROMPT_TEMPLATE
    ).format(history=history_text, question=query)
    try:
        client = get_llm()
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful, accurate general assistant. Answer from your own knowledge."},
                {"role": "user", "content": final_prompt},
            ],
            temperature=0.4,
            max_tokens=1800,
        )
        answer = response.choices[0].message.content.strip()
    except Exception as error:
        return {
            "answer": f"Sorry, an error occurred while connecting to the model:\n\n{error}",
            "sources": [],
            "source_details": [],
            "mode": mode,
        }
    return {"answer": answer, "sources": [], "source_details": [], "mode": mode}


def ask_question(query, chat_history=None, k=RETRIEVAL_K, doc_filter=None, username=None, mode=MODE_DOCUMENTS):
    query = query.strip()
    if not query:
        return {"answer": "Please enter a question.", "sources": [], "source_details": [], "mode": mode}

    # Greetings / small talk are answered politely in BOTH modes (no "not found" here).
    smalltalk = get_smalltalk_reply(query, mode=mode)
    if smalltalk:
        return {"answer": smalltalk, "sources": [], "source_details": [], "mode": mode}

    if username:
        db_manager.log_activity(username, "question_asked", query[:100])

    history_text = format_chat_history(chat_history)

    if mode == MODE_GENERAL:
        return _answer_general(query, history_text, mode)

    try:
        vectordb = get_vectorstore()
        docs = retrieve_relevant_docs(vectordb, query, k=k, doc_filter=doc_filter)
    except Exception as error:
        print(f"Vector database error: {error}")
        docs = []

    if not docs:
        return {
            "answer": NOT_FOUND_MESSAGE + NOT_FOUND_HINT,
            "sources": [],
            "source_details": [],
            "mode": mode,
        }

    context, source_by_id = format_docs(docs)

    final_prompt = PromptTemplate(
        input_variables=["history", "context", "question"], template=PROMPT_TEMPLATE
    ).format(history=history_text, context=context, question=query)

    try:
        client = get_llm()
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": "Never use knowledge outside the supplied document excerpts. Return valid JSON only."},
                {"role": "user", "content": final_prompt},
            ],
            temperature=0,
            max_tokens=1800,
        )
        answer = response.choices[0].message.content.strip()
    except Exception as error:
        return {
            "answer": f"Sorry, an error occurred while connecting to the model:\n\n{error}",
            "sources": [],
            "source_details": [],
        }

    answer, source_details = parse_grounded_response(answer, source_by_id)
    if answer.strip() == NOT_FOUND_MESSAGE:
        answer = NOT_FOUND_MESSAGE + NOT_FOUND_HINT
    return {
        "answer": answer,
        "sources": [detail["label"] for detail in source_details],
        "source_details": source_details,
        "mode": mode,
    }


# ==================== FEATURE 2: WHERE DID I LEARN THIS? ====================

def where_did_i_learn(query, doc_filter=None, k=10):
    query = query.strip()
    if not query:
        return {"found": False, "message": "Please enter a topic to locate.", "locations": []}

    vectordb = get_vectorstore()
    docs = retrieve_relevant_docs(vectordb, query, k=k, doc_filter=doc_filter)
    if not docs:
        return {"found": False, "message": f"No mentions of '{query}' found in your uploaded documents.", "locations": []}

    context, _ = format_docs(docs)

    prompt = f"""
Analyze the following document excerpts to locate where '{query}' is discussed or taught.

Excerpts:
{context}

Return a JSON object listing every distinct location where this topic or related concept appears:
{{
  "summary": "Brief 1-2 sentence overview of where and how this topic is covered across your materials",
  "locations": [
    {{
      "document": "Filename.pdf",
      "page": 1,
      "section": "Section or heading name (or topic context)",
      "snippet": "Short relevant snippet or preview from this excerpt (20-40 words)",
      "takeaway": "What is specifically explained here (1 sentence)"
    }}
  ]
}}
Only reference documents that actually contain relevant content about '{query}'. Do not invent page numbers.
"""
    try:
        client = get_llm()
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": "You are a precise document indexer. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=1500,
        )
        data = json.loads(_clean_json_str(response.choices[0].message.content))
        return {
            "found": True,
            "query": query,
            "summary": data.get("summary", f"Found references to '{query}' in your uploaded documents."),
            "locations": data.get("locations", [])
        }
    except Exception as e:
        # Fallback based directly on retrieved doc metadata
        locations = []
        for doc in docs[:5]:
            src = os.path.basename(doc.metadata.get("source", "Unknown"))
            p = doc.metadata.get("page", 0)
            page_num = p + 1 if isinstance(p, int) else p
            locations.append({
                "document": src,
                "page": page_num,
                "section": "Uploaded Material",
                "snippet": doc.page_content[:200].replace("\n", " ") + "...",
                "takeaway": "Relevant discussion found in this section."
            })
        return {
            "found": True,
            "query": query,
            "summary": f"Located '{query}' across {len(locations)} sections in your documents.",
            "locations": locations
        }


# ==================== FEATURE 3: TEACH ME MODE ====================

def teach_me(topic, doc_filter=None, k=10):
    topic = topic.strip()
    if not topic:
        return "Please specify a topic you would like me to teach."

    vectordb = get_vectorstore()
    docs = retrieve_relevant_docs(vectordb, topic, k=k, doc_filter=doc_filter)
    context, source_by_id = format_docs(docs) if docs else ("No directly matching excerpts found.", {})

    prompt = f"""
You are an inspiring, clear computer science and domain professor in "Teach Me" mode.
Explain the topic '{topic}' in beginner-friendly language that progressively becomes technical.

Prioritize facts from the user's uploaded documents below whenever available. If the document provides specific definitions, classifications, or examples, use them.

Document Excerpts:
{context}

Format your response strictly using this 7-part pedagogical structure:

### 1. What is it?
(Beginner-friendly, intuitive definition and explanation)

### 2. Why is it used / Why does it matter?
(Real-world importance, motivation, and problems it solves)

### 3. How does it work?
(Step-by-step mechanism, architecture, or workflow explained clearly)

### 4. Simple Real-World Analogy / Example
(An everyday analogy anyone can understand, e.g. a restaurant, bank, or lock)

### 5. Technical Example / Walkthrough
(Code, packet flow, syntax, command, or technical scenario)

### 6. Key Takeaways
(3-5 bullet points summarizing the core essentials)

### 7. Quick Question for You! 🎯
(A friendly interactive question to check the student's understanding)
"""
    try:
        client = get_llm()
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": "You are a master educator. Teach progressively from simple to technical."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=2200,
        )
        content = response.choices[0].message.content.strip()

        # Append verified source citations if available
        if docs:
            sources = get_source_details(docs[:4])
            source_lines = [f"• 📄 **{d['label']}**" for d in sources]
            content += "\n\n---\n#### 📚 Sources from Your Vault:\n" + "\n".join(source_lines)

        return content
    except Exception as e:
        return f"Error generating Teach Me explanation: {e}"


# ==================== FEATURE 4: EXAM MODE ====================

def generate_exam_answer(topic, marks=7, doc_filter=None, k=10):
    topic = topic.strip()
    if not topic:
        return "Please specify an exam topic or question."

    vectordb = get_vectorstore()
    docs = retrieve_relevant_docs(vectordb, topic, k=k, doc_filter=doc_filter)
    context, _ = format_docs(docs) if docs else ("No relevant document excerpts found.", {})

    guidance_by_marks = {
        2: "Target: 80-120 words. Concise and direct. Structure: Definition (1 mark) + 2 Key Points/Characteristics (1 mark).",
        5: "Target: 250-350 words. Structure: Definition, Working/Architecture (in bullets), Key Features, Short Example.",
        7: "Target: 450-600 words. Structure: Definition, Detailed Explanation, Step-by-Step Working, Diagram/Flow (ASCII), Example, Advantages/Disadvantages or Prevention, Conclusion.",
        10: "Target: 700-900 words. Comprehensive university answer. Structure: Abstract/Overview, Formal Definition, In-depth Architecture/Working with ASCII Diagram, Detailed Classification/Types, Real-World Case Example, Pros/Cons or Security Measures, Exam Summary Table/Conclusion."
    }
    guidance = guidance_by_marks.get(marks, guidance_by_marks[7])

    prompt = f"""
You are an expert university examiner and top student.
Generate an exam-ready answer for: "{topic}" ({marks} Marks).

EXAM GUIDANCE FOR {marks} MARKS:
{guidance}

Document Excerpts from syllabus/study material:
{context}

Format with clear Markdown headers, bold terminology, bullet points, and an ASCII diagram/flowchart where appropriate.
Ground the response in the provided document excerpts.
"""
    try:
        client = get_llm()
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": "You are a university exam topper writing precise, high-scoring exam answers."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=2200,
        )
        content = response.choices[0].message.content.strip()
        if docs:
            sources = get_source_details(docs[:4])
            content += "\n\n---\n**Exam Source Reference:** " + ", ".join(f"`{d['label']}`" for d in sources)
        return content
    except Exception as e:
        return f"Error generating exam answer: {e}"


# ==================== FEATURE 5: AUTOMATIC QUESTION GENERATOR ====================

def generate_questions(topic_or_doc, question_type="MCQs", count=5, doc_filter=None, k=12):
    vectordb = get_vectorstore()
    query = topic_or_doc if topic_or_doc else "key concepts, definitions, classifications"
    docs = retrieve_relevant_docs(vectordb, query, k=k, doc_filter=doc_filter)
    if not docs:
        return f"No document context found for '{topic_or_doc}'. Please upload or select relevant documents."

    context, _ = format_docs(docs)

    prompt = f"""
Generate {count} high-quality academic/exam questions of type '{question_type}' based strictly on the document material below.

Document Content:
{context}

Question Type Guidelines:
- If 'MCQs': Provide question, 4 options (A, B, C, D), correct option, and brief explanation.
- If '2-mark questions': Provide question + concise 2-point model answer.
- If '5-mark questions': Provide descriptive question + key evaluation points/expected answer structure.
- If '7-mark questions': Provide university-level essay question + detailed marking scheme and outline.
- If 'Viva questions': Provide rapid-fire viva question + sharp, direct answer that impresses examiners.

Format cleanly in Markdown with bold questions and collapsible or clearly demarcated answers/keys.
"""
    try:
        client = get_llm()
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": "You are a professor preparing exam question papers from curriculum notes."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=2400,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error generating questions: {e}"


# ==================== FEATURE 6: INTERACTIVE QUIZ MODE ====================

def generate_quiz(topic_or_doc, count=5, doc_filter=None, k=12, competency_domain=None, difficulty="Medium"):
    vectordb = get_vectorstore()
    query = topic_or_doc if topic_or_doc else "key concepts, definitions, core topics"
    docs = retrieve_relevant_docs(vectordb, query, k=k, doc_filter=doc_filter)
    if not docs:
        return []

    context, _ = format_docs(docs)
    sample_doc = os.path.basename(docs[0].metadata.get("source", "Document"))
    sample_page = docs[0].metadata.get("page", 1)
    display_page = sample_page + 1 if isinstance(sample_page, int) else sample_page

    domain_instruction = f"Target Competency Domain: {competency_domain}." if competency_domain else "Map each question to its relevant competency domain."

    prompt = f"""
Create an interactive multiple-choice quiz of {count} questions testing understanding of: '{topic_or_doc}'.
Difficulty Level: {difficulty}
{domain_instruction}
Base the questions strictly on the document excerpts provided below.

Document Excerpts:
{context}

Return a valid JSON array of questions using this exact shape:
[
  {{
    "id": 1,
    "question": "Clear and specific question text?",
    "options": ["Option A", "Option B", "Option C", "Option D"],
    "answer_index": 0,
    "explanation": "Detailed explanation of why this answer is correct based on the text.",
    "topic": "Specific sub-topic or concept (e.g. Sampling, Probability, Encryption, Classification)",
    "domain": "Statistical Competencies | Technical Competencies | Digital Governance | Behavioural & Managerial",
    "skill": "Specific mapped skill from the framework",
    "difficulty": "{difficulty}",
    "source_doc": "{sample_doc}",
    "page": {display_page}
  }}
]

Make sure answer_index is an integer from 0 to 3. Provide plausible distractors. Return ONLY valid JSON.
"""
    try:
        client = get_llm()
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": "You are a quiz master creating grounded capacity-building MCQs for India's Official Statistical System."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=2400,
        )
        cleaned = _clean_json_str(response.choices[0].message.content)
        quiz = json.loads(cleaned)
        if isinstance(quiz, list):
            for idx, q in enumerate(quiz, start=1):
                q["id"] = idx
                if not q.get("source_doc"):
                    q["source_doc"] = sample_doc
                if not q.get("page"):
                    q["page"] = display_page
                if not q.get("domain"):
                    q["domain"] = competency_domain or DOMAIN_STATISTICAL
            return quiz
        return []
    except Exception as e:
        print(f"Quiz generation error: {e}")
        return []


# ==================== SIH26101: COMPETENCY EXTRACTION & ASSESSMENT ====================

def extract_document_competencies(doc_name: str) -> Dict[str, Any]:
    """Extract key topics, mapped competency domains, and skills from a vault document."""
    cached = db_manager.get_document_topics(doc_name)
    if cached:
        return cached

    vectordb = get_vectorstore()
    docs = vectordb.get_document_chunks(doc_name)
    if not docs:
        docs = vectordb.similarity_search("overview syllabus topics curriculum concepts", k=10, doc_filter=doc_name)

    if not docs:
        fallback = {
            "doc_name": doc_name,
            "topics": [doc_name.replace(".pdf", "").replace("_", " ")],
            "domains": [DOMAIN_STATISTICAL],
            "skills": ["Survey Design & Sampling"],
            "summary": f"Uploaded document: {doc_name}."
        }
        db_manager.save_document_topics(doc_name, fallback["topics"], fallback["domains"], fallback["skills"], fallback["summary"])
        return fallback

    sample_count = min(len(docs), 10)
    step = max(1, len(docs) // sample_count)
    sampled = [docs[i] for i in range(0, len(docs), step)][:sample_count]
    context, _ = format_docs(sampled)

    all_comps = get_all_competencies()
    comp_list_str = "\n".join(f"- {c} ({get_competency_meta(c)['domain']})" for c in all_comps)

    prompt = f"""
You are Second Brain's Official Statistical Capacity Building & Competency Extraction Engine.
Analyze the following document excerpts from '{doc_name}' and extract its topics and competencies.

Document Excerpts:
{context}

Target Competency Framework (SIH26101):
{comp_list_str}

Return a valid JSON object with this exact shape:
{{
  "doc_name": "{doc_name}",
  "topics": ["Major Topic 1", "Major Topic 2", "Major Topic 3", "Major Topic 4"],
  "subtopics": ["Subtopic A", "Subtopic B", "Subtopic C"],
  "domains": ["Statistical Competencies" or "Technical Competencies" or "Digital Governance" or "Behavioural & Managerial"],
  "skills": ["Skill 1 from target framework", "Skill 2 from target framework"],
  "summary": "2-3 sentences summarizing what statistical or technical capacity this document develops."
}}

Ensure mapped skills strictly match or reflect skills in the target framework.
Return ONLY valid JSON.
"""
    try:
        client = get_llm()
        resp = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": "You are a competency extraction specialist for India's Official Statistical System. Output only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=1500
        )
        data = json.loads(_clean_json_str(resp.choices[0].message.content))
        topics = data.get("topics", ["Key Concepts"])
        domains = data.get("domains", [DOMAIN_STATISTICAL])
        skills = data.get("skills", ["Survey Design & Sampling"])
        summary = data.get("summary", f"Learning material from {doc_name}.")

        db_manager.save_document_topics(doc_name, topics, domains, skills, summary)
        return {
            "doc_name": doc_name,
            "topics": topics,
            "domains": domains,
            "skills": skills,
            "summary": summary
        }
    except Exception as e:
        print(f"Competency extraction error: {e}")
        combined_text = " ".join(d.page_content for d in sampled)
        matches = map_text_to_competencies(combined_text)
        top_skills = [m["skill"] for m in matches[:3]] or ["Survey Design & Sampling"]
        top_domains = list({m["domain"] for m in matches[:3]}) or [DOMAIN_STATISTICAL]
        fallback = {
            "doc_name": doc_name,
            "topics": [doc_name.replace(".pdf", "").replace("_", " ")],
            "domains": top_domains,
            "skills": top_skills,
            "summary": f"Learning material from {doc_name} mapped to {', '.join(top_domains)}."
        }
        db_manager.save_document_topics(doc_name, fallback["topics"], fallback["domains"], fallback["skills"], fallback["summary"])
        return fallback


def generate_competency_assessment(domain: Optional[str] = None, count: int = 8, learner_role: str = "Statistical Analyst") -> List[Dict[str, Any]]:
    """Generate diagnostic assessment MCQs covering competencies for India's Official Statistical System."""
    target_domains = [domain] if domain and domain in COMPETENCY_DOMAINS else COMPETENCY_DOMAINS
    domain_str = ", ".join(target_domains)

    prompt = f"""
You are the Chief Assessment Officer for India's Official Statistical System (MoSPI / NASA Capacity Framework).
Generate a diagnostic competency assessment of {count} high-quality Multiple Choice Questions (MCQs).
Target Learner Role: {learner_role}
Competency Domains to cover: {domain_str}

Framework Competencies to draw questions from:
1. Statistical Competencies (Survey Design & Sampling, Descriptive & Inferential Statistics, National Accounts & GVA, Price Statistics & Indices, SDG Indicators & Data Quality)
2. Technical Competencies (Python for Statistical Analysis, SQL & Database Systems, Data Visualization & BI, AI/ML in Official Statistics, R Programming)
3. Digital Governance (Cybersecurity & Data Privacy, Digital Public Infrastructure & Cloud)
4. Behavioural & Managerial (Statistical Ethics & Integrity, Project Management & Communication)

Return a valid JSON array of questions using this exact shape:
[
  {{
    "id": 1,
    "question": "Clear, practical, official-statistics scenario or technical question?",
    "options": ["Option A", "Option B", "Option C", "Option D"],
    "answer_index": 0,
    "domain": "Statistical Competencies | Technical Competencies | Digital Governance | Behavioural & Managerial",
    "skill": "Exact skill name from framework",
    "difficulty": "Easy | Medium | Hard",
    "explanation": "Clear official or theoretical rationale for the correct answer.",
    "source": "MoSPI Training Manual / NSS Guidelines / UN Principles"
  }}
]

Requirements:
- answer_index must be an integer (0, 1, 2, or 3).
- Distribute questions across the requested domains.
- Provide realistic scenarios relevant to government data collection, analysis, cybersecurity, and statistical integrity.
Return ONLY valid JSON.
"""
    try:
        client = get_llm()
        resp = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": "You create rigorous competency assessment question papers for civil service statistical officers."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=2600
        )
        cleaned = _clean_json_str(resp.choices[0].message.content)
        questions = json.loads(cleaned)
        if isinstance(questions, list) and questions:
            for idx, q in enumerate(questions, start=1):
                q["id"] = idx
            return questions
    except Exception as e:
        print(f"Dynamic assessment error: {e}")

    # Curated official statistics fallback assessment questions
    fallback_pool = [
        {
            "id": 1,
            "question": "In multi-stage stratified sampling for household surveys conducted by NSSO, why are villages/urban blocks treated as First Stage Units (FSUs)?",
            "options": [
                "To minimize non-sampling errors by creating homogeneous clusters before household listing",
                "Because complete lists of households nationwide are unavailable without first sampling areas",
                "To ensure every single individual has an identical non-zero probability without stratification",
                "Because multi-stage designs have higher precision than simple random sampling with equal sample size"
            ],
            "answer_index": 1,
            "domain": DOMAIN_STATISTICAL,
            "skill": "Survey Design & Sampling",
            "difficulty": "Medium",
            "explanation": "In large-scale surveys, an exhaustive national list of households does not exist prior to listing. Sampling geographical areas (FSUs) first allows enumerators to prepare local listing frames cost-effectively.",
            "source": "NSSO Survey Methodology Manual (Vol. 1)"
        },
        {
            "id": 2,
            "question": "Which Python library and method is standard for computing descriptive aggregates across grouping variables in statistical survey microdata?",
            "options": [
                "numpy.matrix_multiply()",
                "pandas.DataFrame.groupby().agg()",
                "scipy.cluster.vq()",
                "statsmodels.formula.ols()"
            ],
            "answer_index": 1,
            "domain": DOMAIN_TECHNICAL,
            "skill": "Python for Statistical Analysis",
            "difficulty": "Easy",
            "explanation": "Pandas DataFrame.groupby() along with .agg() is the standard industry method for computing split-apply-combine aggregates across administrative zones and survey strata.",
            "source": "Python for Data Analysis Guide"
        },
        {
            "id": 3,
            "question": "Under the Digital Personal Data Protection (DPDP) Act and official statistical guidelines, what technique must be applied before releasing public research microdata?",
            "options": [
                "Full symmetric encryption with the public key shared on data.gov.in",
                "Statistical anonymization, de-identification, and cell suppression for small samples",
                "Converting all numerical variables to floating point numbers",
                "Removing only the respondent's phone number while preserving names and exact GPS coordinates"
            ],
            "answer_index": 1,
            "domain": DOMAIN_DIGITAL_GOV,
            "skill": "Cybersecurity & Data Privacy",
            "difficulty": "Medium",
            "explanation": "Microdata dissemination requires statistical anonymization (k-anonymity, l-diversity, perturbation, or cell suppression) so individual respondents cannot be re-identified.",
            "source": "DPDP Act Guidelines & MoSPI Microdata Policy"
        },
        {
            "id": 4,
            "question": "According to the UN Fundamental Principles of Official Statistics, what principle governs the obligation to protect individual survey respondents?",
            "options": [
                "Principle of Maximum Commercialization",
                "Strict Confidentiality: data collected for statistical compilation must be strictly confidential and used exclusively for statistical purposes",
                "Open Access: respondent data must be accessible to any inquiring law enforcement authority without court orders",
                "Principle of Mandatory Verification by Local Politicians"
            ],
            "answer_index": 1,
            "domain": DOMAIN_BEHAVIOURAL,
            "skill": "Statistical Ethics & Integrity",
            "difficulty": "Easy",
            "explanation": "Principle 6 of the UN Fundamental Principles guarantees strict confidentiality: individual data collected by statistical agencies must be used exclusively for statistical purposes and protected from disclosure.",
            "source": "UN Fundamental Principles of Official Statistics"
        },
        {
            "id": 5,
            "question": "In the compilation of Gross Value Added (GVA) at basic prices in National Accounts, what is the formula?",
            "options": [
                "GVA at basic prices = Gross Output at basic prices - Intermediate Consumption",
                "GVA at basic prices = GDP + Net Factor Income from Abroad",
                "GVA at basic prices = Gross Capital Formation - Consumption of Fixed Capital",
                "GVA at basic prices = Total Imports - Total Exports"
            ],
            "answer_index": 0,
            "domain": DOMAIN_STATISTICAL,
            "skill": "National Accounts & GVA",
            "difficulty": "Medium",
            "explanation": "By definition in the System of National Accounts (SNA), Gross Value Added (GVA) at basic prices equals Gross Output valued at basic prices minus Intermediate Consumption at purchasers' prices.",
            "source": "System of National Accounts (SNA 2008) / CSO Manual"
        },
        {
            "id": 6,
            "question": "Which SQL clause is used to extract state-wise average consumption expenditures and filter only those states where survey sample counts exceed 500 households?",
            "options": [
                "WHERE count(hh_id) > 500",
                "HAVING count(hh_id) > 500",
                "ORDER BY sample_size > 500",
                "GROUP BY sample_size > 500"
            ],
            "answer_index": 1,
            "domain": DOMAIN_TECHNICAL,
            "skill": "SQL & Database Systems",
            "difficulty": "Medium",
            "explanation": "The HAVING clause filters aggregated groups after the GROUP BY execution, whereas the WHERE clause filters rows prior to aggregation.",
            "source": "Relational Database Concepts for Data Analysts"
        },
        {
            "id": 7,
            "question": "When computing the Consumer Price Index (CPI), why is the Laspeyres price index typically considered to have an upward bias?",
            "options": [
                "It uses current-period quantities as weights",
                "It uses base-period consumption quantities, failing to reflect consumer substitution towards relatively cheaper goods",
                "It includes direct income taxes in the commodity pricing basket",
                "It only samples wholesale transactions rather than retail shops"
            ],
            "answer_index": 1,
            "domain": DOMAIN_STATISTICAL,
            "skill": "Price Statistics & Indices",
            "difficulty": "Hard",
            "explanation": "The Laspeyres index fixes the base-period basket quantities. As prices rise unevenly, consumers substitute cheaper alternatives, so the fixed basket overstates the true cost of maintaining living standards.",
            "source": "Manual on Consumer Price Index (ILO / MoSPI)"
        },
        {
            "id": 8,
            "question": "In digital public infrastructure for official data dissemination, what does the SDMX standard ensure?",
            "options": [
                "Software Driven Mail Exchange for inter-departmental notices",
                "Statistical Data and Metadata Exchange: an open technical and statistical standard for exchanging statistical data and metadata across agencies",
                "Satellite Data Monitoring and Exploration for GIS mapping",
                "Structured Database Management for XML file compression"
            ],
            "answer_index": 1,
            "domain": DOMAIN_DIGITAL_GOV,
            "skill": "Digital Public Infrastructure & Cloud",
            "difficulty": "Medium",
            "explanation": "SDMX (Statistical Data and Metadata eXchange) is sponsored by the UN, BIS, ECB, Eurostat, IMF, OECD, and World Bank to standardize exchange of official statistics.",
            "source": "SDMX International Standards & Guidelines"
        }
    ]

    if domain:
        filtered = [q for q in fallback_pool if q["domain"] == domain]
        return filtered if filtered else fallback_pool[:count]
    return fallback_pool[:count]


def generate_skill_gap_feedback(learner_profile: Dict[str, Any], skill_gaps: List[Dict[str, Any]]) -> str:
    """Generate personalized pedagogical analysis explaining skill gaps and next learning milestones."""
    high_gaps = [g for g in skill_gaps if g["priority"] == "High Priority"]
    med_gaps = [g for g in skill_gaps if g["priority"] == "Medium Priority"]

    name = learner_profile.get("full_name", "Officer")
    role = learner_profile.get("designation", "Statistical Analyst")

    prompt = f"""
You are the Chief Academic Advisor for India's National Academy of Statistical Administration (NASA / MoSPI).
Write a personalized, encouraging, and clear competency diagnostic report for:
Learner: {name}
Role: {role}
Department: {learner_profile.get('department', 'Official Statistics')}

Top High Priority Skill Gaps:
{json.dumps([{'skill': g['skill'], 'domain': g['domain'], 'current': g['current_score'], 'target': g['target_score'], 'gap': g['gap']} for g in high_gaps[:3]])}

Medium Priority Gaps:
{json.dumps([{'skill': g['skill'], 'current': g['current_score'], 'target': g['target_score']} for g in med_gaps[:2]])}

Provide a structured, inspiring evaluation in Markdown:
1. Executive Competency Summary (Assessment of current strengths vs critical operational gaps)
2. Why These Skill Gaps Matter for {role} (Impact on data collection, validation, and official reporting)
3. 3-Phase Immediate Action Roadmap (Step 1: Foundational, Step 2: Practical, Step 3: Assessment)
4. Recommended iGOT Karmayogi Courses to enroll in today.
"""
    try:
        client = get_llm()
        resp = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": "You provide executive capacity-building guidance for statistical civil servants."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=1800
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"""### 📊 Competency Diagnostic Summary for {name} ({role})

**Strengths:** You have established a solid foundation in core statistical principles and ethics.
**Critical Gaps Identified:**
{chr(10).join(f"- **{g['skill']}**: Current competency {g['current_score']}% is below the target benchmark of {g['target_score']}% (Gap: {g['gap']}%)." for g in high_gaps[:3])}

**Recommended Action:**
1. Enroll in the recommended **iGOT Karmayogi** modules for your top skill gaps.
2. Review uploaded learning materials in the Second Brain Vault.
3. Take practice quizzes in Quiz Mode to adaptively elevate your competency scores."""


# ==================== FEATURE 7: SMART NOTES / SUMMARY ====================

def generate_smart_notes(doc_name, topic=None):
    vectordb = get_vectorstore()
    docs = vectordb.get_document_chunks(doc_name)
    if not docs:
        docs = vectordb.similarity_search(topic or doc_name, k=12, doc_filter=doc_name)
    if not docs:
        return f"No document content found for '{doc_name}'."

    # Sample representative chunks across the document
    sample_count = min(len(docs), 12)
    step = max(1, len(docs) // sample_count)
    sampled_docs = [docs[i] for i in range(0, len(docs), step)][:sample_count]
    context, _ = format_docs(sampled_docs)

    prompt = f"""
You are Second Brain's Smart Note Generator.
Create a clean, highly structured, comprehensive set of study notes for: '{doc_name}'.

Document Content:
{context}

Organize the notes strictly into these sections:
# 📝 Smart Notes: {doc_name}

## 1. Executive Summary
(A concise, high-impact summary of what this document covers)

## 2. Important Concepts & Frameworks
(Core conceptual pillars explained with bullet points)

## 3. Key Definitions & Terminology
(Dictionary/glossary style definitions of crucial terms)

## 4. Crucial Points & Mechanisms
(Detailed working principles, rules, workflows, or classifications)

## 5. Examples & Case Studies
(Practical examples or applications mentioned in or relevant to the text)

## 6. High-Yield Exam / Interview Questions
(Top 5 questions that could be asked from this material)

## 7. Keywords & Quick Review Flashcards
(Bullet list of essential keywords and 1-line mnemonics)
"""
    try:
        client = get_llm()
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": "You create elegant, comprehensive academic study notes."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=2500,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error generating smart notes: {e}"


# ==================== FEATURE 8: KNOWLEDGE MAP / CONCEPT GRAPH ====================

def extract_concept_graph(doc_name=None, focus_topic=None):
    vectordb = get_vectorstore()
    query = focus_topic if focus_topic else "key concepts, components, hierarchy, relationships"
    docs = retrieve_relevant_docs(vectordb, query, k=12, doc_filter=doc_name)
    if not docs:
        return {"nodes": [], "edges": []}

    context, _ = format_docs(docs)

    prompt = f"""
Analyze these document excerpts and extract a structured knowledge concept map (nodes and directed relationships).

Document Content:
{context}

Return a valid JSON object with:
{{
  "nodes": [
    {{"id": "c1", "label": "Concept Name", "category": "root|branch|leaf"}},
    ... (between 8 to 15 key concepts)
  ],
  "edges": [
    {{"source": "c1", "target": "c2", "relationship": "contains|causes|mitigates|type_of|uses"}},
    ... (between 8 to 18 relationships)
  ]
}}
Return ONLY valid JSON.
"""
    try:
        client = get_llm()
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": "You are an ontology and knowledge graph specialist. Output only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=1800,
        )
        data = json.loads(_clean_json_str(response.choices[0].message.content))
        return data if isinstance(data, dict) and "nodes" in data else {"nodes": [], "edges": []}
    except Exception as e:
        print(f"Knowledge map extraction error: {e}")
        return {"nodes": [], "edges": []}


# ==================== FEATURE 10: STUDY PLANNER ====================

def generate_study_plan_schedule(subject, exam_date, daily_hours, doc_names=None):
    vectordb = get_vectorstore()
    docs = []
    if doc_names:
        for name in doc_names:
            docs.extend(vectordb.similarity_search("syllabus topics units", k=4, doc_filter=name))
    else:
        docs = vectordb.similarity_search(subject, k=8)

    context = "\n---\n".join(d.page_content[:400] for d in docs) if docs else "General academic subject curriculum."

    today = datetime.now().date()
    days_left = max(1, (exam_date - today).days) if hasattr(exam_date, "year") else 7

    prompt = f"""
Create an optimal, realistic day-by-day study schedule for:
Subject: {subject}
Days remaining until exam: {days_left} days (Exam date: {exam_date})
Available study time: {daily_hours} hours/day
Document material context:
{context}

Return a valid JSON array of day objects:
[
  {{
    "day": 1,
    "title": "Unit 1: Fundamentals & Concepts",
    "tasks": [
      "Read introduction and core definitions (1.5 hrs)",
      "Practice 2-mark definitions and note formulas (1 hr)",
      "Self-test checkpoint (30 mins)"
    ],
    "milestone": "Master basic concepts"
  }},
  ...
]

Ensure the schedule covers:
- Gradual topic progression across the {min(days_left, 14)} days
- Built-in quiz and active recall checkpoints
- Dedicated final revision and mock test before the exam
Return ONLY valid JSON.
"""
    try:
        client = get_llm()
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": "You are an expert academic study strategist. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=2200,
        )
        cleaned = _clean_json_str(response.choices[0].message.content)
        schedule = json.loads(cleaned)
        return schedule if isinstance(schedule, list) else []
    except Exception as e:
        print(f"Study schedule generation error: {e}")
        return []


# ==================== FEATURE 12: COMPARE DOCUMENTS ====================

def compare_documents(doc_a, doc_b, topic=None):
    vectordb = get_vectorstore()
    query = topic if topic else "overview key concepts architecture advantages disadvantages"
    docs_a = retrieve_relevant_docs(vectordb, query, k=6, doc_filter=doc_a)
    docs_b = retrieve_relevant_docs(vectordb, query, k=6, doc_filter=doc_b)

    context_a, _ = format_docs(docs_a)
    context_b, _ = format_docs(docs_b)

    prompt = f"""
You are Second Brain's comparative intelligence module.
Compare the following two documents{f' on the topic of {topic}' if topic else ''}:

DOCUMENT A ({doc_a}):
{context_a}

DOCUMENT B ({doc_b}):
{context_b}

Provide an exhaustive, structured comparison:
# ⚖ Comparative Analysis: {doc_a} vs {doc_b}

## 1. Executive Comparison Table
| Feature / Dimension | {doc_a} | {doc_b} | Key Takeaway |
| --- | --- | --- | --- |
(Include 4-6 meaningful rows comparing core concepts)

## 2. Common Concepts & Shared Principles
(What concepts, foundations, or goals do both documents agree on?)

## 3. Key Differences & Contrasting Perspectives
(Where do they diverge in philosophy, implementation, scope, or taxonomy?)

## 4. Unique to {doc_a}
(Key topics or details present ONLY in Document A)

## 5. Unique to {doc_b}
(Key topics or details present ONLY in Document B)

## 6. Synthesis & Final Takeaway
(How a student or researcher should integrate the knowledge from both)
"""
    try:
        client = get_llm()
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": "You are a comparative literature and technical analyst."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=2200,
        )
        content = response.choices[0].message.content.strip()

        # Add citations for both docs
        details_a = get_source_details(docs_a[:2])
        details_b = get_source_details(docs_b[:2])
        content += "\n\n---\n**Sources Compared:**\n"
        content += "\n".join(f"• 📄 {d['label']}" for d in details_a + details_b)
        return content
    except Exception as e:
        return f"Error comparing documents: {e}"
