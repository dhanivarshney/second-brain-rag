"""Strict, evidence-grounded Document Intelligence & Study Assistant Engine."""

import json
import os
import re
from datetime import datetime

import httpx
from dotenv import load_dotenv
from groq import Groq
from langchain_core.prompts import PromptTemplate

import db_manager
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

def generate_quiz(topic_or_doc, count=5, doc_filter=None, k=12):
    vectordb = get_vectorstore()
    query = topic_or_doc if topic_or_doc else "key concepts, definitions, core topics"
    docs = retrieve_relevant_docs(vectordb, query, k=k, doc_filter=doc_filter)
    if not docs:
        return []

    context, _ = format_docs(docs)

    prompt = f"""
Create an interactive multiple-choice quiz of {count} questions testing understanding of: '{topic_or_doc}'.
Base the questions on the document excerpts provided.

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
    "topic": "Specific sub-topic or concept (e.g. SQL Injection, Buffer Overflow, Key Management)",
    "source": "Document filename or page"
  }}
]

Make sure answer_index is an integer from 0 to 3. Provide plausible distractors. Return ONLY valid JSON.
"""
    try:
        client = get_llm()
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": "You are a quiz master. Return only a valid JSON array of questions."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=2200,
        )
        cleaned = _clean_json_str(response.choices[0].message.content)
        quiz = json.loads(cleaned)
        return quiz if isinstance(quiz, list) else []
    except Exception as e:
        print(f"Quiz generation error: {e}")
        return []


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
