"""
investigate.py -- Phase 6, first version of the investigation.

    python scripts/investigate.py            # investigates the latest month
    python scripts/investigate.py 2026-10    # investigates a specific month

Needs: backend running (uvicorn), Ollama running with llama3.1:8b.
Uses only Python's standard library (nothing new to install).

How it works (your principle: AI investigates, code validates, data is evidence):
  1. Code calls your backend endpoints and collects the evidence.
  2. Code does ALL the maths and decides the confidence label.
  3. The local model only WRITES the report from those facts.
  4. Code then checks that the numbers in the report appear in the facts.
"""
import json
import re
import sys
from pathlib import Path
from statistics import mean
from urllib import error, parse, request

API = "http://127.0.0.1:8000"
OLLAMA = "http://localhost:11434/api/chat"
MODEL = "llama3.1:8b"
ROOT = Path(r"C:\Users\lavan\AI-Operations-Intelligence")

DOC_QUERIES = [
    "root cause of the payment gateway incident",
    "what was released and changed this month",
    "why did customers cancel",
    "what to do when a payment fails",
]


# ------------------------------------------------------------ 1. gather
def get(path, **params):
    url = API + path + ("?" + parse.urlencode(params) if params else "")
    with request.urlopen(url, timeout=120) as r:
        return json.load(r)


def gather():
    return {
        "cancellations": get("/cancellations/monthly"),
        "linked": get("/cancellations/after-failed-payment"),
        "payments": get("/payments/failure-rate"),
        "reasons": get("/payments/failure-reasons"),
        "tickets": get("/tickets/by-category"),
        "incidents": get("/incidents"),
    }


def gather_docs():
    seen = {}
    for q in DOC_QUERIES:
        for hit in get("/documents/search", q=q, limit=6):
            key = (hit["doc_path"], hit["content"])
            if key not in seen or hit["score"] > seen[key]["score"]:
                seen[key] = hit
    hits = sorted(seen.values(), key=lambda h: -h["score"])[:8]
    return [{"document": h["doc_path"], "text": h["content"][:600]} for h in hits]


# ------------------------------------------------------------ 2. calculate
def compute(raw, target):
    by_month = lambda rows, key: {r["month"]: r[key] for r in rows}
    canc = by_month(raw["cancellations"], "cancellations")
    linked = by_month(raw["linked"], "after_failed_payment")
    fail_pct = by_month(raw["payments"], "fail_pct")
    failed_n = by_month(raw["payments"], "failed")

    months = sorted(canc)
    if target not in canc:
        raise SystemExit(f"No cancellation data for {target}. Months available: {months}")
    base = [m for m in months if m < target]
    if len(base) < 3:
        raise SystemExit("Need at least 3 earlier months to build a baseline.")
    prev = base[-1]
    avg = lambda d: mean(d.get(m, 0) for m in base)

    # cancellations
    inc = canc[target] - avg(canc)
    other_t = canc[target] - linked.get(target, 0)
    other_b = mean(canc[m] - linked.get(m, 0) for m in base)
    linked_inc = linked.get(target, 0) - avg(linked)
    share = round(100 * linked_inc / inc, 1) if inc > 0 else None
    share_note = None
    if share is not None and share > 100:
        share_note = ("Over 100% because cancellations NOT preceded by a failed payment "
                      "were slightly lower than usual, so payment-linked cancellations "
                      "rose by more than the total increase.")

    # failure reasons
    reasons = {}
    for r in raw["reasons"]:
        reasons.setdefault(r["month"], {})[r["failure_reason"]] = r["failed"]
    gw_t = reasons.get(target, {}).get("gateway_timeout", 0)
    gw_b = mean(reasons.get(m, {}).get("gateway_timeout", 0) for m in base)

    # tickets
    cats = {}
    for r in raw["tickets"]:
        cats.setdefault(r["category"], {})[r["month"]] = r["tickets"]
    tickets = {}
    for c, d in cats.items():
        b = mean(d.get(m, 0) for m in base)
        t = d.get(target, 0)
        tickets[c] = {"this_month": t, "baseline_avg": round(b, 1),
                      "change_pct": round(100 * (t - b) / b, 1) if b else None}

    # incidents that started in the target month
    incidents = [{"id": i["incident_id"], "service": i["service"],
                  "severity": i["severity"], "start": i["start_time"],
                  "end": i["end_time"], "description": i["description"]}
                 for i in raw["incidents"] if i["start_time"][:7] == target]

    # confidence: simple, visible rules (not decided by the model)
    pay_t = tickets.get("payment", {})
    points = {
        "payment-linked cancellations explain at least half of the increase":
            share is not None and share >= 50,
        "a failure reason that never appeared before showed up this month":
            gw_t > 0 and gw_b == 0,
        "payment tickets rose by at least 50%":
            (pay_t.get("change_pct") or 0) >= 50,
        "a payment-related incident started this month":
            any("payment" in i["service"] for i in incidents),
    }
    score = sum(points.values())
    label = "High" if score == 4 else "Medium" if score >= 2 else "Low"

    return {
        "month": target,
        "baseline": f"{base[0]} to {base[-1]} (average of {len(base)} months)",
        "cancellations": {
            "this_month": canc[target], "baseline_avg": round(avg(canc), 1),
            "increase": round(inc, 1),
            "increase_pct": round(100 * inc / avg(canc), 1),
            "previous_month": canc[prev]},
        "cancellations_after_failed_payment": {
            "this_month": linked.get(target, 0), "baseline_avg": round(avg(linked), 1),
            "increase": round(linked_inc, 1),
            "share_of_total_increase_pct": share, "note": share_note},
        "cancellations_without_failed_payment": {
            "this_month": other_t, "baseline_avg": round(other_b, 1)},
        "payment_failures": {
            "fail_pct_this_month": fail_pct.get(target),
            "fail_pct_baseline_avg": round(avg(fail_pct), 1),
            "failed_this_month": failed_n.get(target),
            "failed_baseline_avg": round(avg(failed_n), 1),
            "gateway_timeout_this_month": gw_t,
            "gateway_timeout_baseline_avg": round(gw_b, 1)},
        "tickets_by_category": tickets,
        "incidents_this_month": incidents,
        "confidence": {"label": label, "checks_passed": [k for k, v in points.items() if v],
                       "checks_failed": [k for k, v in points.items() if not v]},
        "caveats": [
            "'After a failed payment' means a failed payment in the 14 days before cancelling; "
            "this window is an assumption.",
            "This shows association, not proof of cause.",
            "The data is synthetic and cleaner than real company data.",
        ],
    }


