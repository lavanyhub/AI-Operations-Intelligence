import { useCallback, useEffect, useState } from "react";
import "./App.css";

const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

const FALLBACK_MONTHS = Array.from({ length: 10 }, (_, i) => `2026-${String(i + 1).padStart(2, "0")}`);

const STEP_LABELS = {
  gather_evidence: "Collect data from the API",
  calculate: "Calculate the numbers",
  find_documents: "Find related documents",
  write: "Write the report",
  check: "Check the report",
  revise: "Ask the model to fix the problems",
  save: "Save the report",
};

const SECTION_TITLES = {
  FINDING: "Finding",
  EVIDENCE: "Evidence",
  ANALYSIS: "Analysis",
  CONFIDENCE: "Confidence",
  RECOMMENDATION: "Recommendation",
};

function monthLabel(m) {
  const [y, mo] = m.split("-").map(Number);
  return new Date(y, mo - 1, 1).toLocaleString("en", { month: "long", year: "numeric" });
}

function asText(v) {
  return typeof v === "string" ? v : JSON.stringify(v);
}

function duration(seconds) {
  const s = Math.max(0, Math.round(seconds));
  const m = Math.floor(s / 60);
  return m ? `${m} min ${s % 60} s` : `${s} s`;
}

// Turns the agent's printed lines like "[check] 2 problems" into a trail of steps.
function stepsFromLines(lines) {
  const steps = [];
  for (const line of lines) {
    const m = line.match(/^\[([a-z_]+)\]\s*(.*)$/i);
    if (!m) continue;
    const key = m[1].toLowerCase();
    const last = steps[steps.length - 1];
    if (last && last.key === key) {
      if (m[2]) last.details.push(m[2]);
      continue;
    }
    steps.push({ key, label: STEP_LABELS[key] || key.replace(/_/g, " "), details: m[2] ? [m[2]] : [] });
  }
  return steps;
}

function parseReport(text) {
  if (!text) return null;
  const parts = text.split(/\*\*(FINDING|EVIDENCE|ANALYSIS|CONFIDENCE|RECOMMENDATION)\*\*:?/);
  if (parts.length < 3) return null;
  const sections = [];
  for (let i = 1; i < parts.length; i += 2) {
    sections.push({ name: parts[i], body: (parts[i + 1] || "").trim() });
  }
  return sections;
}

function Inline({ text }) {
  const parts = text.split(/\*\*(.+?)\*\*/g);
  return parts.map((p, i) => (i % 2 ? <strong key={i}>{p}</strong> : p));
}

function Rich({ text }) {
  const blocks = [];
  let list = null;
  for (const raw of (text || "").split("\n")) {
    const line = raw.trim();
    if (!line) {
      list = null;
      continue;
    }
    const m = line.match(/^[-*\u2022]\s+(.*)/);
    if (m) {
      if (!list) {
        list = [];
        blocks.push({ type: "ul", items: list });
      }
      list.push(m[1]);
    } else {
      list = null;
      blocks.push({ type: "p", text: line });
    }
  }
  return (
    <>
      {blocks.map((b, i) =>
        b.type === "ul" ? (
          <ul key={i}>
            {b.items.map((it, j) => (
              <li key={j}>
                <Inline text={it} />
              </li>
            ))}
          </ul>
        ) : (
          <p key={i}>
            <Inline text={b.text} />
          </p>
        )
      )}
    </>
  );
}

function Progress({ job, now }) {
  const steps = stepsFromLines(job.lines);
  const running = job.status === "running";
  const failed = job.status === "failed";
  const end = job.finished_at || now;
  return (
    <section className="progress" aria-live="polite">
      <h2>{running ? "Investigation running" : failed ? "Investigation failed" : "Investigation finished"}</h2>
      <p className="muted">
        {monthLabel(job.month)}, {duration(end - job.started_at)}
        {running ? " so far. A local model can take several minutes." : ""}
      </p>
      <ol className="trail">
        {steps.length === 0 && running && (
          <li className="step running">
            <span className="dot" aria-hidden="true" />
            <div>
              <p className="step-name">Starting the agent</p>
            </div>
          </li>
        )}
        {steps.map((s, i) => {
          const isLast = i === steps.length - 1;
          const state = isLast ? (running ? "running" : failed ? "failed" : "done") : "done";
          return (
            <li key={i} className={`step ${state}`}>
              <span className="dot" aria-hidden="true" />
              <div>
                <p className="step-name">{s.label}</p>
                {s.details.slice(0, 4).map((d, j) => (
                  <p className="step-detail" key={j}>
                    {d.length > 160 ? d.slice(0, 157) + "..." : d}
                  </p>
                ))}
              </div>
            </li>
          );
        })}
      </ol>
      {failed && job.error && <pre className="checks">{job.error}</pre>}
    </section>
  );
}

