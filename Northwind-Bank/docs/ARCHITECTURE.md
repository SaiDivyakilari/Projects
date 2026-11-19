# Northwind Bank — Architecture

How the Internal Operations Assistant is put together. For installation steps see
[SETUP.md](SETUP.md); for the release pipeline see [DEPLOYMENT.md](DEPLOYMENT.md).

> **Status:** this describes the target design. At the time of writing only `app/config.py`
> and the Bedrock smoke test (`test/test.py`) are implemented; the other modules are stubs.

---

## What it does

Bank staff ask questions about internal policy documents (lending, savings, fees, card
disputes, account opening, AML/KYC). The assistant answers from those documents only, cites
the section it used, and never shows a user content above their role.

Two rules shape most of the design:

1. **Role isolation.** A teller must never see content restricted to compliance, such as AML
   thresholds. This is enforced at retrieval time, not by asking the model to behave.
2. **Supersession.** Circulars amend policies (for example `NB-CIR-2026-04` amends the
   personal-loan policy). An answer must use the current rule, not the amended one.

---

## Components

```
                 ┌──────────────────────────── Browser ────────────────────────────┐
                 │  index.html + app.js                                            │
                 └───────┬──────────────────────────────────────────────┬─────────┘
                         │ chat / API                                   │ PUT (presigned URL)
                         ▼                                              ▼
┌──────────────────────── FastAPI (app/) ─────────────────────┐   ┌──────────┐
│ main.py       routes, health checks                         │   │   S3     │
│ graph.py      LangGraph workflow                            │   │ original │
│ guardrails.py input & output checks                         │   │   docs   │
│ rag.py        retrieval, rerank, supersession               │   └────┬─────┘
│ vector.py     Pinecone, role-filtered search ───────────────┼──┐     │
│ aws.py        boto3: Bedrock, presigned URLs                │  │     │ read
│ memory.py     chat history                                  │  │     ▼
│ db.py         Postgres                                      │  │ ┌──────────── worker/ ───────────┐
└──────┬──────────────────┬───────────────────────────────────┘  │ │ extract → chunk → embed →      │
       │                  │                                      │ │ upsert                         │
       ▼                  ▼                                      ▼ └───────┬────────────────┬───────┘
┌────────────┐   ┌──────────────────┐                   ┌──────────────┐   │                │
│ Bedrock    │   │ RDS PostgreSQL   │                   │ Pinecone     │◄──┘ upsert         │
│ Nova 2 Lite│   │ documents, chat, │◄──────────────────┤ 1024-d index │                    │
│ Titan V2   │   │ audit, approvals,│   doc registry    └──────────────┘                    │
└────────────┘   │ feedback         │◄──────────────────────────────────────────────────────┘
                 └──────────────────┘
       All requests traced to LangSmith.
```

| Component | Technology | Responsibility |
|---|---|---|
| Web app | FastAPI, Jinja2, vanilla JS | Chat UI, API, presigned upload URLs |
| Orchestration | LangGraph | Runs each request as a graph of nodes |
| Chat model | Bedrock Nova 2 Lite (`us.amazon.nova-2-lite-v1:0`) via `converse` | Writes the answer from retrieved chunks |
| Embeddings | Bedrock Titan Text Embeddings V2 via `invoke_model` | 1024-d vectors for chunks and queries |
| Vector store | Pinecone serverless, cosine | Similarity search with metadata filters |
| Object store | S3 | Source documents; browser uploads go straight here |
| Relational store | RDS PostgreSQL | Document registry, conversations, approvals, feedback, audit |
| Ingestion | `worker/` | Turns documents into embedded, labelled chunks |
| Observability | LangSmith | Per-request traces and evaluation runs |

---

## Request flow

One chat message passes through the LangGraph workflow in `app/graph.py`:

1. **Input guardrail** — reject prompt injection, out-of-scope requests and attempts to
   request restricted content.
2. **Load memory** — the last `MEMORY_TURNS` turns from `chat_messages`.
3. **Embed query** — Titan V2, 1024-d, normalized.
4. **Retrieve** — Pinecone query with a metadata filter on the user's role (see below).
5. **Supersession** — drop or rewrite chunks whose `superseded_by` points to a newer document
   that was also retrieved, so the current rule wins.