# ------------------------------------------------------------ 3. write
def ask_model(facts, docs):
    system = ("You are an operations analyst. Write the report using ONLY the facts and "
              "document excerpts provided. Never calculate or invent numbers; copy numbers "
              "exactly as given. If something is not in the facts, say it is not available.")
    user = f"""Question: Why did customer cancellations increase in {facts['month']}?

FACTS (calculated by code, trustworthy):
{json.dumps(facts, indent=2)}

DOCUMENT EXCERPTS:
{json.dumps(docs, indent=2)}

Write the report with exactly these five headings: FINDING, EVIDENCE, ANALYSIS, CONFIDENCE, RECOMMENDATION.
- FINDING: one or two sentences.
- EVIDENCE: 4 to 6 bullets using numbers from the FACTS and naming the documents used.
- ANALYSIS: explain how the evidence connects, and mention the caveats.
- CONFIDENCE: use the label "{facts['confidence']['label']}" and give the reason from the checks.
- RECOMMENDATION: 2 or 3 practical actions."""
    body = json.dumps({"model": MODEL, "stream": False,
                       "options": {"temperature": 0, "num_ctx": 8192},
                       "messages": [{"role": "system", "content": system},
                                    {"role": "user", "content": user}]}).encode()
    req = request.Request(OLLAMA, data=body, headers={"Content-Type": "application/json"})
    with request.urlopen(req, timeout=600) as r:
        return json.load(r)["message"]["content"]


# ------------------------------------------------------------ 4. validate
def numbers_in(text):
    out = set()
    for tok in re.findall(r"\d[\d,]*(?:\.\d+)?", text):
        try:
            out.add(float(tok.replace(",", "")))
        except ValueError:
            pass
    return out


def unverified_numbers(report, facts, docs):
    allowed = numbers_in(json.dumps(facts)) | numbers_in(json.dumps(docs))
    bad = []
    for tok in re.findall(r"\d[\d,]*(?:\.\d+)?", report):
        val = float(tok.replace(",", ""))
        if val < 10 and "." not in tok:
            continue  # ignore tiny whole numbers like list numbering
        if val not in allowed and not any(abs(val - a) < 0.051 for a in allowed):
            bad.append(tok)
    return sorted(set(bad))


# ------------------------------------------------------------ main
def main():
    target = sys.argv[1] if len(sys.argv) > 1 else None
    try:
        raw = gather()
    except error.URLError:
        sys.exit("Cannot reach the backend at 127.0.0.1:8000. Is uvicorn running?")
    target = target or max(r["month"] for r in raw["cancellations"])
    facts = compute(raw, target)
    try:
        docs = gather_docs()
    except error.URLError:
        docs = []

    print("\n=== CALCULATED FACTS (by code) ===")
    print(json.dumps(facts, indent=2))
    print(f"\nCollected {len(docs)} document excerpts. Asking {MODEL} to write the report "
          "(this can take a minute)...\n")

    try:
        report = ask_model(facts, docs)
    except error.URLError:
        sys.exit("Cannot reach Ollama at localhost:11434. Is the Ollama app running?")

    bad = unverified_numbers(report, facts, docs)
    check = ("All numbers in the report appear in the facts."
             if not bad else f"WARNING: numbers not found in the facts: {bad}")

    print("=== REPORT (written by the model) ===")
    print(report)
    print("\n=== NUMBER CHECK (by code) ===")
    print(check)

    out_dir = ROOT / "reports"
    out_dir.mkdir(exist_ok=True)
    out = out_dir / f"investigation_{target}.md"
    out.write_text(f"{report}\n\n---\nNumber check: {check}\n\n"
                   f"Facts used:\n```json\n{json.dumps(facts, indent=2)}\n```\n",
                   encoding="utf-8")
    print(f"\nSaved to {out}")


if __name__ == "__main__":
    main()
