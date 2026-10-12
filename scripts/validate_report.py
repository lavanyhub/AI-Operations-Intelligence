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


# The October 1 release is the key event in this project's story. The report must
# name it, meaning "release" appears close to the release date (either order).
# Just the word "release" is not enough: "release checklist" would pass by accident.
RELEASE_DATE = r"(?:October 1(?!\d)|Oct 1(?!\d)|2026-10-01|1 October)"
RELEASE_NAMED = re.compile(
    rf"{RELEASE_DATE}\W+(?:\w+\W+){{0,6}}release\b"
    rf"|\brelease\b\W+(?:\w+\W+){{0,6}}{RELEASE_DATE}"
    r"|\brelease\s+2026\.10\b",
    re.I,
)


def names_release(report):
    """True if the report names the October 1 release."""
    return bool(RELEASE_NAMED.search(report))


# ---------------------------------------------------------------- wrong source dates
MONTHS = ["january", "february", "march", "april", "may", "june", "july",
          "august", "september", "october", "november", "december"]
DATE_RE = re.compile(
    r"\b(" + "|".join(MONTHS) + r")\s+(\d{1,2})(?!\d)|\b\d{4}-(\d{2})-(\d{2})\b", re.I)


def _dates(text):
    """All dates in a text as (month, day) pairs, from 'October 14' or '2026-10-14'."""
    out = set()
    for m in DATE_RE.finditer(text):
        if m.group(1):
            out.add((MONTHS.index(m.group(1).lower()) + 1, int(m.group(2))))
        else:
            out.add((int(m.group(3)), int(m.group(4))))
    return out


def _sentences(report):
    return [s for s in re.split(r"(?<=[.!?])\s+|\n+", report) if s.strip()]


def wrong_source_dates(report, docs):
    """Dates cited to one incident that appear only in a DIFFERENT incident's text.
    Conservative: a date found in no incident text is not flagged."""
    by_incident = {}
    for d in docs:
        m = re.search(r"INC-\d{3}", d["document"])
        if m:
            by_incident.setdefault(m.group(0), set()).update(_dates(d["text"]))
    problems = []
    for sentence in _sentences(report):
        cited = set(re.findall(r"INC-\d{3}", sentence))
        if not cited:
            continue
        allowed = set().union(*[by_incident.get(c, set()) for c in cited])
        for date in sorted(_dates(sentence)):
            owners = sorted(i for i, ds in by_incident.items() if i not in cited and date in ds)
            if date not in allowed and owners:
                problems.append(f"{MONTHS[date[0] - 1].capitalize()} {date[1]} is cited to "
                                f"{', '.join(sorted(cited))}, but it comes from {', '.join(owners)}")
    return sorted(set(problems))


# ---------------------------------------------------------------- root cause wording
_ACTION_BEFORE_ROOT_CAUSE = re.compile(
    r"\b(identify|investigate|find|determine|confirm|establish|uncover|understand|diagnose)\b"
    r"(?:\W+\w+){0,3}?\W+root cause", re.I)


def root_cause_overstated(report):
    """Sentences that claim a 'root cause' without 'preliminary' (the incident report only
    calls it a preliminary root cause). Sentences that only recommend finding it,
    like 'identify the root cause', are not claims and are skipped."""
    return [s.strip() for s in _sentences(report)
            if re.search(r"root cause", s, re.I)
            and not re.search(r"preliminary", s, re.I)
            and not _ACTION_BEFORE_ROOT_CAUSE.search(s)]

# ---------------------------------------------------------------- FINDING gives the why
def finding_names_cause(report):
    """The FINDING section should say what the increase is linked to. Skipped (True)
    when the report has no FINDING section."""
    m = re.search(r"\*\*FINDING\*\*(.*?)\*\*EVIDENCE\*\*", report, re.S | re.I)
    if not m:
        return True
    return bool(re.search(r"payment|gateway", m.group(1), re.I))
