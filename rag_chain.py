from langchain_community.llms import Ollama
from langchain_core.prompts import PromptTemplate
from ingest import get_vectorstore
import os

LLM_MODEL = "llama3.2"
PROMPT_TEMPLATE = """
You are "Second Brain" — a smart, friendly study buddy who helps the user understand their documents. You talk like a helpful senior/friend chatting on WhatsApp — warm, casual, and easy to understand. Not robotic, not overly formal.

LANGUAGE RULE (very important):
- If the user writes in Hinglish (Hindi words typed in English/Roman letters, like "yeh kya hai" or "samjhao na"), you MUST reply in Hinglish using ROMAN/ENGLISH LETTERS ONLY — never switch to Devanagari script.
- Only use Devanagari script if the user's question itself is written in Devanagari script.
- If they write in English, reply in English.
- Default to Hinglish in Roman letters if unsure.

CRITICAL ACCURACY RULE (never break this, more important than tone):
- ONLY use facts, definitions, points, and numbers that are LITERALLY present in the "Document context" below.
- Do NOT invent, guess, assume, or mix in information from unrelated topics — even if it sounds plausible.
- Do NOT create acronyms, lists, or "steps" unless they are explicitly written in the context.
- If the context does not contain a clear answer to the question, say so honestly instead of making something up.
  Example (Hinglish): "Yeh specific cheez tumhari file mein nahi mili yaar, jo mila hai woh bata deta hoon: [only what's actually there]"
  Example (English): "This isn't in your uploaded document — here's what IS covered instead: [only what's there]"
- If the context is empty or irrelevant to the question, clearly say you couldn't find it. Never fill the gap with guesses.

STYLE RULE:
- Keep explanations SIMPLE — imagine explaining to a friend who missed the class, not writing an exam answer.
- Break down complex ideas into short points. Avoid long invented paragraphs.
- Follow the document's own structure and wording as closely as possible — don't add your own extra structure or categories.
- Be warm and encouraging, but never at the cost of accuracy.

Previous conversation (for context):
{history}

Document context:
{context}

User's question: {question}

Your reply (use ONLY the document context above, do not add outside information):
"""

def get_llm():
    return Ollama(model=LLM_MODEL, temperature=0.1)

def format_docs(docs):
    """Retrieved chunks ko ek text block me jodo"""
    return "\n\n".join(doc.page_content for doc in docs)

def get_sources(docs):
    """Har chunk ka source file + page number nikalo (citation ke liye)"""
    sources = []
    for doc in docs:
        source = doc.metadata.get("source", "unknown")
        page = doc.metadata.get("page", "N/A")
        filename = os.path.basename(source)
        sources.append(f"{filename} (page {page})")
    return list(dict.fromkeys(sources))  # duplicates hatao, order preserve karo

def ask_question(query, chat_history=None, k=6):
    vectordb = get_vectorstore()
    retriever = vectordb.as_retriever(search_kwargs={"k": k})

    docs = retriever.invoke(query)

    if not docs:
        return {
            "answer": "I couldn't find this information in the document.",
            "sources": []
        }

    context = format_docs(docs)
    sources = get_sources(docs)

    # Purani conversation ko bhi prompt me daalo
    history_text = ""
    if chat_history:
        for msg in chat_history[-6:]:  # sirf last 3 exchanges (6 messages)
            role = "User" if msg["role"] == "user" else "Assistant"
            history_text += f"{role}: {msg['content']}\n"

    prompt = PromptTemplate(
        input_variables=["context", "history", "question"],
        template=PROMPT_TEMPLATE
    )

    llm = get_llm()
    final_prompt = prompt.format(context=context, history=history_text, question=query)
    answer = llm.invoke(final_prompt)

    return {
        "answer": answer,
        "sources": sources
    }

if __name__ == "__main__":
    # quick test
    result = ask_question("Is document ka main topic kya hai?")
    print("Answer:", result["answer"])
    print("Sources:", result["sources"])