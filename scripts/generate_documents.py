"""
generate_documents.py -- writes the NovaFlow text documents (Markdown files).

Run from the project root (after generate_data.py has created incidents.csv):
    python scripts/generate_documents.py

Folders created under data/documents/:
    incident_reports/   one report per incident in incidents.csv
    release_notes/      one file per month, Jan-Oct 2026
    support_policies/   how support handles payment failures and cancellations
    product_docs/       how billing and renewals work
    internal_reports/   September and mid-October operations reports

Like the CSVs, these files contain evidence but never state a conclusion
like "the gateway caused the cancellations". The agent has to work that out.
"""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
DOCS = ROOT / "data" / "documents"


def write(folder, name, text):
    d = DOCS / folder
    d.mkdir(parents=True, exist_ok=True)
    (d / name).write_text(text.strip() + "\n", encoding="utf-8")


# ----------------------------------------------------------- incident reports
GENERIC = {
    "login": ("A configuration change slowed the authentication service.",
              "The change was reverted and login times returned to normal."),
    "dashboard": ("A slow database query affected the dashboard charts.",
                  "The query was optimized and the cache was cleared."),
    "api": ("A traffic spike exceeded the API rate-limit settings.",
            "Rate limits were adjusted and extra capacity was added."),
    "search": ("The search index fell behind after a large data import.",
               "The index was rebuilt and monitoring was added."),
    "workflows": ("The job scheduler stalled after a node restart.",
                  "The scheduler was restarted and queued jobs were re-run."),
}

CUSTOM = {
    "INC-007": """
## Summary
After the October 1 release, which upgraded our payment gateway integration, card
payments failed at a high rate for about four hours. Customers trying to pay or
renew during this window saw errors or timeouts at checkout.

## Timeline
- 08:30 Release 2026.10 deployed, including the new payment gateway integration.
- 09:00 Alerts fired for a rising checkout error rate.
- 09:20 Incident declared (severity: critical).
- 11:10 The new timeout setting was identified as a suspect.
- 12:40 The timeout setting was rolled back.
- 13:00 Checkout error rate fell but did not return fully to normal.

## Preliminary root cause
The new integration used a shorter request timeout than the gateway needs to
respond under load. Requests were cancelled before the gateway could confirm them.

## Customer impact
Customers paying or renewing during the window saw failures. The number of
affected customers has not been calculated yet.

## Follow-up actions
- Investigate remaining intermittent timeouts (see INC-008).
- Review whether automatic payment retries ran as designed during the window.
- Add a gateway timeout check to the release checklist.
""",
    "INC-008": """
## Summary
After the INC-007 rollback, the payment gateway kept timing out intermittently.
A hotfix on October 2 reduced the problem but did not remove it. A permanent fix
was released on the evening of October 14.

## Timeline
- Oct 2, 08:00 Hotfix deployed; failure rate improved but stayed above normal.
- Oct 3-10 Intermittent gateway timeouts continued. A ticket was opened with the
  gateway vendor.
- Oct 14, 18:00 Vendor-side fix and configuration update released. Incident closed.

## Customer impact
An elevated share of payment attempts failed during this period. Support received
tickets about payment errors and failed renewals.

## Follow-up actions
- Agree on a response-time commitment with the gateway vendor.
- Add alerting on the payment failure rate.
""",
}


def incident_reports():
    with open(RAW / "incidents.csv", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            iid = row["incident_id"]
            body = CUSTOM.get(iid)
            if body is None:
                cause, fix = GENERIC.get(row["service"], ("Under investigation.", "Resolved."))
                body = f"""
## Summary
{row['description']}.

## Root cause
{cause}

## Resolution
{fix}

## Customer impact
Limited. A small number of support tickets were received.
"""
            header = f"""# Incident report {iid}

- Service: {row['service']}
- Severity: {row['severity']}
- Start: {row['start_time']}
- End: {row['end_time']}
"""
            write("incident_reports", f"{iid}.md", header + body)


# ---------------------------------------------------------------- release notes
RELEASES = {
    1: ["Faster workflow editor", "Fixed CSV export for large reports"],
    2: ["New dashboard widgets", "Improved login speed"],
    3: ["API rate-limit controls", "Bulk user import"],
    4: ["Role-based permissions (beta)", "Fixed duplicate workflow runs"],
    5: ["Search improvements", "New invoice download page"],
    6: ["Scheduled workflow retries", "Dashboard performance improvements"],
    7: ["Slack notifications", "Audit log for admin actions"],
    8: ["Dashboard loading time reduced", "Fixed report date filters"],
    9: ["Updated pricing page and new annual plan discount", "Improved onboarding checklist"],
    10: ["Payment gateway integration upgraded to the vendor's v2 API "
         "(new retry logic, shorter request timeout)", "Minor dashboard fixes"],
}


def release_notes():
    for month, items in RELEASES.items():
        bullets = "\n".join(f"- {i}" for i in items)
        write("release_notes", f"release_2026_{month:02d}.md",
              f"# NovaFlow release notes - 2026-{month:02d}-01\n\n{bullets}\n")


# -------------------------------------------------------------------- policies
def policies_and_docs():
    write("support_policies", "payment_failures.md", """
# Support policy: failed payments

1. Check the status page and open incidents before replying. If a payment
   gateway incident is open, tell the customer we are aware of the problem.
2. Failed renewals are retried automatically up to 3 times over 7 days.
3. A subscription stays active during a 7-day grace period after a failed renewal.
4. If the customer's card is declined or expired, ask them to update it in
   Billing settings.
5. If the customer was charged but the subscription shows unpaid, escalate to
   the billing team with the payment ID.
6. Tag every payment-related ticket with category "payment" so the monthly
   report can count them.
""")
    write("support_policies", "cancellations.md", """
# Support policy: cancellation requests

1. Ask the customer for the main reason for cancelling and record it.
2. Offer a plan downgrade or a pause before processing the cancellation.
3. Cancellations take effect at the end of the paid period unless the customer
   asks otherwise.
4. Never promise refunds for failed-payment cases. Escalate them to billing.
""")
    write("product_docs", "billing_and_renewals.md", """
# Billing and renewals

- NovaFlow plans are billed monthly on the customer's signup day (day 28 at most).
- Plans: Basic (199), Pro (499) and Enterprise (1499) per month.
- Payments go through our external payment gateway.
- If a renewal payment fails, the system retries up to 3 times over 7 days.
  The subscription stays active during this grace period.
- Customers can cancel at any time from Account settings.
""")


# ------------------------------------------------------------ internal reports
def internal_reports():
    write("internal_reports", "monthly_operations_2026_09.md", """
# Monthly operations report - September 2026

- Payments processed: 40,365 (2.0% failed)
- Cancellations: 1,230
- Open incidents at month end: none
- Notes: Pricing page update shipped on Sept 1. Support volume was normal.
""")
    write("internal_reports", "monthly_operations_2026_10_midmonth.md", """
# Operations report - October 2026 (mid-month draft)

- Payments processed so far this month: about 39,000 (6.0% failed)
- Cancellations this month: 1,659
- Incidents: INC-007 (critical) and INC-008 (high), both on the payment gateway
- Notes: Engineering is still investigating the October 1 release. Support
  reports a higher number of payment-related tickets than usual. No overall
  conclusion has been reached about what is driving cancellations.
""")


if __name__ == "__main__":
    incident_reports()
    release_notes()
    policies_and_docs()
    internal_reports()
    n = sum(1 for _ in DOCS.rglob("*.md"))
    print(f"Wrote {n} documents to {DOCS}")
