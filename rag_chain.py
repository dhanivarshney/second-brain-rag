"""Strict, evidence-only question answering over the local document index."""

import json
import os
import re

import httpx
from dotenv import load_dotenv
from groq import Groq
from langchain_core.prompts import PromptTemplate

from ingest import get_vectorstore

load_dotenv()

LLM_MODEL = "openai/gpt-oss-120b"
RETRIEVAL_K = 12
NOT_FOUND_MESSAGE = "I could not find this information in the uploaded PDF(s)."

PROMPT_TEMPLATE = """
You are Second Brain, a strict PDF-grounded assistant.

Answer the current question using ONLY facts explicitly supported by the
uploaded-document excerpts below. Do not use general knowledge, guesses,
assumptions, or facts from the conversation as evidence. Conversation history
may only help interpret a short follow-up question.

If the excerpts do not contain the answer, or contain only part of it, say
exactly: "I could not find this information in the uploaded PDF(s)."
Then, if useful, state the narrow part that is supported. Never fill missing
parts with outside knowledge.

Match the user's language and requested level of detail. Do not invent page
numbers, quotes, citations, examples, or document content.

Return only valid JSON, with no Markdown fences, using this exact shape:
{{"answer": "your answer", "evidence": [{{"source_id": 1, "quote": "an exact copied quote from the excerpt"}}]}}
Every answer claim must be supported by the evidence. Each `quote` must be a
verbatim copy from its `source_id` excerpt and must directly support the
answer. Build the answer only from the quoted evidence; do not take facts from
another searched excerpt and cite a different page. Do not cite a page merely
because it was searched. If the answer is not fully supported, return exactly:
{{"answer": "I could not find this information in the uploaded PDF(s).", "evidence": []}}

Conversation history (interpretation only):
{history}

PDF excerpts searched for this question:
{context}

Current question:
{question}
"""


def get_llm():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY is not set in the .env file.")
    return Groq(api_key=api_key, http_client=httpx.Client(trust_env=False, timeout=45.0))


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
        excerpts.append(f"[SOURCE_ID: {source_id}; PDF: {filename}; page: {display_page}]\n{text}")
    return "\n\n".join(excerpts), source_by_id


def is_greeting(query):
    """Greetings have no document claim to verify, so always refuse them."""
    normalised = re.sub(r"[^a-z\s]", "", query.lower()).strip()
    return normalised in {
        "hi", "hii", "hiii", "hello", "hey", "hola", "namaste", "namaskar",
        "good morning", "good afternoon", "good evening", "hi there", "hello there",
    }


def get_source_details(docs):
    """Return the unique document pages actually supplied to the model."""
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
    for message in chat_history[-10:]:
        content = message.get("content", "").strip()
        if content:
            role = "User" if message.get("role") == "user" else "Assistant"
            parts.append(f"{role}: {content}")
    return "\n".join(parts)


def create_retrieval_query(query, history_text):
    if not history_text:
        return query
    return f"Previous conversation:\n{history_text[-500:]}\n\nCurrent question:\n{query}"


def retrieve_relevant_docs(vectordb, retrieval_query, k=RETRIEVAL_K):
    try:
        return vectordb.similarity_search(retrieval_query, k=k)
    except Exception as error:
        print(f"Retrieval error: {error}")
        return []


def _normalise_evidence(text):
    return " ".join(text.split()).casefold()


def parse_grounded_response(raw_answer, source_by_id):
    """Accept an answer only when each cited quote exists on its shown page."""
    try:
        cleaned = raw_answer.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else ""
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3].strip()
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
                raise ValueError("Invalid evidence item")
            source_id = int(item.get("source_id"))
            quote = item.get("quote", "").strip()
            document = source_by_id.get(source_id)
            if not document or len(_normalise_evidence(quote)) < 8:
                raise ValueError("Missing evidence quote")
            if _normalise_evidence(quote) not in _normalise_evidence(document.page_content):
                raise ValueError("Evidence quote does not exist in the cited excerpt")
            verified_evidence.append((source_id, quote))

        selected_docs = [source_by_id[source_id] for source_id, _ in dict.fromkeys(verified_evidence)]
        details = get_source_details(selected_docs)
        details_by_page = {(detail["source"], detail["page"]): detail for detail in details}
        for source_id, quote in verified_evidence:
            document = source_by_id[source_id]
            detail = details_by_page[(document.metadata.get("source", "unknown"), document.metadata.get("page", "N/A"))]
            if quote not in detail["evidence"]:
                detail["evidence"].append(quote)
        return answer, details
    except (ValueError, TypeError, json.JSONDecodeError):
        return NOT_FOUND_MESSAGE, []


def ask_question(query, chat_history=None, k=RETRIEVAL_K):
    query = query.strip()
    if not query:
        return {"answer": "Please enter a question.", "sources": [], "source_details": []}
    if is_greeting(query):
        return {"answer": NOT_FOUND_MESSAGE, "sources": [], "source_details": []}

    history_text = format_chat_history(chat_history)
    try:
        vectordb = get_vectorstore()
        docs = retrieve_relevant_docs(vectordb, create_retrieval_query(query, history_text), k=k)
    except Exception as error:
        print(f"Vector database error: {error}")
        docs = []

    if not docs:
        return {"answer": NOT_FOUND_MESSAGE, "sources": [], "source_details": []}

    context, source_by_id = format_docs(docs)

    final_prompt = PromptTemplate(
        input_variables=["history", "context", "question"], template=PROMPT_TEMPLATE
    ).format(history=history_text, context=context, question=query)

    try:
        client = get_llm()
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": "Never use knowledge outside the supplied PDF excerpts. If evidence is missing, use the required refusal sentence."},
                {"role": "user", "content": final_prompt},
            ],
            temperature=0,
            max_tokens=1800,
        )
        answer = response.choices[0].message.content.strip()
    except Exception as error:
        return {
            "answer": f"Sorry, an error occurred while generating the answer:\n\n{error}",
            "sources": [],
            "source_details": [],
        }

    answer, source_details = parse_grounded_response(answer, source_by_id)
    return {"answer": answer, "sources": [detail["label"] for detail in source_details], "source_details": source_details}


if __name__ == "__main__":
    print(ask_question("What is the main topic?"))
