import os

import psycopg
from dotenv import load_dotenv
from fastapi import FastAPI
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