import os

import numpy as np
import psycopg
from dotenv import load_dotenv
from fastapi import FastAPI, Query
from fastembed import TextEmbedding
from psycopg.rows import dict_row

load_dotenv()  # reads the .env file


def run_query(sql):
    """Open a connection to PostgreSQL, run one SQL query, return rows."""
    with psycopg.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        row_factory=dict_row,
    ) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            return cur.fetchall()


app = FastAPI(title="NovaFlow Operations API")


@app.get("/")
def health_check():
    return {"status": "ok"}


@app.get("/payments/failure-rate")
def payment_failure_rate():
    return run_query("""
        SELECT TO_CHAR(date, 'YYYY-MM') AS month,
               COUNT(*) AS payments,
               SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) AS failed,
               ROUND(100.0 * SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END)
                     / COUNT(*), 1) AS fail_pct
        FROM payments
        GROUP BY month
        ORDER BY month
    """)


@app.get("/cancellations/monthly")
def cancellations_monthly():
    return run_query("""
        SELECT TO_CHAR(end_date, 'YYYY-MM') AS month,
               COUNT(*) AS cancellations
        FROM subscriptions
        WHERE status = 'cancelled'
        GROUP BY month
        ORDER BY month
    """)
@app.get("/payments/failure-reasons")
def payment_failure_reasons():
    return run_query("""
        SELECT TO_CHAR(date, 'YYYY-MM') AS month,
               failure_reason,
               COUNT(*) AS failed
        FROM payments
        WHERE status = 'failed'
        GROUP BY month, failure_reason
        ORDER BY month, failure_reason
    """)


@app.get("/tickets/by-category")
def tickets_by_category():
    return run_query("""
        SELECT TO_CHAR(created_at, 'YYYY-MM') AS month,
               category,
               COUNT(*) AS tickets
        FROM support_tickets
        GROUP BY month, category
        ORDER BY month, category
    """)


@app.get("/incidents")
def list_incidents():
    return run_query("""
        SELECT incident_id, start_time, end_time, service, severity, description
        FROM incidents
        ORDER BY start_time
    """)
_model = None


def get_model():
    """Load the embedding model once and reuse it."""
    global _model
    if _model is None:
        _model = TextEmbedding("BAAI/bge-small-en-v1.5")
    return _model


@app.get("/documents/search")
def search_documents(q: str = Query(..., min_length=3),
                     limit: int = Query(5, ge=1, le=20)):
    chunks = run_query(
        "SELECT doc_path, doc_type, content, embedding FROM document_chunks"
    )
    if not chunks:
        return []
    vec = list(get_model().query_embed(q))[0]
    vec = vec / np.linalg.norm(vec)
    matrix = np.array([c["embedding"] for c in chunks])
    scores = matrix @ vec
    best = np.argsort(-scores)[:limit]
    return [
        {
            "score": round(float(scores[i]), 3),
            "doc_path": chunks[i]["doc_path"],
            "doc_type": chunks[i]["doc_type"],
            "content": chunks[i]["content"],
        }
        for i in best
    ]
@app.get("/cancellations/after-failed-payment")
def cancellations_after_failed_payment():
    return run_query("""
        SELECT TO_CHAR(s.end_date, 'YYYY-MM') AS month,
               COUNT(DISTINCT s.subscription_id) AS cancellations,
               COUNT(DISTINCT s.subscription_id)
                   FILTER (WHERE p.payment_id IS NOT NULL) AS after_failed_payment
        FROM subscriptions s
        LEFT JOIN payments p
               ON p.customer_id = s.customer_id
              AND p.status = 'failed'
              AND p.date BETWEEN s.end_date - 14 AND s.end_date
        WHERE s.status = 'cancelled'
        GROUP BY month
        ORDER BY month
    """)