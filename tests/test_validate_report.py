import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from validate_report import causal_words


def test_real_claim_is_flagged():
    assert causal_words("Cancellations rose due to the outage.") == ["due to"]


def test_negated_claim_is_not_flagged():
    text = "The increase is not solely due to failed payments."
    assert causal_words(text) == []


def test_other_causal_phrases_are_flagged():
    assert causal_words("The gateway caused by the release failed.") == ["caused by"]
    assert causal_words("It happened because of the timeout.") == ["because of"]


def test_never_caused_by_is_not_flagged():
    assert causal_words("This was never caused by pricing.") == []


def test_negation_in_an_earlier_sentence_does_not_hide_a_claim():
    text = "Pricing did not change. Cancellations rose due to the outage."
    assert causal_words(text) == ["due to"]


def test_clean_report_has_no_causal_words():
    assert causal_words("Cancellations were linked to the gateway failures.") == []


from validate_report import names_release


def test_release_named_date_first():
    assert names_release("After the October 1 release, payment failures rose.")


def test_release_named_release_first():
    assert names_release("The release on October 1 upgraded the gateway integration.")


def test_release_named_iso_date():
    assert names_release("Release notes of 2026-10-01 mention a shorter timeout.")


def test_release_checklist_alone_does_not_count():
    assert not names_release("Add a gateway timeout check to the release checklist (INC-007).")


def test_date_without_release_does_not_count():
    assert not names_release("The issue started on October 1 and ended on October 14.")


def test_previous_report_text_fails_the_check():
    old = ("The timeline of the incident shows that the issue started on October 1 and was not "
           "fully resolved until October 14 (INC-007). Add a gateway timeout check to the "
           "release checklist (INC-007).")
    assert not names_release(old)


from validate_report import wrong_source_dates, root_cause_overstated, finding_names_cause

DOCS = [
    {"document": "incident_reports/INC-007.md",
     "text": "# Incident report INC-007\n## Summary\nAfter the October 1 release, which upgraded our payment gateway integration, card payments failed."},
    {"document": "incident_reports/INC-008.md",
     "text": "# Incident report INC-008\n## Summary\nA hotfix on October 2 reduced the problem. A permanent fix was released on the evening of October 14."},
    {"document": "release_notes/release_2026_10.md", "text": "# Release notes 2026-10-01 - gateway upgraded"},
]


def test_date_from_other_incident_is_flagged():
    text = "The issue started on October 1 and was not resolved until October 14 (INC-007)."
    assert wrong_source_dates(text, DOCS) == ["October 14 is cited to INC-007, but it comes from INC-008"]


def test_correct_dates_pass():
    assert wrong_source_dates("The release came on October 1 (INC-007).", DOCS) == []
    assert wrong_source_dates("A permanent fix came on October 14 (INC-008).", DOCS) == []


def test_two_incidents_cited_together_pass():
    assert wrong_source_dates("Both incidents (INC-007 and INC-008) ran from October 1 to October 14.", DOCS) == []


def test_date_in_no_incident_is_not_flagged():
    assert wrong_source_dates("Something happened on October 20 (INC-007).", DOCS) == []


def test_iso_dates_are_understood():
    assert wrong_source_dates("It ended on 2026-10-14 (INC-007).", DOCS) == ["October 14 is cited to INC-007, but it comes from INC-008"]


def test_root_cause_without_preliminary_is_flagged():
    assert root_cause_overstated("The root cause was identified as a shorter timeout.")


def test_preliminary_root_cause_passes():
    assert root_cause_overstated("The preliminary root cause was a shorter timeout.") == []
    assert root_cause_overstated("The timeout is the likely explanation.") == []


def test_finding_without_cause_is_flagged():
    report = "**FINDING**\nCancellations increased by 39%.\n\n**EVIDENCE**\n- payment failures"
    assert not finding_names_cause(report)


def test_finding_with_cause_passes():
    report = "**FINDING**\nCancellations rose 39%, linked to the payment gateway problems.\n\n**EVIDENCE**\n- x"
    assert finding_names_cause(report)


def test_report_without_finding_section_is_skipped():
    assert finding_names_cause("No sections here.")
