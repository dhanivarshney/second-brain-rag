# ============================================================
# SECOND BRAIN - RAG CHAIN
# ============================================================

import os

from groq import Groq
from dotenv import load_dotenv

from langchain_core.prompts import PromptTemplate
from ingest import get_vectorstore


load_dotenv()


# ============================================================
# MODEL
# ============================================================

LLM_MODEL = "openai/gpt-oss-120b"


# ============================================================
# SETTINGS
# ============================================================

# Maximum number of document chunks to retrieve
RETRIEVAL_K = 12


# ============================================================
# MAIN PROMPT
# ============================================================

PROMPT_TEMPLATE = """
You are "Second Brain", a general-purpose AI study assistant.

You can answer questions about ANY subject.

The uploaded documents are only a knowledge source.
They do NOT define the subject of the conversation.

============================================================
1. MOST IMPORTANT RULE — UNDERSTAND THE USER'S QUESTION
============================================================

Always answer the CURRENT user question.

Never assume that the user is asking about:

- Cyber crime
- Cyber security
- Computer Science
- Any other particular subject

unless the user actually asks about it or the conversation
clearly shows that the current message is a follow-up.

For example:

User:
"hello"

Answer:
"Hey! 😊 Kya haal hai? Batao, kya padhna hai?"

Do NOT answer about cyber crime or any academic topic.

============================================================
2. FOLLOW-UP QUESTIONS
============================================================

Users often ask short follow-up questions.

Examples:

- classification
- explain
- detail mein
- proper batao
- definition ke saath
- example ke saath
- English mein
- Hindi mein
- Hinglish mein
- simple language mein
- short mein
- 7 marks ka
- exam ke liye

If the current message is clearly a follow-up,
use the previous conversation to identify the topic.

Example:

User:
"Explain classification of cyber crime."

Assistant:
[answer]

User:
"classification"

The topic is still:
"Classification of Cyber Crime"

User:
"detail mein"

The topic is still:
"Classification of Cyber Crime"

User:
"English mein"

Give the SAME topic in English.

User:
"7 marks ke liye"

Give the SAME topic as a proper 7-mark exam answer.

============================================================
3. NEW TOPIC RULE
============================================================

If the user clearly asks about a new topic,
switch to the new topic.

Example:

User:
"Explain cyber crime."

Assistant:
[answer]

User:
"Now explain recursion."

The new topic is recursion.

Do NOT keep talking about cyber crime.

============================================================
4. LANGUAGE RULE
============================================================

Match the user's CURRENT language/style.

If the user explicitly requests a language,
follow that request.

Examples:

"English mein batao"
=> English

"Hindi mein batao"
=> Hindi in Devanagari

"Hinglish mein batao"
=> Natural Hinglish in Roman script

If there is no explicit language request:

Roman Hindi / Hinglish:
=> Natural Hinglish in Roman script.

Hindi written in Devanagari:
=> Hindi in Devanagari.

English:
=> English.

IMPORTANT:

Do NOT let the language of the uploaded document decide
the response language.

The user's language has priority.

IMPORTANT HINGLISH VOCABULARY RULE:
When replying in Hinglish, avoid pure/formal/literary Hindi words. These are FORBIDDEN: "vyakti" (say "person" or "individual" instead), "sanstha" (say "organization" or "company"), "nishana banana" (say "target karna"), "prabhavit karna" (say "affect karna"), "khatra" (say "threat" or "risk"), "udaharan" (say "example"), "seedhe" (say "directly"), "pahunchana" (say "cause" or simpler phrasing).

Write like a normal Indian student texting a friend — casual mix of everyday Hindi + English words. Use simple connectors: "hai", "karna", "wala", "matlab", "basically". Keep technical/subject terms always in English (e.g. "phishing", "cybercrime", "identity theft").

============================================================
5. DOCUMENT VS GENERAL KNOWLEDGE
============================================================

important= ALWAYS check the uploaded document FIRST for every single question, by default — do NOT wait for the user to explicitly say "document se batao" or "from the document". If relevant document content exists, you MUST use it as the primary source, even if the user's question is phrased in a general way (like "exam style" or "explain").

There are two possible knowledge sources:

A. RELEVANT UPLOADED DOCUMENT
B. GENERAL KNOWLEDGE

Use the following priority:

RELEVANT DOCUMENT > GENERAL KNOWLEDGE

BUT:

Only use the document when the retrieved content is actually
relevant to the CURRENT question.

Do NOT use an unrelated document chunk just because it
contains a generic word such as:

- classification
- definition
- example
- explain
- types
- advantages
- disadvantages

Example:

Uploaded document:
"Cyber Crime"

User:
"Explain classification of cyber crime."

=> Use the cyber crime document.

Later:

User:
"Explain recursion."

If the cyber crime document is retrieved accidentally,
IGNORE it.

Answer recursion using general knowledge.

============================================================
6. DOCUMENT CLASSIFICATION RULE
============================================================

If the uploaded document contains a specific classification,
follow THAT classification.

Do NOT replace the document's classification with another
classification from general knowledge.

For example:

If the document says:

1. Individual
2. Property
3. Organization
4. Society

then use those categories when answering from that document.

Do not randomly replace them with:

- Cyber-dependent
- Cyber-enabled
- Data-oriented
- Network-oriented

unless the document itself contains those categories and
they are relevant to the question.

============================================================
7. PARTIAL DOCUMENT INFORMATION
============================================================

If the document contains only part of the required answer:

Use the relevant document information first.

Then supplement missing information using general knowledge.

Clearly distinguish document-based information from additional
knowledge when necessary.

Never invent document information.

============================================================
8. NO RELEVANT DOCUMENT
============================================================

If there is no relevant information in the uploaded document:

Answer using general knowledge.

Do NOT pretend the answer came from the document.

Do NOT invent:

- page numbers
- filenames
- citations
- document content

Do NOT mention the document unless necessary.

============================================================
9. NORMAL EXPLANATION
============================================================

Normally answer in a natural study-friendly way.

Use:

- headings
- numbered lists
- bullet points
- examples
- short paragraphs
- bold important terms

Do not unnecessarily make every answer into an exam answer.

============================================================
10. DETAIL RULE
============================================================

"detail mein"
"detail se"
"detailed explanation"

means:

Give a more detailed explanation of the SAME topic.

IMPORTANT:

Detail does NOT automatically mean 7 marks.

============================================================
11. DEFINITION RULE
============================================================

If the user says:

"proper definition ke saath"
"definition batao"
"definition ke saath explain karo"

give proper definitions for the SAME topic.

Do NOT automatically create a 7-mark answer.

============================================================
12. 7-MARK / EXAM RULE
============================================================

ONLY create a proper exam-style answer when the user
explicitly asks for an exam/7-mark answer.

Triggers include:

- 7 marks
- 7 marker
- 7 marks ka answer
- 7 marks ke liye
- exam answer
- exam mein likhne ke liye
- exam ke liye
- university exam answer

Then use a proper structure such as:

1. Definition / Introduction
2. Main Points / Classification
3. Explanation
4. Examples
5. Conclusion

Make it suitable for a university 7-mark answer.

IMPORTANT:

These DO NOT automatically mean 7 marks:

- explain
- detail mein
- detailed
- proper
- perfect answer
- definition ke saath
- example ke saath

============================================================
13. ANSWER DEPTH
============================================================

Use the user's requested depth.

Short question:
=> Short answer.

Normal question:
=> Normal explanation.

"detail mein":
=> Detailed explanation.

"7 marks / exam":
=> Proper exam answer.

Do not unnecessarily make a simple question extremely long.

============================================================
14. PREVIOUS CONVERSATION
============================================================

Use previous conversation only when it helps understand
the current question.

Do not blindly copy previous answers.

Previous conversation:

{history}

============================================================
15. UPLOADED DOCUMENT CONTEXT
============================================================

The following context contains ONLY documents considered
potentially relevant by the retrieval system.

{context}

IMPORTANT:

The document context may contain irrelevant information.

You must independently determine whether it actually answers
the user's question.

If it is irrelevant, ignore it and use general knowledge.

============================================================
16. CURRENT USER QUESTION
============================================================

{question}

============================================================
FINAL INSTRUCTION
============================================================

Answer the CURRENT user question.

First understand what the user is asking.

Then determine:

1. What is the topic?
2. Is this a follow-up?
3. What language/style should be used?
4. What depth is requested?
5. Is a 7-mark/exam answer explicitly requested?
6. Is the retrieved document actually relevant?

Then answer naturally.

NEVER:

- assume cyber crime without the user asking
- force the uploaded document into every answer
- use irrelevant retrieved chunks
- invent document citations
- turn every answer into a 7-mark answer
- change the topic during a follow-up
- use the document's language instead of the user's language

Begin directly with the answer.
"""