function Report({ job }) {
  const sections = parseReport(job.report);
  const state = job.passed === true ? "ok" : job.passed === false ? "warn" : "unknown";
  const verdict =
    state === "ok"
      ? "All automatic checks passed"
      : state === "warn"
      ? "Saved with problems the checks still found"
      : "Check result not available";
  return (
    <article className={`sheet ${state}`}>
      <div className="verdict">
        <strong>{verdict}</strong>
        {job.attempts ? ` after ${job.attempts} attempt${job.attempts > 1 ? "s" : ""}` : ""}
      </div>
      {state === "warn" && job.checks && <pre className="checks">{job.checks}</pre>}
      {sections ? (
        sections.map((s) => (
          <section key={s.name}>
            <h3>{SECTION_TITLES[s.name]}</h3>
            <Rich text={s.body} />
          </section>
        ))
      ) : (
        <Rich text={job.report} />
      )}
    </article>
  );
}

function Rail({ job, runs, activeId, onPick }) {
  const facts = job && job.facts;
  const conf = facts && facts.confidence;
  const key = facts && Array.isArray(facts.key_statements) ? facts.key_statements : [];
  const caveats = facts && Array.isArray(facts.caveats) ? facts.caveats : [];
  const passed = conf && Array.isArray(conf.checks_passed) ? conf.checks_passed : [];
  const failed = conf && Array.isArray(conf.checks_failed) ? conf.checks_failed : [];
  return (
    <aside className="rail">
      {key.length > 0 && (
        <section>
          <h3>Numbers calculated by code</h3>
          <ul className="facts">
            {key.map((k, i) => (
              <li key={i}>{asText(k)}</li>
            ))}
          </ul>
        </section>
      )}
      {conf && conf.label && (
        <section>
          <h3>Confidence set by code</h3>
          <p>
            <span className={`badge badge-${String(conf.label).toLowerCase()}`}>{conf.label}</span>
          </p>
          {passed.length > 0 && (
            <>
              <p className="muted">Checks passed</p>
              <ul className="facts">
                {passed.map((c, i) => (
                  <li key={i}>{asText(c)}</li>
                ))}
              </ul>
            </>
          )}
          {failed.length > 0 && (
            <>
              <p className="muted">Checks not met</p>
              <ul className="facts">
                {failed.map((c, i) => (
                  <li key={i}>{asText(c)}</li>
                ))}
              </ul>
            </>
          )}
        </section>
      )}
      {caveats.length > 0 && (
        <section>
          <h3>Caveats</h3>
          <ul className="facts">
            {caveats.map((c, i) => (
              <li key={i}>{asText(c)}</li>
            ))}
          </ul>
        </section>
      )}
      <section>
        <h3>Runs since the server started</h3>
        {runs.length === 0 ? (
          <p className="muted">None yet.</p>
        ) : (
          <ul className="runs">
            {runs.map((r) => (
              <li key={r.id}>
                <button
                  type="button"
                  className="run-item"
                  aria-current={r.id === activeId ? "true" : undefined}
                  onClick={() => onPick(r)}
                >
                  <span>{monthLabel(r.month)}</span>
                  <span className={`status status-${r.status}`}>{r.status}</span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>
    </aside>
  );
}

export default function App() {
  const [months, setMonths] = useState(FALLBACK_MONTHS);
  const [month, setMonth] = useState(FALLBACK_MONTHS[FALLBACK_MONTHS.length - 1]);
  const [jobId, setJobId] = useState(null);
  const [job, setJob] = useState(null);
  const [runs, setRuns] = useState([]);
  const [notice, setNotice] = useState(null);
  const [now, setNow] = useState(Date.now() / 1000);
  const [starting, setStarting] = useState(false);

  const unreachable = `Can't reach the API at ${API}. Start uvicorn, then reload this page.`;

  const loadRuns = useCallback(async () => {
    try {
      const r = await fetch(`${API}/investigations`);
      if (!r.ok) throw new Error("bad status");
      setRuns(await r.json());
    } catch {
      setNotice({ kind: "bad", text: unreachable });
    }
  }, [unreachable]);

  // month list from the API, with a fixed list as fallback
  useEffect(() => {
    fetch(`${API}/cancellations/monthly`)
      .then((r) => r.json())
      .then((d) => {
        const arr = Array.isArray(d) ? d : d && Array.isArray(d.value) ? d.value : [];
        const found = arr
          .map((x) => (x && x.month ? String(x.month).slice(0, 7) : ""))
          .filter((m) => /^\d{4}-\d{2}$/.test(m))
          .sort();
        if (found.length) {
          setMonths(found);
          setMonth(found[found.length - 1]);
        }
      })
      .catch(() => {});
    loadRuns();
  }, [loadRuns]);

  // poll the running investigation
  useEffect(() => {
    if (!jobId) return undefined;
    let stop = false;
    let timer;
    async function tick() {
      try {
        const r = await fetch(`${API}/investigations/${jobId}`);
        if (!r.ok) throw new Error("bad status");
        const j = await r.json();
        if (stop) return;
        setJob(j);
        if (j.status !== "running") {
          loadRuns();
          return;
        }
      } catch {
        if (!stop) setNotice({ kind: "bad", text: unreachable });
        return;
      }
      timer = setTimeout(tick, 2000);
    }
    tick();
    return () => {
      stop = true;
      clearTimeout(timer);
    };
  }, [jobId, loadRuns, unreachable]);

  // clock for the elapsed time while a run is going
  const running = job && job.status === "running";
  useEffect(() => {
    if (!running) return undefined;
    const t = setInterval(() => setNow(Date.now() / 1000), 1000);
    return () => clearInterval(t);
  }, [running]);

  async function start(e) {
    e.preventDefault();
    setNotice(null);
    setStarting(true);
    try {
      const r = await fetch(`${API}/investigations`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ month }),
      });
      const data = await r.json().catch(() => ({}));
      if (r.status === 409 && data.detail && data.detail.id) {
        setNotice({ kind: "info", text: "An investigation is already running. Showing its progress." });
        setJob(null);
        setJobId(data.detail.id);
      } else if (!r.ok) {
        setNotice({ kind: "bad", text: typeof data.detail === "string" ? data.detail : "The API refused the request." });
      } else {
        setJob(null);
        setJobId(data.id);
        loadRuns();
      }
    } catch {
      setNotice({ kind: "bad", text: unreachable });
    } finally {
      setStarting(false);
    }
  }

  function pick(run) {
    setNotice(null);
    setJob(null);
    setJobId(run.id);
    if (months.includes(run.month)) setMonth(run.month);
  }

  return (
    <div className="app">
      <header className="top">
        <h1>NovaFlow operations</h1>
        <p className="muted">Ask why a number moved. The agent checks the data and writes up what it found.</p>
      </header>

      <div className="grid">
        <main>
          <form className="ask" onSubmit={start}>
            <label className="question">
              Why did customer cancellations increase in{" "}
              <select value={month} onChange={(e) => setMonth(e.target.value)}>
                {months.map((m) => (
                  <option key={m} value={m}>
                    {monthLabel(m)}
                  </option>
                ))}
              </select>
              ?
            </label>
            <button className="run" type="submit" disabled={starting || running}>
              {running ? "Investigation running" : "Run investigation"}
            </button>
          </form>

          {notice && (
            <p role="alert" className={`notice ${notice.kind}`}>
              {notice.text}
            </p>
          )}

          {job ? (
            <>
              <Progress job={job} now={now} />
              {job.status === "done" && job.report && <Report job={job} />}
            </>
          ) : (
            !notice && (
              <section className="empty">
                <h2>No investigation open</h2>
                <p>
                  Pick a month and run the investigation. The agent collects the numbers, finds related incident
                  reports and release notes, writes a report and checks it. On a local model this takes a few minutes.
                </p>
              </section>
            )
          )}
        </main>

        <Rail job={job} runs={runs} activeId={jobId} onPick={pick} />
      </div>

      <footer className="foot">
        The numbers come from code. The wording is written by a local AI model and checked by rules, so read the
        evidence before you act on it.
      </footer>
    </div>
  );
}
