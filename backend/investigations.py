"""Runs the investigation agent as a background job and exposes it over HTTP.

POST /investigations       {"month": "2026-10"}  -> starts a run (one at a time)
GET  /investigations       -> list of runs since the server started
GET  /investigations/{id}  -> status, progress lines and, when finished, the report

The agent (scripts/investigate_graph.py) is run as a separate process, so none of
its code is changed. Its printed progress lines are collected for the dashboard,
and the finished report is read from the file the agent saves in reports/.
"""
import json
import os
import re
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parent.parent      # project folder (parent of backend/)
SCRIPT = ROOT / "scripts" / "investigate_graph.py"
MONTH_RE = re.compile(r"^20\d\d-(0[1-9]|1[0-2])$")

router = APIRouter()
_jobs = {}
_lock = threading.Lock()


class StartRequest(BaseModel):
    month: str


def _parse_report(text):
    """Split the saved report file into report, checks line, run trace and facts."""
    report, _, rest = text.partition("\n\n---\nChecks after")
    result = {"report": report.strip(), "checks": None, "passed": None,
              "attempts": None, "trace": [], "facts": None}
    if not rest:
        return result
    checks_part, _, after = rest.partition("\n\nRun trace:\n")
    result["checks"] = ("Checks after" + checks_part).strip()
    result["passed"] = "Final report passed all checks." in checks_part
    m = re.match(r"\s*(\d+) attempt", checks_part)
    result["attempts"] = int(m.group(1)) if m else None
    trace_part, _, facts_part = after.partition("\n\nFacts used:\n")
    result["trace"] = [ln[2:] for ln in trace_part.splitlines() if ln.startswith("- ")]
    fm = re.search(r"```json\n(.*?)\n```", facts_part, re.S)
    if fm:
        try:
            result["facts"] = json.loads(fm.group(1))
        except ValueError:
            pass
    return result


def _run(job):
    try:
        env = dict(os.environ, PYTHONIOENCODING="utf-8")
        proc = subprocess.Popen(
            [sys.executable, "-u", str(SCRIPT), job["month"]],
            cwd=str(ROOT), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace")
        for line in proc.stdout:
            if line.strip():
                job["lines"].append(line.rstrip())
        code = proc.wait()
        out = ROOT / "reports" / f"investigation_{job['month']}_graph.md"
        if code == 0 and out.exists() and out.stat().st_mtime >= job["started_at"] - 1:
            job.update(_parse_report(out.read_text(encoding="utf-8")))
            job["status"] = "done"
        else:
            job["status"] = "failed"
            job["error"] = "\n".join(job["lines"][-3:]) or f"The agent exited with code {code}."
    except Exception as exc:                      # e.g. python or the script not found
        job["status"] = "failed"
        job["error"] = str(exc)
    finally:
        job["finished_at"] = time.time()


def _public(job):
    return dict(job, lines=list(job["lines"]))


@router.post("/investigations")
def start_investigation(req: StartRequest):
    if not MONTH_RE.match(req.month):
        raise HTTPException(422, "month must look like 2026-10")
    with _lock:
        running = next((j for j in _jobs.values() if j["status"] == "running"), None)
        if running:
            raise HTTPException(409, detail={
                "message": "An investigation is already running. Wait for it to finish.",
                "id": running["id"]})
        job = {"id": uuid.uuid4().hex[:8], "month": req.month, "status": "running",
               "started_at": time.time(), "finished_at": None, "lines": [],
               "report": None, "checks": None, "passed": None, "attempts": None,
               "trace": [], "facts": None, "error": None}
        _jobs[job["id"]] = job
    threading.Thread(target=_run, args=(job,), daemon=True).start()
    return {"id": job["id"], "month": job["month"], "status": job["status"]}


@router.get("/investigations")
def list_investigations():
    return [{"id": j["id"], "month": j["month"], "status": j["status"],
             "started_at": j["started_at"], "finished_at": j["finished_at"]}
            for j in sorted(_jobs.values(), key=lambda j: j["started_at"], reverse=True)]


@router.get("/investigations/{job_id}")
def get_investigation(job_id: str):
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(404, "No such investigation")
    return _public(job)
