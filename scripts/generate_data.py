"""
generate_data.py  --  builds the NovaFlow dataset (6 connected CSV files).

Usage (from the project root):
    python scripts/generate_data.py            # 100 customers (quick test)
    python scripts/generate_data.py 2000       # 2,000 customers
    python scripts/generate_data.py 50000      # full dataset

Only uses Python's standard library. No pip install needed.

The hidden story:
  - Oct 1 2026: a payment gateway deployment goes wrong (4-hour outage).
  - Oct 2-14: the gateway stays flaky, so payment failures stay high.
  - Failed payments -> support tickets -> some customers cancel.
  - Nothing in the files says "the gateway caused the cancellations".
    The evidence is spread across payments, tickets, events, incidents.
"""
import csv
import random
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

# ---------------------------------------------------------------- settings
NUM_CUSTOMERS = int(sys.argv[1]) if len(sys.argv) > 1 else 100
random.seed(42)  # same seed = same data every run

OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
OUT_DIR.mkdir(parents=True, exist_ok=True)

SIM_START = date(2026, 1, 1)   # we simulate billing from here...
SIM_END = date(2026, 10, 31)   # ...to here. October is "this month".

BASE_FAILURE_RATE = 0.021      # normal: 2.1% of payments fail
OUTAGE_DAY = date(2026, 10, 1)
OUTAGE_FAILURE_RATE = 0.40     # during the outage day
DEGRADED_START = date(2026, 10, 2)
DEGRADED_END = date(2026, 10, 14)
DEGRADED_FAILURE_RATE = 0.08   # flaky gateway afterwards

CANCEL_AFTER_FAILED_PAYMENT = 0.30   # chance a customer cancels after a failed payment
BASE_CANCEL_RATE = 0.025             # normal monthly cancellation chance (other reasons)
TICKET_AFTER_FAILED_PAYMENT = 0.40   # chance a failed payment produces a ticket

# ------------------------------------------------------------ lookup lists
PREFIXES = ["Acme", "Beta", "Nimbus", "Orbit", "Vertex", "Pioneer", "Summit",
            "Bluepeak", "Ironclad", "Lumen", "Zenith", "Harbor", "Quantum", "Atlas"]
SUFFIXES = ["Ltd", "Corp", "Inc", "Systems", "Labs", "Group", "Solutions", "Partners"]
INDUSTRIES = ["Technology", "Finance", "Healthcare", "Retail", "Manufacturing",
              "Logistics", "Education", "Media"]
COUNTRIES = ["India", "USA", "UK", "Germany", "Singapore", "UAE", "Canada", "Australia"]
COMPANY_SIZES = [10, 25, 50, 100, 200, 500, 1000]

PLANS = {"Basic": 199, "Pro": 499, "Enterprise": 1499}
PLAN_WEIGHTS = [0.50, 0.35, 0.15]

NORMAL_FAILURE_REASONS = ["card_declined", "insufficient_funds", "expired_card"]

PAYMENT_TICKET_TEXT = [
    "Payment failed", "Unable to renew subscription",
    "Card charged but subscription shows unpaid",
    "Checkout keeps showing an error", "Payment page timed out",
]
OTHER_TICKETS = {
    "technical": ["Dashboard is slow", "Export to CSV not working", "Workflow stuck on step 3"],
    "billing": ["Need a copy of my invoice", "Wrong company name on invoice"],
    "pricing": ["Plan is too expensive for our team", "Asking about a discount"],
    "feature_request": ["Please add Slack integration", "Need role-based permissions"],
    "account": ["Cannot reset password", "Add a new user to our account"],
}
EVENT_TYPES = [("login", "dashboard"), ("dashboard_view", "dashboard"),
               ("workflow_created", "workflows"), ("report_exported", "reports"),
               ("api_call", "api")]


# ------------------------------------------------------------------ helpers
def month_starts():
    d = SIM_START
    while d <= SIM_END:
        yield d
        d = date(d.year + (d.month == 12), d.month % 12 + 1, 1)


def month_end(d):
    nxt = date(d.year + (d.month == 12), d.month % 12 + 1, 1)
    return min(nxt - timedelta(days=1), SIM_END)


