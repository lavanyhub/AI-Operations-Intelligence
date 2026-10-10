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