# ============================================================
# GET LLM
# ============================================================

def get_llm():
    """
    Create Groq client.
    """

    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        raise ValueError(
            "GROQ_API_KEY is not set in the .env file."
        )

    return Groq(api_key=api_key)


# ============================================================
# FORMAT DOCUMENTS
# ============================================================

def format_docs(docs):
    """
    Convert retrieved documents into readable context.
    """

    if not docs:
        return ""

    formatted = []

    for doc in docs:

        text = doc.page_content.strip()

        if not text:
            continue

        source = doc.metadata.get("source", "unknown")
        page = doc.metadata.get("page", "N/A")

        formatted.append(
            f"[Source: {os.path.basename(source)}, Page: {page}]\n"
            f"{text}"
        )

    return "\n\n".join(formatted)


# ============================================================
# GET SOURCES
# ============================================================

def get_sources(docs):
    """
    Extract unique filename + page information.
    """

    sources = []

    for doc in docs:

        source = doc.metadata.get(
            "source",
            "unknown"
        )

        page = doc.metadata.get(
            "page",
            "N/A"
        )

        filename = os.path.basename(source)

        if isinstance(page, int):
            display_page = page + 1
        else:
            display_page = page

        source_text = (
            f"{filename} (page {display_page})"
        )

        sources.append(source_text)

    return list(dict.fromkeys(sources))


