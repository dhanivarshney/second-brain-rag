from langchain_community.llms import Ollama
from langchain_core.prompts import PromptTemplate
from ingest import get_vectorstore

LLM_MODEL = "llama3.2"

PROMPT_TEMPLATE = """
You are a helpful assistant that answers questions based only on the given context.
Answer in the same language as the question was asked.
If the answer is not present in the context, say so clearly.
Do not make up any information.

Context:
{context}

Question: {question}

Answer:
"""

def get_llm():
    return Ollama(model=LLM_MODEL, temperature=0.3)

def format_docs(docs):
    """Retrieved chunks ko ek text block me jodo"""
    return "\n\n".join(doc.page_content for doc in docs)

def get_sources(docs):
    """Har chunk ka source file + page number nikalo (citation ke liye)"""
    sources = []
    for doc in docs:
        source = doc.metadata.get("source", "unknown")
        page = doc.metadata.get("page", "N/A")
        sources.append(f"{source} (page {page})")
    return list(set(sources))  # duplicates hatao

def ask_question(query, k=4):
    """
    Ye main function hai - app.py isko call karega.
    query -> relevant chunks fetch -> LLM se answer -> return answer + sources
    """
    vectordb = get_vectorstore()
    retriever = vectordb.as_retriever(search_kwargs={"k": k})

    # relevant chunks fetch karo
    docs = retriever.invoke(query)

    if not docs:
        return {
            "answer": "Koi relevant document nahi mila. Pehle kuch files upload karo.",
            "sources": []
        }

    context = format_docs(docs)
    sources = get_sources(docs)

    prompt = PromptTemplate(
        input_variables=["context", "question"],
        template=PROMPT_TEMPLATE
    )

    llm = get_llm()
    final_prompt = prompt.format(context=context, question=query)
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