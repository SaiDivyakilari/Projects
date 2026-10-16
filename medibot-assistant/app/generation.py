from app.config import *
from app.retreival import Retrieval

from langchain_groq import ChatGroq

retriever = Retrieval()

llm = ChatGroq(**LLM_MODEL_CONFIG)


def generate_answer(query : str, role : str) -> str:
    docs = retriever.retrieve(query, role)

    if not docs:
        allowed = ", ".join(c for c, roles in ROLES.items() if role in roles)
        return f"As a {role}, I can only answer questions from the {allowed} collections.", []

    context = "\n\n".join(
        f"[{d.metadata['source_document']} - {d.metadata.get('section_title')}]\n{d.page_content}"
        for d in docs
    )

    prompt = f"""You are MediBot, an assistant for MediAssist hospital staff.
Answer the question using the context below.
Do not give the answer beyond the given context

Context:
{context}

Question: {query}

Answer:"""

    resp = llm.invoke(prompt)
    answer = resp.content
    print(resp.response_metadata.get("finish_reason"))
    print(answer)

    sources = [
        {
            "source_document": d.metadata["source_document"],
            "section_title": d.metadata.get("section_title"),
            "collection": d.metadata["collection"],
        }
        for d in docs
    ]

    return answer, sources


if __name__ == "__main__":
    for q, role in [
        ("How do I apply for annual leave?", "nurse"),
        ("Show me all insurance billing codes.", "nurse"),
    ]:
        answer, sources = generate_answer(q, role)
        print(f"\n[{role}] {q}\n{answer}")









