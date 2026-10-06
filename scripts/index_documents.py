"""
index_documents.py -- makes the NovaFlow documents searchable by meaning.

Run from the project root (venv active, PostgreSQL running):
    python scripts/index_documents.py

What it does:
  1. Reads every .md file in data/documents/
  2. Cuts each file into chunks (one chunk per "## section")
  3. Turns each chunk into numbers (an embedding) using a model on your laptop
  4. Saves chunks + embeddings in a PostgreSQL table called document_chunks

Safe to re-run: it clears the table first, so you never get duplicates.
"""
import os
from pathlib import Path

import numpy as np
import psycopg
from dotenv import load_dotenv
from fastembed import TextEmbedding

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "data" / "documents"
MODEL_NAME = "BAAI/bge-small-en-v1.5"

load_dotenv(ROOT / ".env")


def chunk_markdown(text):
    """Split one document into chunks, one per '## ' section.
    Every chunk starts with the document's title line so it keeps its context."""
    lines = text.strip().splitlines()
    title = lines[0].lstrip("# ").strip() if lines else ""
    chunks, current = [], []
    for line in lines:
        if line.startswith("## ") and current:
            chunks.append("\n".join(current).strip())
            current = [f"# {title}", line]
        else:
            current.append(line)
    if current:
        chunks.append("\n".join(current).strip())
    return title, [c for c in chunks if len(c) > 20]


def connect():
    return psycopg.connect(
        host=os.getenv("DB_HOST"), port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"), user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )


def main():
    # 1 + 2: read and chunk
    rows = []  # (doc_path, doc_type, title, chunk_index, content)
    for path in sorted(DOCS.rglob("*.md")):
        title, chunks = chunk_markdown(path.read_text(encoding="utf-8"))
        rel = path.relative_to(DOCS).as_posix()
        doc_type = path.parent.name
        for i, content in enumerate(chunks):
            rows.append((rel, doc_type, title, i, content))
    print(f"Read {len(set(r[0] for r in rows))} documents -> {len(rows)} chunks")

    # 3: embed (first run downloads the model, about 100 MB)
    print("Loading embedding model (first run downloads it)...")
    model = TextEmbedding(MODEL_NAME)
    vectors = list(model.embed([r[4] for r in rows]))
    print(f"Embedded {len(vectors)} chunks, {len(vectors[0])} numbers each")

    # 4: store
    with connect() as conn, conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS document_chunks (
                chunk_id    SERIAL PRIMARY KEY,
                doc_path    TEXT,
                doc_type    TEXT,
                title       TEXT,
                chunk_index INT,
                content     TEXT,
                embedding   REAL[]
            )
        """)
        cur.execute("TRUNCATE document_chunks RESTART IDENTITY")
        for (doc_path, doc_type, title, idx, content), vec in zip(rows, vectors):
            vec = (vec / np.linalg.norm(vec)).astype(float).tolist()
            cur.execute(
                "INSERT INTO document_chunks "
                "(doc_path, doc_type, title, chunk_index, content, embedding) "
                "VALUES (%s, %s, %s, %s, %s, %s::real[])",
                (doc_path, doc_type, title, idx, content, vec),
            )
    print("Done. Saved to table document_chunks.")


if __name__ == "__main__":
    main()
