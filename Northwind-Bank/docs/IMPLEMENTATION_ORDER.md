# Northwind-Bank — Step-by-Step Implementation Order



---

## 1 — Setup and infrastructure

1. **`requirements.txt`**: dependencies for FastAPI, LangGraph, boto3, Pinecone, psycopg,
   pdfplumber and LangSmith.
2. **`.env.example` → `.env`**: AWS region, S3 bucket, `DATABASE_URL`, Pinecone and
   LangSmith settings. Never commit `.env`.
3. **`app/config.py`**: model constants plus a `pydantic-settings` `Settings` class that loads
   `.env`, so the rest of the code imports `settings.DATABASE_URL` and never calls `os.getenv`
   directly.
4. **`infra/schema.sql`**: tables `documents` (with `min_role`, `superseded_by`, `status`),
   `chat_messages`, `approvals`, `feedback` and `audit_events`. Use `CREATE TABLE IF NOT EXISTS`.
5. **`app/db.py`**: a psycopg connection pool built from `DATABASE_URL`, plus small query
   helpers.
6. **`scripts/init_db.py`**: applies `schema.sql` to RDS and prints the tables it created.
7. **`app/aws.py`**: boto3 clients, S3 presigned PUT/GET URLs, `embed(text)` (Titan V2 via
   `invoke_model`) and `chat(messages)` (Nova 2 Lite via `converse`).
8. **`app/vector.py`**: create or connect to the Pinecone index (1024-d, cosine),
   `upsert(chunks)`, and `search(query_vec, role, k)` with the **`min_role` filter inside the
   query**.

## 2 — Document ingestion

9. **`scripts/seed_s3.py`**: uploads the 7 PDFs in `corpus/` to S3 and registers each one in
   `documents` with its `min_role` and `superseded_by`. For example, `NB-CMP-005` is
   compliance-only, and `NB-CIR-2026-04` supersedes parts of `NB-POL-001`.
10. **`worker/extract.py`**: `pdfplumber` with `layout=True`, returning text per page.
11. **`worker/chunker.py`**: splits on section headings first, then by size, and attaches
    `doc_id`, `section`, `page`, `min_role` and `superseded_by` to each chunk.
12. **`worker/ingest.py`**: S3 download → extract → chunk → embed → Pinecone upsert → set
    `documents.status = 'ready'`. A file in `worker/` doesn't run on its own. It's invoked in
    two ways:
    - **manually:** `python -m worker.ingest` re-ingests the whole corpus, using an
      `if __name__ == "__main__":` block.
    - **from the API:** after an upload, `/api/ingest` calls `ingest_document(doc_id)` as a
      FastAPI `BackgroundTask` (step 22).
13. **Retrieval check**: before any LLM code, run a few questions as each role and read the
    chunks that come back. Confirm a teller never gets `NB-CMP-005` chunks.

## 3 — RAG pipeline

14. **`app/rag.py`**: `retrieve(question, role)` embeds the question, calls the role-filtered
    search and applies **supersession**. If a chunk and the document that supersedes it both
    come back, keep the newer one. Also builds the prompt with citations (`doc_id` and
    section).
15. **`app/memory.py`**: saves and loads the last `MEMORY_TURNS` turns from `chat_messages`,
    per conversation.
16. **`app/guardrails.py`**: deterministic checks.
    - **Input:** prompt injection, out-of-scope questions, and attempts to get restricted
      content ("show me the AML thresholds").
    - **Output:** the answer must cite retrieved chunks, contain no content above the user's
      role and no PII patterns (account or card numbers).
17. **`app/graph.py`**: the LangGraph flow is input guardrail → load memory → retrieve +
    supersession → Nova generate → output guardrail → **HITL routing** → persist. When
    `HITL_ENABLED=true`, an answer that would trigger an action goes to `approvals` instead of
    to the user. Every request writes an `audit_events` row.

## 4 — Observability with LangSmith

18. **`app/observability.py`**: reads `LANGSMITH_TRACING`, `LANGSMITH_API_KEY` and
    `LANGSMITH_PROJECT`, and makes tracing optional (off when there's no key). Hide or
    truncate document text and user PII in traces.
19. **LangGraph nodes**: traced automatically once tracing is on. Nothing to add beyond clear
    node names.
20. **`app/aws.py`, `app/vector.py`, `worker/ingest.py`**: add `@traceable` to the Bedrock
    calls, the Pinecone search and the ingest stages, so you can see latency and errors per
    step.
21. **LangSmith dashboard**: send a few test questions and confirm one trace per request with
    all nodes in it. Check that no secrets appear in the trace data.

## 5 — FastAPI and user interface

22. **`app/schemas.py` + `app/main.py`**:
    - **Schemas:** Pydantic models for requests and responses.
    - **Routes:** presigned upload, ingest trigger, document list and status, chat, approvals
      (list/approve/reject), feedback, `/health/live`, `/health/ready` (DB check), and API
      docs at `/api/docs`.
    - **Role:** taken from the request, a simple header or a dropdown for now.
23. **`app/templates/index.html`**: views for chat, upload, documents, approvals and a
    **role selector**, so you can demo role isolation.
24. **`app/static/css/styles.css`**: layout, plus a fixed-height chat panel that scrolls
    vertically.
25. **`app/static/js/app.js`**: API calls, presigned PUT upload straight to S3, rendering chat
    with citations, approve and reject buttons, thumbs feedback, and auto-scroll to the newest
    message.

## 6 — Integration and evaluation

26. **Amazon S3 CORS**: allow `PUT` from `http://127.0.0.1:8000` and `http://localhost:8000`.
27. **`tests/`**: pytest unit tests that make no AWS calls.
    - **`test_chunker.py`:** sections and metadata are correct.
    - **`test_guardrails.py`:** injection and restricted requests are blocked.
    - **`test_rag.py`:** supersession logic, and the role filter is always passed to the
      search (mock Pinecone).
28. **`eval/gold_set.jsonl`**: about 20 labelled questions, each with the asker's role, the
    expected `doc_id`/section, and a few deliberate role-leak and supersession traps.
29. **`eval/scorers.py` + `eval/run.py`**: context recall, faithfulness, **role-leak rate (must
    be 0)** and supersession accuracy. Add a `--retrieval-only` mode, and exit non-zero when a
    threshold is missed.

## 7 — Packaging and deployment

30. **`Dockerfile`, `.dockerignore`, `docker-compose.yml`**: run the app in a container
    locally, with `.env` passed in at runtime and never copied into the image.
31. **`.github/workflows/deploy.yml`**: tests → eval gate → docker build → push to ECR (tagged
    with the commit SHA) → deploy to EC2 through SSM. Authenticate with **GitHub OIDC**, not
    stored keys.
32. **AWS production setup**: an IAM role for OIDC, an EC2 instance profile, secrets in
    **Secrets Manager**, RDS moved to a private subnet, and logs in CloudWatch. Add the
    deployed URL to the S3 CORS rule.
33. **`docs/SETUP.md`, `docs/ARCHITECTURE.md`, `docs/DEPLOYMENT.md`**: update them as each
    piece goes from *planned* to working.

## 8 — End-to-end demonstration

34. **Full run**:
    1. Run `init_db`, then `seed_s3`, then ingest.
    2. Start FastAPI.
    3. Ask questions as a **teller** and as **compliance**; the AML content shows only for
       compliance.
    4. Ask a personal-loan question; the answer follows the 2026 circular.
    5. Test memory, guardrails and HITL approval.
    6. Check the traces in LangSmith and run `eval.run` as the final gate.
