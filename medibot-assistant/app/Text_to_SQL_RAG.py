from app.config import *

import sqlite3
import re

from langchain_groq import ChatGroq


llm = ChatGroq(
    model="openai/gpt-oss-20b",
        temperature=0,
        max_tokens=None,
)


# connecting to the DB and getting the Schema
def get_schema():
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()

    try:
        parts = []
        for name, ddl in cursor.execute(
            "SELECT name, sql FROM sqlite_master "
            "WHERE type='table' AND name NOT LIKE 'sqlite_%' AND sql IS NOT NULL"
        ).fetchall():
            rows = cursor.execute(f"SELECT * FROM [{name}] LIMIT 3").fetchall()
            parts.append(f"{ddl}\n-- sample rows: {rows}")

        return "\n\n".join(parts)

    finally:
        cursor.close()
        connection.close()


# Hitting the database and running the SQL query
def run_sql(sql: str):
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()

    try:
        rows = cursor.execute(sql).fetchall()
        columns = [description[0] for description in cursor.description] if cursor.description else []
        return columns, rows

    finally:
        cursor.close()
        connection.close()


def generate_sql(question: str) -> str:

    SCHEMA = get_schema()

    prompt = f"""You are a SQLite expert working with a hospital operations database.

    Schema:
    {SCHEMA}

    Write a single SQLite SELECT query that answers the question below.
    Use only the tables and columns shown above, and match the exact string
    values shown in the sample rows.
    Return ONLY the SQL statement: no explanation, no markdown fences.

    Question: {question}
"""

    return llm.invoke(prompt).content


def clean_sql(raw: str) -> str:
    """Strip markdown fences and any preamble, leaving only the SQL statement."""
    raw = re.sub(r"```(?:sql)?", "", raw).strip("`").strip()
    # If the LLM prefixed with 'SQLQuery:' or 'Question: ...\nSQLQuery:', keep only what's after
    if "SQLQuery:" in raw:
        raw = raw.split("SQLQuery:")[-1].strip()
    return raw


def phrase_answer(question: str, sql: str, rows, columns=None):
    if not rows:
        return "The query ran successfully but no records matched."

    if columns is None:
        columns = []

    preview = rows[:30]
    truncated = " (showing the first 30 rows)" if len(rows) > 30 else ""

    prompt = f"""Question: {question}

                SQL executed:
                {sql}

                Columns: {columns}
                Rows{truncated}: {preview}

                Answer the question in one or two sentences using only these results.
                Include the relevant numbers. Do not mention SQL or the query itself."""

    
    return llm.invoke(prompt).content



def sql_rag_chain(question : str) -> str:
    # 1. translate the question into SQL
    raw_sql = generate_sql(question)

    # 2. clean the raw output down to an executable statement
    cleaned_sql = clean_sql(raw_sql)
    print("SQL:", cleaned_sql) 

    # 3. execute, then hand the result back to the LLM
    columns, rows = run_sql(cleaned_sql)
    return phrase_answer(question, cleaned_sql, rows, columns)

if __name__ == "__main__":
    for q in [
        "How many claims are there by status?",
        "Which equipment category has the most open maintenance tickets?",
        "What is the total claim amount by department?",
        "How many maintenance tickets were raised in each month?",
    ]:
        print(f"\nQ: {q}")
        print(f"A: {sql_rag_chain(q)}")









