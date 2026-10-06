"""
search_documents.py -- ask a question, see which document chunks match best.

Usage (from the project root, venv active):
    python scripts/search_documents.py "why did payments fail in October"
"""
import os
import sys
from pathlib import Path

import numpy as np
import psycopg
from dotenv import load_dotenv
from fastembed import TextEmbedding

ROOT = Path(__file__).resolve().parent.parent
MODEL_NAME = "BAAI/bge-small-en-v1.5"
TOP_K = 5

load_dotenv(ROOT / ".env")


def rank(query_vec, chunks, top_k=TOP_K):
    """chunks: list of (doc_path, content, embedding). Returns best matches."""
    matrix = np.array([c[2] for c in chunks])
    q = np.array(query_vec)
    q = q / np.linalg.norm(q)
    scores = matrix @ q          # similarity of the question to every chunk
    best = np.argsort(-scores)[:top_k]
    return [(float(scores[i]), chunks[i][0], chunks[i][1]) for i in best]


def main():
    if len(sys.argv) < 2:
        print('Usage: python scripts/search_documents.py "your question"')
        return
    question = " ".join(sys.argv[1:])

    model = TextEmbedding(MODEL_NAME)
    query_vec = list(model.query_embed(question))[0]

    with psycopg.connect(
        host=os.getenv("DB_HOST"), port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"), user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    ) as conn, conn.cursor() as cur:
        cur.execute("SELECT doc_path, content, embedding FROM document_chunks")
        chunks = cur.fetchall()

    print(f'\nQuestion: {question}\n')
    for score, path, content in rank(query_vec, chunks):
        preview = " ".join(content.split())[:160]
        print(f"{score:.3f}  {path}\n       {preview}...\n")


if __name__ == "__main__":
    main()
