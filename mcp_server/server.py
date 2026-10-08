import httpx
from mcp.server.fastmcp import FastMCP

BACKEND = "http://127.0.0.1:8000"   # your FastAPI backend
mcp = FastMCP("novaflow")


def _get(path, **params):
    """Call one backend endpoint and return its data."""
    r = httpx.get(f"{BACKEND}{path}", params=params, timeout=60)
    r.raise_for_status()
    return r.json()


@mcp.tool()
def get_payment_failure_rate():
    """Payments, failed payments and failure percentage per month."""
    return _get("/payments/failure-rate")


@mcp.tool()
def get_monthly_cancellations():
    """Number of customer cancellations per month."""
    return _get("/cancellations/monthly")


@mcp.tool()
def get_payment_failure_reasons():
    """Why payments failed (for example gateway_timeout), counted per month."""
    return _get("/payments/failure-reasons")


@mcp.tool()
def get_tickets_by_category():
    """Support tickets per month, split by category (payment, pricing, and so on)."""
    return _get("/tickets/by-category")


@mcp.tool()
def get_incidents():
    """List of recorded incidents with service, severity, start and end time."""
    return _get("/incidents")


@mcp.tool()
def get_cancellations_after_failed_payment():
    """Cancellations that had a failed payment in the 14 days before (14 days is an assumption)."""
    return _get("/cancellations/after-failed-payment")


@mcp.tool()
def search_documents(query: str, limit: int = 6):
    """Search incident reports, release notes and policies by meaning. Dates work poorly here; use get_documents_by_month for a month."""
    return _get("/documents/search", q=query, limit=limit)


@mcp.tool()
def get_documents_by_month(month: str):
    """Documents for one month, as YYYY-MM (for example 2026-10)."""
    return _get("/documents/by-month", month=month)


if __name__ == "__main__":
    mcp.run()