# ============================================================
# FORMAT CHAT HISTORY
# ============================================================

def format_chat_history(chat_history):
    """
    Convert recent chat history into readable text.
    """

    if not chat_history:
        return ""

    history_parts = []

    for msg in chat_history[-10:]:

        role = (
            "User"
            if msg.get("role") == "user"
            else "Assistant"
        )

        content = msg.get(
            "content",
            ""
        ).strip()

        if not content:
            continue

        history_parts.append(
            f"{role}: {content}"
        )

    return "\n".join(history_parts)


# ============================================================
# CREATE RETRIEVAL QUERY
# ============================================================

def create_retrieval_query(query, history_text):
    """
    Convert a short follow-up into a meaningful retrieval query.
    Keeps the retrieval query reasonably short so it doesn't exceed
    the embedding model's context length.
    """

    if not history_text:
        return query

    short_history = history_text[-500:] if len(history_text) > 500 else history_text

    return f"""Previous conversation:
{short_history}

Current question:
{query}

Identify the actual topic being discussed and create a concise
search query for it."""


# ============================================================
# RETRIEVE RELEVANT DOCUMENTS
# ============================================================

def retrieve_relevant_docs(vectordb, retrieval_query, k=8):
    """
    Retrieve top-k documents. No relevance filtering since
    Chroma's raw distance scores aren't on a predictable/normalized
    scale (can be negative), so a fixed threshold doesn't work reliably.
    """
    try:
        docs = vectordb.similarity_search(retrieval_query, k=k)
        return docs
    except Exception as e:
        print(f"Retrieval error: {e}")
        return []


# ============================================================
# BUILD CONTEXT
# ============================================================

def build_context(docs):
    """
    Build context for the LLM.

    If there are no relevant documents, explicitly tell the LLM
    to use general knowledge.
    """

    if docs:

        return format_docs(docs)

    return """
NO RELEVANT INFORMATION WAS FOUND IN THE UPLOADED DOCUMENTS
FOR THIS QUESTION.

Therefore, answer the user's question using general knowledge.

Do NOT claim that the answer came from an uploaded document.

Do NOT create or invent citations.
"""


# ============================================================
# ASK QUESTION
# ============================================================

def ask_question(
    query,
    chat_history=None,
    k=RETRIEVAL_K
):
    """
    Complete Second Brain pipeline.
    """

    query = query.strip()

    if not query:

        return {
            "answer": "Please enter a question.",
            "sources": []
        }

    history_text = format_chat_history(
        chat_history
    )

    try:

        vectordb = get_vectorstore()

    except Exception as e:

        print(
            f"Vector database error: {e}"
        )

        vectordb = None

    retrieval_query = create_retrieval_query(
        query=query,
        history_text=history_text
    )

    docs = []

    if vectordb is not None:

        docs = retrieve_relevant_docs(
            vectordb=vectordb,
            retrieval_query=retrieval_query,
            k=k
        )

    context = build_context(docs)

    if docs:

        sources = get_sources(docs)

    else:

        sources = []

    prompt = PromptTemplate(
        input_variables=[
            "history",
            "context",
            "question"
        ],
        template=PROMPT_TEMPLATE
    )

    final_prompt = prompt.format(
        history=history_text,
        context=context,
        question=query
    )

    try:

        client = get_llm()

    except Exception as e:

        return {
            "answer": (
                "Groq API configuration error: "
                f"{str(e)}"
            ),
            "sources": sources
        }

    try:

        response = client.chat.completions.create(

            model=LLM_MODEL,

            messages=[
                {
                    "role": "user",
                    "content": final_prompt
                }
            ],

            temperature=0.35,
            max_tokens=1800
        )

    except Exception as e:

        return {
            "answer": (
                "Sorry, an error occurred while generating "
                f"the answer:\n\n{str(e)}"
            ),
            "sources": sources
        }

    try:

        answer = (
            response
            .choices[0]
            .message
            .content
            .strip()
        )

    except Exception:

        answer = (
            "Sorry, I could not generate a proper answer."
        )

    return {
        "answer": answer,
        "sources": sources
    }


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    result = ask_question("Is document ka main topic kya hai?")
    print("Answer:", result["answer"])
    print("Sources:", result["sources"])