"""
toy_graph.py -- a tiny LangGraph example (no AI, no database).
It imitates our report loop: write -> check -> retry if needed.
"""
from typing import TypedDict

from langgraph.graph import END, START, StateGraph


class State(TypedDict):
    attempt: int      # how many times we have written
    report: str       # the latest "report"
    problems: list    # what the check found


def write(state):
    n = state["attempt"] + 1
    print(f"WRITE: attempt {n}")
    # pretend the first attempt forgets a number, the second includes it
    report = "Cancellations rose 39%." if n == 1 else "Cancellations rose 39%. There were 1,506 gateway_timeout failures."
    return {"attempt": n, "report": report}


def check(state):
    problems = [] if "1,506" in state["report"] else ["missing the number 1,506"]
    print("CHECK:", problems or "clean")
    return {"problems": problems}


def decide(state):
    if not state["problems"]:
        return "done"
    if state["attempt"] >= 3:
        return "give_up"
    return "retry"


graph = StateGraph(State)
graph.add_node("write", write)
graph.add_node("check", check)
graph.add_edge(START, "write")
graph.add_edge("write", "check")
graph.add_conditional_edges("check", decide,
                            {"done": END, "give_up": END, "retry": "write"})
app = graph.compile()

result = app.invoke({"attempt": 0, "report": "", "problems": []})
print("\nFINAL REPORT:", result["report"])
print("ATTEMPTS:", result["attempt"])
