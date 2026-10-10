"""Deterministic checks on a finished report (plain code, no AI)."""
import re

CAUSAL = re.compile(r"\b(caused by|due to|because of|proved|proves)\b", re.I)

# a negation shortly before the causal phrase means the sentence DENIES a cause,
# for example "not solely due to" or "was never caused by"
NEGATION_BEFORE = re.compile(r"\b(not|never|no|nor|cannot|can't|isn't|wasn't|doesn't)\b(\W+\w+){0,2}\W*$", re.I)


def causal_words(report):
    """Causal phrases the report really uses to CLAIM a cause (negated ones are ignored)."""
    found = set()
    for m in CAUSAL.finditer(report):
        before = report[max(0, m.start() - 40):m.start()]
        if NEGATION_BEFORE.search(before):
            continue
        found.add(m.group(1).lower())
    return sorted(found)