
from pathlib import Path

folders = [
    ".github/workflows",
    "app/templates",
    "app/static/css",
    "app/static/js",
    "worker",
    "eval",
    "tests",
    "corpus",
    "infra",
    "scripts",
    "docs",
]

files = [
    # root
    "requirements.txt",
    "requirements-dev.txt",
    ".env",
    ".env.example",
    ".gitignore",
    ".dockerignore",
    "Dockerfile",
    "docker-compose.yml",
    "README.md",

    # ci
    ".github/workflows/deploy.yml",

    # backend
    "app/__init__.py",
    "app/main.py",
    "app/config.py",
    "app/schemas.py",
    "app/db.py",
    "app/aws.py",
    "app/vector.py",
    "app/rag.py",
    "app/memory.py",
    "app/guardrails.py",
    "app/graph.py",
    "app/observability.py",

    # frontend
    "app/templates/index.html",
    "app/static/css/styles.css",
    "app/static/js/app.js",

    # ingestion
    "worker/__init__.py",
    "worker/extract.py",
    "worker/chunker.py",
    "worker/ingest.py",

    # evaluation
    "eval/__init__.py",
    "eval/gold_set.jsonl",
    "eval/scorers.py",
    "eval/run.py",

    # tests
    "tests/__init__.py",
    "tests/test_guardrails.py",
    "tests/test_chunker.py",
    "tests/test_rag.py",

    # database
    "infra/schema.sql",
    "scripts/init_db.py",
    "scripts/seed_s3.py",

    # docs
    "docs/SETUP.md",
    "docs/ARCHITECTURE.md",
    "docs/DEPLOYMENT.md",
]


def create_structure():
    for folder in folders:
        Path(folder).mkdir(parents=True, exist_ok=True)

    for file in files:
        path = Path(file)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch(exist_ok=True)

    print("Project folders and files created successfully!")
    print(f"Total folders: {len(folders)}")
    print(f"Total files: {len(files)}")


if __name__ == "__main__":
    create_structure()