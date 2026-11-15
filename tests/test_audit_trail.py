import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from audit_trail import write_audit, list_runs


def fake_state(problems=None):
    return {
        "target": "2026-10",
        "facts": {"month": "2026-10", "confidence": {"label": "High"}, "key_statements": ["x"]},
        "docs": [{"document": "incident_reports/INC-007.md", "text": "Summary ..."}],
        "attempts": [
            {"attempt": 1, "at": "2026-10-12T10:00:00", "report": "first draft", "problems": ["missing 111.3"]},
            {"attempt": 2, "at": "2026-10-12T10:05:00", "report": "final", "problems": []},
        ],
        "attempt": 2,
        "report": "final",
        "problems": problems or [],
    }


def test_record_has_the_evidence_and_every_attempt(tmp_path):
    path = write_audit(fake_state(), tmp_path, "llama3.1:8b")
    record = json.loads(path.read_text(encoding="utf-8"))
    assert record["month"] == "2026-10"
    assert record["model"] == "llama3.1:8b"
    assert record["confidence"]["label"] == "High"
    assert record["excerpts_given_to_model"][0]["document"] == "incident_reports/INC-007.md"
    assert [a["attempt"] for a in record["attempts"]] == [1, 2]
    assert record["attempts"][0]["problems"] == ["missing 111.3"]
    assert record["final"]["passed_all_checks"] is True
    assert record["final"]["report"] == "final"


def test_a_report_saved_with_problems_is_marked_as_failed(tmp_path):
    path = write_audit(fake_state(problems=["Remove the causal wording ['due to']."]), tmp_path, "m")
    record = json.loads(path.read_text(encoding="utf-8"))
    assert record["final"]["passed_all_checks"] is False
    assert record["final"]["remaining_problems"]


def test_list_runs_summarises_saved_records(tmp_path):
    write_audit(fake_state(), tmp_path, "m")
    rows = list_runs(tmp_path)
    assert len(rows) == 1
    assert rows[0]["attempts"] == 2 and rows[0]["passed"] is True and rows[0]["excerpts"] == 1


def test_list_runs_with_no_records_is_empty(tmp_path):
    assert list_runs(tmp_path) == []


def test_a_failure_to_write_never_raises(tmp_path):
    blocker = tmp_path / "reports"
    blocker.write_text("this is a file, not a folder")   # makes the audit folder impossible
    assert write_audit(fake_state(), tmp_path, "m") is None
