"""
investigate_graph.py -- Phase 7: the investigation rebuilt as a LangGraph graph.

    python scripts/investigate_graph.py              # latest month
    python scripts/investigate_graph.py 2026-10      # a specific month
    python scripts/investigate_graph.py --diagram    # print the graph as a diagram

It REUSES the evidence-gathering, maths and checking functions from
investigate.py (keep that file in the same folder). What is new here is the
structure: each step is a node, and the retry loop is a visible arrow.

    gather_evidence -> calculate -> find_documents -> write -> check
                                                        ^        |
                                                        |   (problems and
                                                      revise <-  tries left)
                                                                 |
                                                       (clean or out of tries)
                                                                 v
                                                               save -> END
"""
import json
import operator
import re
import sys
from typing import Annotated, Literal, TypedDict
from urllib import error, request

from langgraph.graph import END, START, StateGraph

import investigate as iv  # our existing functions
import validate_report as vr  # new, tested checks
import audit_trail as au  # audit trail

MAX_RETRIES = 2  # rewrites allowed after the first attempt


# ------------------------------------------------------------ the notebook
class State(TypedDict, total=False):
    target: str            # month being investigated, e.g. "2026-10"
    raw: dict              # raw answers from the backend
    facts: dict            # numbers calculated by code
    docs: list             # document excerpts
    messages: list         # conversation with the model
    report: str            # latest report
    problems: list         # what the checks found
    attempt: int           # how many times the model has written
    attempts: Annotated[list, operator.add]   # one record per attempt, for the audit trail
    log: Annotated[list, operator.add]   # run trace; each node ADDS lines


# ------------------------------------------------------- model helpers
def build_messages(facts, docs):
    system = ("You are an operations analyst. Write the report using ONLY the briefing and "
              "document excerpts provided. Copy numbers exactly as written. Never calculate or "
              "invent numbers. If something is not provided, say it is not available.")
    briefing = {"key_statements": facts["key_statements"],
                "confidence": facts["confidence"], "caveats": facts["caveats"]}
    # a clear story (Medium or High confidence) gets the story rules; a calm month (Low) must not be given one
    story = facts["confidence"]["label"] != "Low"
    if story:
        finding_rule = ("- FINDING: one or two sentences. Say what happened and what it is linked to "
                        "(the payment gateway problems after the release). EVIDENCE: 5 to 7 bullets. "
                        "ANALYSIS: how the evidence connects, plus the caveats.")
        story_rules = ('- Name the release from the release notes that changed the payment gateway integration '
                       '(for example "after the October 1 release") as what the failures followed.')
    else:
        finding_rule = ("- FINDING: one or two sentences. Say how much cancellations changed and whether the "
                        "evidence points to a clear cause. EVIDENCE: 5 to 7 bullets. "
                        "ANALYSIS: how the evidence connects, plus the caveats.")
        story_rules = ("- The confidence is Low. Say plainly that the change is small or that no clear cause was "
                       "found. Do not invent a cause, an incident or a story that the briefing does not support.")
    user = f"""Question: Why did customer cancellations increase in {facts['month']}?

BRIEFING (calculated by code, trustworthy):
{json.dumps(briefing, indent=2)}

DOCUMENT EXCERPTS:
{json.dumps(docs, indent=2)}

Write the report with exactly these five headings: FINDING, EVIDENCE, ANALYSIS, CONFIDENCE, RECOMMENDATION.
Rules:
- Use the key statements as they are written. Do not restate a number with a different meaning.
- Say "linked to" or "followed", never "caused by" or "due to", because the data shows association only.
- If a statement explains why a share is over 100%, include that explanation.
- Mention whether other ticket categories (including pricing) changed.
- Use the document excerpts for what happened (root cause, timeline) and name the document.
{story_rules}
- The incident report calls the cause a "preliminary root cause". Write "preliminary root cause" or "the likely explanation", never just "the root cause".
- Only attach a date to an incident (INC-...) if that date appears in that incident's own excerpt.
- State that "after a failed payment" means a failed payment in the 14 days before cancelling, and that this window is an assumption.
- Every number in the key statements must appear somewhere in the report.
{finding_rule}
- CONFIDENCE: use the label "{facts['confidence']['label']}" and the checks that passed.
- RECOMMENDATION: 2 or 3 actions taken from the follow-up actions in the documents or directly from the evidence. Do not invent generic advice.
- Do not repeat the same sentence in different sections."""
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def chat(messages):
    body = json.dumps({"model": iv.MODEL, "stream": False,
                       "options": {"temperature": 0, "num_ctx": 8192},
                       "messages": messages}).encode()
    req = request.Request(iv.OLLAMA, data=body, headers={"Content-Type": "application/json"})
    with request.urlopen(req, timeout=600) as r:
        return json.load(r)["message"]["content"]