6. **Generate** — Nova 2 Lite through `converse`, instructed to answer only from the supplied
   chunks and to cite `doc_id` and `section`.
7. **Output guardrail** — check the answer is grounded in the chunks and contains nothing
   above the user's role.
8. **Human approval (HITL)** — when `HITL_ENABLED=true`, answers that would trigger an action
   are held in `approvals` until a reviewer accepts them.
9. **Persist** — write the turn to `chat_messages` and an entry to `audit_events`.

Each node shows up as a span in the LangSmith trace for that request.

---

## Vector store

One Pinecone index holds every chunk from every document. Each record is:

```
id         "<doc_id>#<chunk_no>"
values     1024 floats (Titan V2)
metadata   doc_id, section, page, min_role, superseded_by
```

**Role filtering happens inside the query**, as a Pinecone metadata filter on `min_role`. The
search only ever considers chunks the user is allowed to see. Filtering the results afterwards
would be weaker: restricted chunks would still take up top-k slots, and one bug in the
post-filter would leak them.

Namespaces are not used, because separation is by role and a single document can contain
chunks for different roles.

The index dimension must equal `EMBED_DIMENSION` in `app/config.py`. Changing the embedding
model or dimension means re-creating the index and re-ingesting.

---

## Ingestion

`python -m worker.ingest` runs offline, not per request:

1. **Extract** (`extract.py`) — `pdfplumber` with `layout=True`, so tables and numbered
   clauses keep their structure.
2. **Chunk** (`chunker.py`) — split on section boundaries, then by size; attach `doc_id`,
   `section`, `page`, `min_role` and `superseded_by`.
3. **Embed** — Titan V2 via `invoke_model`.
4. **Upsert** — to Pinecone, and register the document in the `documents` table.

`min_role` and `superseded_by` come from the document registry, not from the model, so
access control never depends on an LLM's judgement.

---

## Data model (PostgreSQL)

| Table | Holds |
|---|---|
| `documents` | Registry: `doc_id`, title, S3 key, `min_role`, `superseded_by`, version |
| `chat_messages` | Conversation turns, used for memory |
| `audit_events` | Who asked what, which chunks were returned, what was answered |
| `approvals` | Answers waiting for or decided by a human reviewer |
| `feedback` | Thumbs up/down and comments on answers |

The schema lives in `infra/schema.sql` and is applied by `scripts/init_db.py`.

---

## Configuration

| Kind | Where | Examples |
|---|---|---|
| Constants | `app/config.py` | `BEDROCK_CHAT_MODEL`, `BEDROCK_EMBED_MODEL`, `EMBED_DIMENSION` |
| Secrets and per-environment values | `.env` locally, AWS Secrets Manager in production | `DATABASE_URL`, `PINECONE_API_KEY`, `LANGSMITH_API_KEY` |

`.env.example` lists every variable. `.env` is gitignored.

---

## Evaluation

`eval/gold_set.jsonl` holds labelled questions with the expected source chunks and the role
of the person asking. `python -m eval.run` scores:

| Metric | Meaning | Threshold |
|---|---|---|
| Context recall | Were the right chunks retrieved? | high |
| Faithfulness | Is the answer supported by those chunks? | high |
| Role-leak rate | Did any answer include content above the asker's role? | **exactly 0** |
| Supersession accuracy | Was the current rule used, not the amended one? | high |

The script exits non-zero when any threshold is missed, and CI uses that exit code to block
the deploy.

---

## Deployment

```
push → GitHub Actions: tests → eval gate → docker build → ECR → EC2 (via SSM)
```

- CI authenticates to AWS with **GitHub OIDC**, assuming a deploy role. No access keys are
  stored in GitHub.
- The developer IAM user has no ECR or EC2 permissions, so a leaked laptop credential cannot
  change production.
- The container runs on EC2. The deploy step uses AWS Systems Manager to pull the new image
  and restart, so the instance needs no inbound SSH.
- In production, RDS is in a private subnet that only the EC2 instance can reach. Secrets
  come from Secrets Manager, and logs go to CloudWatch.

Details in [DEPLOYMENT.md](DEPLOYMENT.md).
