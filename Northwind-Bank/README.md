## Project structure

```
Northwind-Bank/
│
├── .github/workflows/
│   └── deploy.yml              CI: tests → eval gate → build → ECR → EC2
│
├── app/
│   ├── __init__.py
│   ├── main.py                 routes, app wiring
│   ├── config.py               settings from env
│   ├── schemas.py              Pydantic request & response models
│   ├── db.py                   Postgres
│   ├── aws.py                  boto3 clients, presigned URLs, Bedrock
│   ├── vector.py               Pinecone, role-filtered search
│   ├── rag.py                  retrieval, rerank, supersession
│   ├── memory.py               chat history
│   ├── guardrails.py           input & output guardrails
│   ├── graph.py                LangGraph workflow
│   ├── observability.py        LangSmith config
│   ├── templates/
│   │   └── index.html
│   └── static/
│       ├── css/styles.css
│       └── js/app.js
│
├── worker/
│   ├── __init__.py
│   ├── extract.py              pdfplumber, layout=True
│   ├── chunker.py              chunking + metadata
│   └── ingest.py               extract → chunk → embed → upsert
│
├── eval/
│   ├── __init__.py
│   ├── gold_set.jsonl          20 labelled questions
│   ├── scorers.py              recall, faithfulness, role-leak
│   └── run.py                  exits non-zero on regression
│
├── tests/
│   ├── __init__.py
│   ├── test_guardrails.py
│   ├── test_chunker.py
│   └── test_rag.py
│
├── corpus/                     7 bank PDFs
├── infra/schema.sql
├── scripts/
│   ├── init_db.py
│   └── seed_s3.py
├── docs/
│   ├── SETUP.md
│   ├── ARCHITECTURE.md
│   ├── DEPLOYMENT.md
│   └── IMPLEMENTATION_ORDER.md
│
├── .env                        gitignored
├── .env.example
├── .gitignore
├── .dockerignore
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── requirements-dev.txt
└── README.md
```

## Technology stack

| Layer | Technology | Purpose |
|---|---|---|
| Backend | Python, FastAPI, Uvicorn | API and application server |
| Frontend | HTML, CSS, JavaScript | Browser-based user interface |
| Orchestration | LangGraph | Stateful RAG workflow with guardrail nodes |
| LLM | Amazon Bedrock — Nova 2 Lite | Response generation |
| Embeddings | Amazon Bedrock — Titan Text Embeddings V2 | Document and query vectors (1,024 dimensions) |
| Vector database | Pinecone | Semantic retrieval over document chunks |
| Object storage | Amazon S3 | Original documents, presigned upload |
| Relational database | Amazon RDS (PostgreSQL) | Registry, conversations, approvals, feedback, audit |
| Secrets | AWS Secrets Manager | Pinecone, LangSmith and database credentials |
| Observability & evals | **LangSmith** | Request tracing and gold-set evaluation runs |
| Containerization | Docker | Portable application runtime |
| Image registry | Amazon ECR | Private image storage, tagged by commit |
| Compute | Amazon EC2 | Runs the deployed container |
| CI/CD | GitHub Actions | Build, test, eval gate, publish, deploy |
| CI authentication | GitHub OIDC → IAM role | Short-lived credentials, no stored access keys |
| Deployment | AWS Systems Manager | Pull-and-restart, no inbound SSH |
| Logs | Amazon CloudWatch | Container logs and instance metrics |

