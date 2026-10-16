from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.auth import login, role_for_token, collections_for, SESSIONS
from app.config import DB_ROLES
from app.generation import generate_answer
from app.Text_to_SQL_RAG import sql_rag_chain

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class LoginRequest(BaseModel):
    username: str
    password: str


class ChatRequest(BaseModel):
    question: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/login")
def login_endpoint(request: LoginRequest):
    token = login(request.username, request.password)
    if not token:
        raise HTTPException(401, "Invalid username or password")

    role = role_for_token(token)
    return {"token": token, "role": role, "collections": collections_for(role)}


@app.get("/collections/{role}")
def collections_endpoint(role: str):
    return {"role": role, "collections": collections_for(role)}

@app.post("/chat")
def chat_endpoint(request: ChatRequest, authorization: str | None = Header(default=None, alias="Authorization")):
    token = authorization.replace("Bearer ", "") if authorization else ""
    role = role_for_token(token)

    if not role:
        raise HTTPException(401, "Invalid or expired token")

    question = request.question.lower()
    analytical = any(w in question for w in ["how many", "count", "total", "average", "most"])

    if analytical and role in DB_ROLES:
        answer = sql_rag_chain(request.question)
        return {"answer": answer, "sources": [], "retrieval_type": "sql_rag", "role": role}

    answer, sources = generate_answer(request.question, role)
    return {"answer": answer, "sources": sources, "retrieval_type": "hybrid_rag", "role": role}