def find_problems(report, facts, docs):
    problems = []
    story = facts["confidence"]["label"] != "Low"   # story checks only when the evidence shows a story
    bad = iv.unverified_numbers(report, facts, docs)
    if bad:
        problems.append(f"These numbers are not in the briefing: {bad}. Remove or correct them.")
    missing = iv.missing_key_numbers(report, facts)
    if missing:
        problems.append(f"The report must mention these numbers from the briefing: {missing}.")
    causal = vr.causal_words(report)
    if causal:
        problems.append(f"Remove the causal wording {causal}. Use 'linked to' or 'followed'.")
    if story and not vr.names_release(report):
        problems.append("Name the release that changed the payment gateway integration, "
                        "for example 'after the October 1 release' (see the release notes). "
                        "Say 'linked to' or 'followed', not that it caused anything.")
    if not re.search(r"14[- ]day|14 days", report, re.I):
        problems.append("State that 'after a failed payment' means a failed payment in the "
                        "14 days before cancelling, and that this window is an assumption.")
    for wrong_date in vr.wrong_source_dates(report, docs):
        problems.append(f"{wrong_date}. Cite the date to the incident it comes from, "
                        "or leave out the incident reference.")
    if vr.root_cause_overstated(report):
        problems.append("The incident report calls the cause a 'preliminary root cause'. "
                        "Write 'preliminary root cause', or call it 'the likely explanation'.")
    if story and not vr.finding_names_cause(report):
        problems.append("The FINDING must also say what the increase is linked to: the payment "
                        "gateway problems after the October 1 release. Say 'linked to', "
                        "not 'caused by'.")
    return problems


# ------------------------------------------------------------ the nodes
def gather_evidence(state):
    raw = iv.gather()
    target = state.get("target") or max(r["month"] for r in raw["cancellations"])
    print(f"[gather_evidence] collected data from 6 endpoints; investigating {target}")
    return {"raw": raw, "target": target, "attempt": 0,
            "log": [f"gather_evidence: 6 endpoints read, month {target}"]}


def calculate(state):
    facts = iv.compute(state["raw"], state["target"])
    print(f"[calculate] confidence label set by code: {facts['confidence']['label']}")
    return {"facts": facts, "log": [f"calculate: confidence {facts['confidence']['label']}"]}


def find_documents(state):
    try:
        docs = iv.gather_docs(state["target"], state["facts"])
    except error.URLError:
        docs = []
    print(f"[find_documents] {len(docs)} excerpts:")
    for d in docs:
        print("    - " + d["document"] + ": " + " ".join(d["text"].split())[:90] + "...")
    return {"docs": docs, "messages": build_messages(state["facts"], docs),
            "log": [f"find_documents: {len(docs)} excerpts"]}


def write(state):
    n = state["attempt"] + 1
    print(f"[write] asking {iv.MODEL} (attempt {n}); this can take a few minutes...")
    report = chat(state["messages"])
    return {"report": report, "attempt": n, "log": [f"write: attempt {n}"]}


def check(state):
    problems = find_problems(state["report"], state["facts"], state["docs"])
    print(f"[check] " + ("clean" if not problems else f"{len(problems)} problem(s):"))
    for p in problems:
        print("    - " + p)
        return {"problems": problems,
            "attempts": [{"attempt": state["attempt"], "at": au.now(),
                          "report": state["report"], "problems": problems}],
            "log": [f"check: {len(problems)} problem(s)" if problems else "check: clean"]}
    
def decide(state) -> Literal["finish", "revise", "give_up"]:
    """The conditional edge: where to go after the check."""
    if not state["problems"]:
        return "finish"
    if state["attempt"] > MAX_RETRIES:
        return "give_up"
    return "revise"


def revise(state):
    feedback = ("Rewrite the whole report with the same five headings. Fix ONLY these "
                "problems and keep everything else:\n- " + "\n- ".join(state["problems"]))
    messages = state["messages"] + [{"role": "assistant", "content": state["report"]},
                                    {"role": "user", "content": feedback}]
    return {"messages": messages, "log": ["revise: sent the problems back to the model"]}


def save(state):
    au.write_audit(state, iv.ROOT, iv.MODEL)
    problems = state["problems"]
    status = ("Final report passed all checks." if not problems
              else "Final report still has problems:\n- " + "\n- ".join(problems))
    out_dir = iv.ROOT / "reports"
    out_dir.mkdir(exist_ok=True)
    out = out_dir / f"investigation_{state['target']}_graph.md"
    out.write_text(
        f"{state['report']}\n\n---\nChecks after {state['attempt']} attempt(s): {status}\n\n"
        "Run trace:\n" + "\n".join(f"- {line}" for line in state["log"]) +
        f"\n\nFacts used:\n```json\n{json.dumps(state['facts'], indent=2)}\n```\n",
        encoding="utf-8")
    print(f"[save] saved to {out}")
    return {"log": [f"save: {out.name}"]}


# ------------------------------------------------------------ the graph
def build_graph():
    g = StateGraph(State)
    for name, fn in [("gather_evidence", gather_evidence), ("calculate", calculate),
                     ("find_documents", find_documents), ("write", write),
                     ("check", check), ("revise", revise), ("save", save)]:
        g.add_node(name, fn)
    g.add_edge(START, "gather_evidence")
    g.add_edge("gather_evidence", "calculate")
    g.add_edge("calculate", "find_documents")
    g.add_edge("find_documents", "write")
    g.add_edge("write", "check")
    g.add_conditional_edges("check", decide,
                            {"finish": "save", "give_up": "save", "revise": "revise"})
    g.add_edge("revise", "write")
    g.add_edge("save", END)
    return g.compile()


def main():
    app = build_graph()
    if "--diagram" in sys.argv:
        print(app.get_graph().draw_mermaid())
        return
    target = next((a for a in sys.argv[1:] if not a.startswith("--")), None)
    try:
        final = app.invoke({"target": target})
    except error.URLError:
        sys.exit("Could not reach the backend (127.0.0.1:8000) or Ollama (localhost:11434). "
                 "Check that uvicorn and the Ollama app are both running.")
    print("\n=== REPORT ===")
    print(final["report"])
    print("\n=== RUN TRACE ===")
    for line in final["log"]:
        print(" -", line)


if __name__ == "__main__":
    main()
