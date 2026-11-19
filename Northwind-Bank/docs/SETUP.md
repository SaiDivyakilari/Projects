# Northwind Bank — Setup Guide

Work through these in order; each step depends on the one before it.

> Steps marked **(planned)** describe scripts or endpoints that are not implemented yet.

---

## 1. Create a Python environment

```powershell
py -3.13 -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
```

Verify you are in the right environment before installing anything:

```powershell
python -c "import sys; print(sys.executable)"
```

The path must contain `.venv`. Always use `python -m pip`, never bare `pip` — on Windows,
`pip` often resolves to a different Python than `python` does, which installs your packages
into the wrong environment.

---

## 2. Configure AWS IAM credentials

1. Sign in to the [AWS Console](https://console.aws.amazon.com/).
2. In **IAM → Users**, create a dedicated user for this project (`northwind-dev` or similar).
3. Attach permissions for:
   - `s3:PutObject`, `s3:GetObject`, `s3:DeleteObject`, `s3:ListBucket` on the project bucket
   - `bedrock:InvokeModel` (covers both `InvokeModel` and `Converse`)
   - `bedrock:InvokeModelWithResponseStream` if you use `converse_stream`
4. **Security credentials → Create access key → Local code.** Copy the secret immediately;
   it is shown once.
5. Region: `us-east-1`.

Because the chat model is called through a cross-region inference profile (step 3), the
Bedrock permission must cover **both** the inference profile and the underlying model in
every region the profile can route to:

```json
{
  "Effect": "Allow",
  "Action": ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
  "Resource": [
    "arn:aws:bedrock:us-east-1:*:inference-profile/us.amazon.nova-2-lite-v1:0",
    "arn:aws:bedrock:*::foundation-model/amazon.nova-2-lite-v1:0",
    "arn:aws:bedrock:us-east-1::foundation-model/amazon.titan-embed-text-v2:0"
  ]
}
```

ECR and EC2 permissions do **not** belong on this user. Those are used only by CI at deploy
time, through a separate IAM role assumed via GitHub OIDC. Keeping them apart means a leaked
development credential cannot modify production.

### Where the credentials live

Pick **one** of these and stick with it:

- **`aws configure` (recommended).** Stores the keys in `~/.aws/credentials`. boto3 finds them
  automatically, so leave `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` blank in `.env`.
- **`.env`.** Put the keys in `.env` and pass them to `boto3.client(...)` explicitly.

Either way, confirm they work:

```powershell
aws sts get-caller-identity
```

It should return your account ID and the IAM user's ARN.

---

## 3. Configure Amazon Bedrock

| Purpose | Model | ID to use in code |
|---|---|---|
| Chat | Amazon Nova 2 Lite | `us.amazon.nova-2-lite-v1:0` |
| Embeddings | Amazon Titan Text Embeddings V2 | `amazon.titan-embed-text-v2:0` |

There is no model access step. Serverless Bedrock models are enabled automatically the first
time your account invokes them.

**Nova 2 Lite must be called through an inference profile.** The bare ID
`amazon.nova-2-lite-v1:0` fails with *"Invocation of model ID ... with on-demand throughput
isn't supported"*. The `us.` prefix is the US cross-region profile, which lets Bedrock route
the request to whichever US region has capacity. Use `eu.` or `apac.` for those regions.
Titan V2 supports on-demand calls, so it uses the bare ID.

Titan V2 supports 1024, 512 or 256 dimensions; this project uses **1024**.

The two models are called through different APIs:

- **Embeddings → `invoke_model`**, with Titan's native body (`inputText`, `dimensions`, `normalize`).
- **Chat → `converse`**, Bedrock's model-agnostic chat API. Swapping models means changing only the ID.

List the inference profiles available to your account:

```powershell
aws bedrock list-inference-profiles --region us-east-1 --query "inferenceProfileSummaries[?contains(inferenceProfileId,'nova')].inferenceProfileId"
```

Smoke-test both models:

```powershell
python test\test.py
```

---

## 4. Create the S3 bucket and add CORS

1. Open [Amazon S3](https://console.aws.amazon.com/s3/).
2. **Create bucket** with a globally unique name, in `us-east-1`.
3. Leave **Block all public access** enabled and keep default encryption on.
4. Bucket → **Permissions → Cross-origin resource sharing (CORS) → Edit**:

```json
[
  {
    "AllowedHeaders": ["*"],
    "AllowedMethods": ["PUT"],
    "AllowedOrigins": [
      "http://127.0.0.1:8000",
      "http://localhost:8000"
    ],
    "ExposeHeaders": ["ETag"],
    "MaxAgeSeconds": 3000
  }
]
```

CORS is required because the browser uploads directly to S3 using a presigned URL — the file
never passes through FastAPI. Without this rule the browser fails with `Failed to fetch`.

Use the exact origin shown in your browser's address bar. When the app is deployed, add the
deployed origin to this list.

Upload the corpus **(planned)**:

```powershell
python scripts\seed_s3.py
```

---

## 5. Configure Pinecone

1. Open the [Pinecone Console](https://app.pinecone.io/) and create an API key.
2. Create an index with:
   - **Dimension: 1024** — must match `EMBED_DIMENSION` exactly
   - **Metric: cosine**
   - **Type: dense, serverless, AWS `us-east-1`**
3. Copy the index **name** into `.env` as `PINECONE_INDEX`.

`PINECONE_INDEX_HOST` is optional. Passing it skips one lookup call at startup; leaving it
out means the SDK resolves the host from the index name.

See [ARCHITECTURE.md](ARCHITECTURE.md#vector-store) for the record layout and how role
filtering works.

---

## 6. Configure Amazon RDS (PostgreSQL)

1. Open the [RDS Console](https://console.aws.amazon.com/rds/) → **Create database**.
2. Choose **Full configuration** (not Easy create — it hides the settings you need).

| Field | Value |
|---|---|
| Engine | PostgreSQL 16 |
| Template | Free tier |
| DB instance identifier | `northwind-bank` |
| Master username | `postgres` |
| Credentials management | Self managed — set a password |
| Instance class | `db.t4g.micro` |
| Storage | gp3, 20 GiB, autoscaling **off** |
| **Public access** | **Yes** |
| VPC security group | Create new → `northwind-db-sg` |
| Port | 5432 |
| Performance Insights | **Off** |
| **Initial database name** | **`northwind`** |

**Initial database name** is under *Additional configuration*. Leave it blank and RDS creates
a server with no `northwind` database on it.

**Public access** can be changed later (**Modify → Connectivity → Public access**), but the
**VPC** cannot. Choose the VPC carefully.

Wait for status **Available** (5–10 minutes).

### Open the firewall

Instance → **Connectivity & security** → security group → **Inbound rules**. You need a
PostgreSQL (5432) rule with your IP as source. If only an *Outbound* rule is listed, add it:
**Edit inbound rules → Add rule → PostgreSQL → My IP**.

Without this the connection hangs until it times out, with no useful error. "My IP" is your
current address, so the rule needs updating if your network changes.

### Connection string

Copy the **Endpoint** from Connectivity & security, then set one variable in `.env`:

```dotenv
DATABASE_URL=postgresql://postgres:PASSWORD@YOUR-ENDPOINT.us-east-1.rds.amazonaws.com:5432/northwind?sslmode=require
```

URL-encode any `@ / # : ?` in the password (`@` becomes `%40`). An unencoded `@` makes the URL
parse wrong and produces a confusing host error.

`DATABASE_URL` is the only database variable the app needs. Do not keep separate username,
password or database-name variables alongside it — they drift out of sync.

Public access is a development convenience. In production the database sits in a private
subnet reachable only from the EC2 instance, with no public endpoint.

---

## 7. Configure LangSmith

1. Open [LangSmith](https://smith.langchain.com/) and create an API key.
2. Add the `LANGSMITH_*` variables to `.env` (step 8).

No tracing code is required. LangGraph sends traces automatically once
`LANGSMITH_TRACING=true`, so every node, retrieval and model call appears in the trace for
each request.

---

## 8. Create the `.env` file

```powershell
Copy-Item .env.example .env
```

Then fill in the values. `.env.example` lists every variable:

```dotenv
# AWS — leave the keys blank if you ran `aws configure`
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_REGION=us-east-1
S3_BUCKET=YOUR_BUCKET_NAME

# Amazon RDS (PostgreSQL)
DATABASE_URL=postgresql://postgres:PASSWORD@YOUR-ENDPOINT.us-east-1.rds.amazonaws.com:5432/northwind?sslmode=require

# Pinecone
PINECONE_API_KEY=YOUR_PINECONE_API_KEY
PINECONE_INDEX=northwind-bank-ai-index
PINECONE_CLOUD=aws
PINECONE_REGION=us-east-1
PINECONE_READY_TIMEOUT=180

# LangSmith
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=YOUR_LANGSMITH_API_KEY
LANGSMITH_PROJECT=northwind

# App
HITL_ENABLED=true
MEMORY_TURNS=6
```

**Model IDs and the embedding dimension are not in `.env`.** They are constants, not secrets,
and live in `app/config.py`:

```python
BEDROCK_EMBED_MODEL = "amazon.titan-embed-text-v2:0"
BEDROCK_CHAT_MODEL = "us.amazon.nova-2-lite-v1:0"
EMBED_DIMENSION = 1024
```

Import them from there (`from app.config import BEDROCK_CHAT_MODEL`); do not read them with
`os.getenv`, which returns `None` for variables that are not in `.env`.

Rules for `.env`:

- **It must be in `.gitignore` before your first commit.** Once pushed, deleting the file
  later does not remove it from git history. Commit `.env.example` instead.
- One `KEY=value` per line, no spaces around `=`, no spaces inside the key, no surrounding
  quotes. A trailing space becomes part of the value and will be rejected by the API.

---

## 9. Initialize the database

Check the connection first:

```powershell
python -c "import os, psycopg; from dotenv import load_dotenv; load_dotenv(); print(psycopg.connect(os.environ['DATABASE_URL']).execute('select version()').fetchone()[0])"
```

This should print a PostgreSQL version string. Do not continue until it does.

| Symptom | Cause |
|---|---|
| Hangs, then times out | Security group inbound rule — step 6 |
| `password authentication failed` | Wrong password, or a special character not URL-encoded |
| `database "northwind" does not exist` | Initial database name was left blank |
| `could not translate host name` | Endpoint typo, or an unencoded `@` in the password |

Then create the schema **(planned)**:

```powershell
python scripts\init_db.py
```

Expected: five tables — `documents`, `chat_messages`, `audit_events`, `approvals`, `feedback`.
The schema uses `CREATE TABLE IF NOT EXISTS`, so the script is safe to re-run as the schema grows.

---

## 10. Ingest the corpus (planned)

```powershell
python -m worker.ingest
```

This reads the documents from S3, extracts layout-aware text, chunks it, embeds each chunk
with Titan V2, and upserts to Pinecone with role and supersession metadata.

Before trusting the index, check retrieval on its own, with no LLM involved:

```powershell
python -m eval.run --retrieval-only
```

Most RAG failures are retrieval failures, and they are invisible once a model is smoothing
over the gaps. Look at the chunks that come back for a few gold questions and read them
yourself.

---

## 11. Run the application (planned)

```powershell
uvicorn app.main:app --reload
```

| | |
|---|---|
| App | http://127.0.0.1:8000 |
| API docs | http://127.0.0.1:8000/api/docs |
| Liveness | http://127.0.0.1:8000/health/live |
| Database readiness | http://127.0.0.1:8000/health/ready |

Leave the terminal running. **Ctrl+C** stops the server.

---

## 12. Run the evaluation gate (planned)

```powershell
python -m eval.run
```

Runs the labelled questions in `eval/gold_set.jsonl` and scores context recall,
faithfulness, role-leak rate and supersession accuracy against their thresholds. Exits
non-zero if any threshold is breached, which is what blocks a deploy in CI.

Role-leak rate has a threshold of exactly zero. A teller seeing AML thresholds is not a
quality regression, it is an incident.

---

## Troubleshooting

**`'aws' is not recognized`** — the AWS CLI is not installed, or the terminal was open before
installation. Install it, then open a new terminal; the installer updates PATH and an existing
terminal will not see it.

**`No module named pip`** — `python` and `pip` point at different installations. Recreate the
venv with `py -3.13 -m venv .venv` and use `python -m pip` from then on.

**Dependency conflicts mentioning packages you never installed** — you are installing into a
shared environment from another project. If `python -m pip list` shows packages such as
`langchain-groq` or `docling-core`, you are in the wrong environment.

**`ModuleNotFoundError: No module named 'app'`** — run from the project root with
`python -m <module>`, or add the project root to `sys.path` (see `test/test.py`).

**`Invalid type for parameter modelId, value: None`** — the model ID was read with
`os.getenv` but is not in `.env`. Import it from `app.config` instead.

**`on-demand throughput isn't supported`** — use the inference profile ID
(`us.amazon.nova-2-lite-v1:0`), not the bare model ID. See step 3.

**`AccessDeniedException: Your account is currently being verified`** — an account-level
hold, not a code or IAM problem. It usually clears within a couple of hours; otherwise
contact AWS Support (Account and billing).

**Bedrock `AccessDeniedException` (other messages)** — the IAM policy does not cover the
inference profile and every regional foundation-model ARN behind it. See step 2.

**Browser upload fails with `Failed to fetch`** — S3 CORS, step 4. The origin must match your
address bar exactly.
