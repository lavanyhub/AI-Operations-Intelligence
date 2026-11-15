"""Audit trail: one readable JSON file per investigation run, saved in reports/audit/.

It records what went in (facts, document excerpts, model, code version) and what
happened (every attempt, the problems the checks found, the final report), so that
anyone can later ask "why does this report say that?" and find the evidence.
It never stores passwords or the .env file. A failure here never stops a run.
"""
import json
import subprocess
from datetime import datetime
from pathlib import Path


def now():
    return datetime.now().isoformat(timespec="seconds")


def _git(root, *args):
    try:
        out = subprocess.run(["git", *args], cwd=str(root), capture_output=True,
                             text=True, timeout=10)
        return out.stdout.strip() if out.returncode == 0 else None
    except Exception:
        return None


def build_record(state, root, model):
    problems = state.get("problems", [])
    stamp = datetime.now()
    changes = _git(root, "status", "--porcelain")
    return {
        "run_id": f"{state['target']}_{stamp.strftime('%Y%m%d-%H%M%S')}",
        "saved_at": stamp.isoformat(timespec="seconds"),
        "month": state["target"],
        "model": model,
        "code_version": {
            "git_commit": _git(root, "rev-parse", "--short", "HEAD"),
            "uncommitted_changes": None if changes is None else bool(changes),
        },
        "confidence": state["facts"]["confidence"],
        "facts": state["facts"],
        "excerpts_given_to_model": state.get("docs", []),
        "attempts": state.get("attempts", []),
        "final": {
            "attempts_used": state.get("attempt"),
            "passed_all_checks": not problems,
            "remaining_problems": problems,
            "report": state.get("report"),
        },
        "report_file": f"investigation_{state['target']}_graph.md",
    }


def write_audit(state, root, model):
    """Save the audit record. Returns the file path, or None if it could not be saved."""
    try:
        out_dir = Path(root) / "reports" / "audit"
        out_dir.mkdir(parents=True, exist_ok=True)
        record = build_record(state, root, model)
        path = out_dir / f"audit_{record['run_id']}.json"
        path.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"[audit] saved to {path}")
        return path
    except Exception as exc:
        print(f"[audit] could not save the audit record: {exc}")
        return None


def list_runs(root):
    """One summary row per saved run, oldest first."""
    rows = []
    for p in sorted((Path(root) / "reports" / "audit").glob("audit_*.json")):
        r = json.loads(p.read_text(encoding="utf-8"))
        rows.append({
            "run_id": r["run_id"],
            "month": r["month"],
            "confidence": r["confidence"]["label"],
            "attempts": r["final"]["attempts_used"],
            "passed": r["final"]["passed_all_checks"],
            "excerpts": len(r["excerpts_given_to_model"]),
        })
    return rows


if __name__ == "__main__":
    runs = list_runs(Path(__file__).resolve().parent.parent)
    if not runs:
        print("No audit records yet.")
    for row in runs:
        print(f"{row['run_id']}  confidence={row['confidence']}  attempts={row['attempts']}  "
              f"passed_all_checks={row['passed']}  excerpts={row['excerpts']}")
