FINDING
Customer cancellations increased in 2026-10, with 1659 cancellations against a normal 1193.3 per month, an increase of 465.7 (39.0%). This increase is linked to the payment gateway problems after the October 1 release.

EVIDENCE
• Cancellations that came after a failed payment increased by 518.2, which equals 111.3% of the total increase of 465.7. This is because cancellations without a failed payment fell from a normal 957.6 to 905.
• The payment failure rate was 6.0% against a normal 2.1%, with 2358 failed payments against a normal 807.6.
• Failures with reason gateway_timeout increased to 1506 this month, against 0 in a normal month.
• Payment tickets rose by 187.3% to 931 against a normal 324.
• No other ticket category changed by more than 7.7%, including pricing (0.6%).

ANALYSIS
The evidence suggests that the payment gateway problems after the October 1 release led to an increase in cancellations. The preliminary root cause of the payment gateway failures was a shorter request timeout than the gateway needs to respond under load (INC-007). The likely explanation is that requests were cancelled before the gateway could confirm them. After the October 1 release, the payment gateway integration was upgraded to the vendor's v2 API, which included new retry logic and a shorter request timeout (release_notes/release_2026_10.md). This change was followed by a 4-hour outage on October 1 (INC-007) and intermittent payment gateway timeouts after a hotfix on October 2 (INC-008). The increase in cancellations after a failed payment is likely linked to the payment gateway problems, as customers trying to pay or renew during the window saw errors or timeouts at checkout (INC-007). The assumption is that "after a failed payment" means a failed payment in the 14 days before cancelling, and this window is an assumption. The data shows association, not proof of cause.

CONFIDENCE
The confidence in this finding is High, as the following checks passed:
- Payment-linked cancellations explain at least half of the increase.
- A failure reason that never appeared before showed up this month (gateway_timeout).
- Payment tickets rose by at least 50%.
- A payment-related incident started this month (INC-007).

RECOMMENDATION
Based on the follow-up actions in the documents, the following actions are recommended:
- Investigate remaining intermittent timeouts (INC-008).
- Review whether automatic payment retries ran as designed during the window (INC-007).
- Add a gateway timeout check to the release checklist (INC-007).

---
Checks after 1 attempt(s): Final report passed all checks.

Run trace:
- gather_evidence: 6 endpoints read, month 2026-10
- calculate: confidence High
- find_documents: 12 excerpts
- write: attempt 1
- check: clean

Facts used:
```json
{
  "month": "2026-10",
  "baseline": "2026-01 to 2026-09 (average of 9 months)",
  "cancellations": {
    "this_month": 1659,
    "baseline_avg": 1193.3,
    "increase": 465.7,
    "increase_pct": 39.0,
    "previous_month": 1230
  },
  "cancellations_after_failed_payment": {
    "this_month": 754,
    "baseline_avg": 235.8,
    "increase": 518.2,
    "share_of_total_increase_pct": 111.3,
    "note": "Over 100% because cancellations NOT preceded by a failed payment were slightly lower than usual, so payment-linked cancellations rose by more than the total increase."
  },
  "cancellations_without_failed_payment": {
    "this_month": 905,
    "baseline_avg": 957.6
  },
  "payment_failures": {
    "fail_pct_this_month": 6.0,
    "fail_pct_baseline_avg": 2.1,
    "failed_this_month": 2358,
    "failed_baseline_avg": 807.6,
    "gateway_timeout_this_month": 1506,
    "gateway_timeout_baseline_avg": 0
  },
  "tickets_by_category": {
    "account": {
      "this_month": 225,
      "baseline_avg": 230.4,
      "change_pct": -2.4
    },
    "billing": {
      "this_month": 235,
      "baseline_avg": 227.4,
      "change_pct": 3.3
    },
    "feature_request": {
      "this_month": 343,
      "baseline_avg": 326.2,
      "change_pct": 5.1
    },
    "payment": {
      "this_month": 931,
      "baseline_avg": 324,
      "change_pct": 187.3
    },
    "pricing": {
      "this_month": 334,
      "baseline_avg": 332.1,
      "change_pct": 0.6
    },
    "technical": {
      "this_month": 364,
      "baseline_avg": 337.9,
      "change_pct": 7.7
    }
  },
  "incidents_this_month": [
    {
      "id": "INC-007",
      "service": "payment_gateway",
      "severity": "critical",
      "start": "2026-10-01T09:00:00",
      "end": "2026-10-01T13:00:00",
      "description": "Payment gateway failures after deployment; 4 hour outage"
    },
    {
      "id": "INC-008",
      "service": "payment_gateway",
      "severity": "high",
      "start": "2026-10-02T08:00:00",
      "end": "2026-10-14T18:00:00",
      "description": "Intermittent payment gateway timeouts after hotfix"
    }
  ],
  "confidence": {
    "label": "High",
    "checks_passed": [
      "payment-linked cancellations explain at least half of the increase",
      "a failure reason that never appeared before showed up this month",
      "payment tickets rose by at least 50%",
      "a payment-related incident started this month"
    ],
    "checks_failed": []
  },
  "key_statements": [
    "Cancellations in 2026-10: 1659, against a normal 1193.3 per month. That is 465.7 more (39.0%).",
    "Cancellations that came after a failed payment: 754, against a normal 235.8, an increase of 518.2.",
    "That increase of 518.2 equals 111.3% of the total increase of 465.7. It is over 100% because cancellations without a failed payment fell from a normal 957.6 to 905.",
    "Payment failure rate: 6.0% against a normal 2.1%. Failed payments: 2358 against a normal 807.6.",
    "Failures with reason gateway_timeout: 1506 this month, against 0 in a normal month.",
    "Payment tickets: 931 against a normal 324 (187.3% change).",
    "No other ticket category changed by more than 7.7%, including pricing (0.6%).",
    "Incident INC-007 (payment_gateway, critical) ran from 2026-10-01T09:00:00 to 2026-10-01T13:00:00: Payment gateway failures after deployment; 4 hour outage.",
    "Incident INC-008 (payment_gateway, high) ran from 2026-10-02T08:00:00 to 2026-10-14T18:00:00: Intermittent payment gateway timeouts after hotfix."
  ],
  "required_numbers": [
    1659,
    39.0,
    111.3,
    1506,
    6.0,
    187.3
  ],
  "caveats": [
    "'After a failed payment' means a failed payment in the 14 days before cancelling; this window is an assumption.",
    "This shows association, not proof of cause.",
    "The data is synthetic and cleaner than real company data."
  ]
}
```