def random_date(start, end):
    if end < start:
        return start
    return start + timedelta(days=random.randint(0, (end - start).days))


def random_datetime_on(d):
    return datetime(d.year, d.month, d.day, random.randint(7, 20), random.randint(0, 59))


def failure_rate_on(d):
    if d == OUTAGE_DAY:
        return OUTAGE_FAILURE_RATE
    if DEGRADED_START <= d <= DEGRADED_END:
        return DEGRADED_FAILURE_RATE
    return BASE_FAILURE_RATE


def failure_reason_on(d):
    if OUTAGE_DAY <= d <= DEGRADED_END:
        # mostly gateway problems during the incident, a few normal ones mixed in
        if random.random() < 0.8:
            return "gateway_timeout"
    return random.choice(NORMAL_FAILURE_REASONS)


# --------------------------------------------------------------------- main
def main():
    files = {}
    writers = {}

    def open_csv(name, header):
        f = open(OUT_DIR / f"{name}.csv", "w", newline="", encoding="utf-8")
        files[name] = f
        w = csv.writer(f)
        w.writerow(header)
        writers[name] = w

    open_csv("customers", ["customer_id", "name", "industry", "country", "company_size", "signup_date"])
    open_csv("subscriptions", ["subscription_id", "customer_id", "plan", "start_date", "end_date", "status", "monthly_price"])
    open_csv("payments", ["payment_id", "customer_id", "date", "amount", "status", "failure_reason"])
    open_csv("support_tickets", ["ticket_id", "customer_id", "created_at", "category", "priority", "description", "status"])
    open_csv("product_events", ["event_id", "customer_id", "timestamp", "event_type", "product"])
    open_csv("incidents", ["incident_id", "start_time", "end_time", "service", "severity", "description"])

    n_pay = n_tkt = n_evt = 0
    # for the summary at the end
    stats = {m: {"pay": 0, "fail": 0, "cancel": 0} for m in month_starts()}

    def add_ticket(customer_id, created, category, text, priority):
        nonlocal n_tkt
        n_tkt += 1
        status = "open" if (SIM_END - created.date()).days < 5 and random.random() < 0.5 else "closed"
        writers["support_tickets"].writerow(
            [f"T{n_tkt:07d}", customer_id, created.strftime("%Y-%m-%d %H:%M"),
             category, priority, text, status])

    def add_event(customer_id, ts, etype, product):
        nonlocal n_evt
        n_evt += 1
        writers["product_events"].writerow(
            [f"E{n_evt:08d}", customer_id, ts.strftime("%Y-%m-%d %H:%M:%S"), etype, product])

    for i in range(1, NUM_CUSTOMERS + 1):
        customer_id = f"C{i:05d}"
        signup = random_date(date(2024, 1, 1), date(2026, 9, 30))
        writers["customers"].writerow([
            customer_id, f"{random.choice(PREFIXES)} {random.choice(SUFFIXES)}",
            random.choice(INDUSTRIES), random.choice(COUNTRIES),
            random.choice(COMPANY_SIZES), signup.isoformat()])

        plan = random.choices(list(PLANS), weights=PLAN_WEIGHTS)[0]
        price = PLANS[plan]
        bill_day = min(signup.day, 28)
        cancel_date = None

        for m_start in month_starts():
            bill_date = date(m_start.year, m_start.month, bill_day)
            if bill_date < signup:
                continue  # not a customer yet this month

            # ---- payment
            failed = random.random() < failure_rate_on(bill_date)
            n_pay += 1
            stats[m_start]["pay"] += 1
            if failed:
                stats[m_start]["fail"] += 1
                reason = failure_reason_on(bill_date)
                writers["payments"].writerow([f"P{n_pay:07d}", customer_id, bill_date.isoformat(), price, "failed", reason])
                add_event(customer_id, random_datetime_on(bill_date), "payment_failed", "checkout")
                if random.random() < TICKET_AFTER_FAILED_PAYMENT:
                    created = random_datetime_on(bill_date + timedelta(days=random.randint(0, 2)))
                    add_ticket(customer_id, created, "payment", random.choice(PAYMENT_TICKET_TEXT),
                               random.choice(["high", "high", "medium"]))
            else:
                writers["payments"].writerow([f"P{n_pay:07d}", customer_id, bill_date.isoformat(), price, "success", ""])

            # ---- cancellation decision
            cancel_chance = CANCEL_AFTER_FAILED_PAYMENT if failed else BASE_CANCEL_RATE
            cancelling = random.random() < cancel_chance
            m_end = month_end(m_start)
            if cancelling:
                if failed:
                    cancel_date = min(bill_date + timedelta(days=random.randint(1, 10)), SIM_END)
                else:
                    cancel_date = random_date(bill_date, m_end)
                stats[date(cancel_date.year, cancel_date.month, 1)]["cancel"] += 1
                # customers leaving for other reasons sometimes complain first
                if not failed and random.random() < 0.3:
                    cat = random.choice(["pricing", "technical", "feature_request"])
                    created = random_datetime_on(max(bill_date, cancel_date - timedelta(days=5)))
                    add_ticket(customer_id, created, cat, random.choice(OTHER_TICKETS[cat]), "medium")

            # ---- everyday support tickets (small background noise)
            if random.random() < 0.03:
                cat = random.choice(list(OTHER_TICKETS))
                add_ticket(customer_id, random_datetime_on(random_date(max(bill_date, signup), m_end)),
                           cat, random.choice(OTHER_TICKETS[cat]), random.choice(["low", "medium"]))

            # ---- product usage (people about to leave use the product less)
            usage_end = cancel_date if cancel_date else m_end
            n_events = random.randint(0, 3) if cancelling else random.randint(3, 10)
            for _ in range(n_events):
                etype, product = random.choice(EVENT_TYPES)
                add_event(customer_id, random_datetime_on(random_date(max(bill_date, signup), usage_end)), etype, product)

            if cancelling:
                break  # no more billing after cancelling

        writers["subscriptions"].writerow([
            f"S{i:05d}", customer_id, plan, signup.isoformat(),
            cancel_date.isoformat() if cancel_date else "",
            "cancelled" if cancel_date else "active", price])

    # ---- incidents (not owned by one customer)
    incidents = [
        ("INC-001", "2026-01-14 02:00", "2026-01-14 03:30", "login", "medium", "Login service slow during maintenance"),
        ("INC-002", "2026-02-09 11:00", "2026-02-09 11:45", "dashboard", "low", "Dashboard charts failed to load"),
        ("INC-003", "2026-03-22 08:15", "2026-03-22 10:00", "api", "medium", "Elevated API error rates"),
        ("INC-004", "2026-05-05 14:00", "2026-05-05 15:10", "search", "low", "Search results delayed"),
        ("INC-005", "2026-06-18 01:00", "2026-06-18 02:20", "workflows", "medium", "Scheduled workflows ran late"),
        ("INC-006", "2026-08-03 16:30", "2026-08-03 17:15", "dashboard", "low", "Slow dashboard after release"),
        ("INC-007", "2026-10-01 09:00", "2026-10-01 13:00", "payment_gateway", "critical",
         "Payment gateway failures after deployment; 4 hour outage"),
        ("INC-008", "2026-10-02 08:00", "2026-10-14 18:00", "payment_gateway", "high",
         "Intermittent payment gateway timeouts after hotfix"),
    ]
    for row in incidents:
        writers["incidents"].writerow(row)

    for f in files.values():
        f.close()

    # ---- summary so you can SEE the hidden story
    print(f"\nWrote files to: {OUT_DIR}")
    print(f"customers={NUM_CUSTOMERS}  payments={n_pay}  tickets={n_tkt}  events={n_evt}\n")
    print(f"{'month':<9}{'payments':>10}{'fail %':>9}{'cancellations':>15}")
    for m, s in stats.items():
        rate = 100 * s["fail"] / s["pay"] if s["pay"] else 0
        print(f"{m.strftime('%Y-%m'):<9}{s['pay']:>10}{rate:>8.1f}%{s['cancel']:>15}")


if __name__ == "__main__":
    main()
