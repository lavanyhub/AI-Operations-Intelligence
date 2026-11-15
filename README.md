# NovaFlow AI Operations Intelligence

I built this to see if an AI agent could answer a manager's question properly: "Why did customer cancellations go up this month?"

NovaFlow is a made-up B2B software company with 50,000 customers. I generated all of its data myself and planted one hidden cause in it, a problem with the payment gateway that made payments fail and pushed people to cancel. The agent's job is to find that cause using the data, the company's documents, and its own checks.

Everything runs on my own laptop. The language model is a small local one (llama3.1:8b through Ollama), so there are no API costs. That choice shaped a lot of the design, which I explain below.

<!-- Add a dashboard screenshot: save it as docs/dashboard.png, then delete this line and use:
![Dashboard](docs/dashboard.png)
-->

## How it works

The main rule is that the numbers never come from the AI. A small local model is not reliable with figures, so code does the counting and the model only writes the explanation.

- The backend reads six connected tables from PostgreSQL (customers, subscriptions, payments, support tickets, product events, incidents). It works out the payment failure rate, cancellations, failure reasons, ticket counts and incidents. The confidence label (Low, Medium or High) is also set by code.
- I generated 23 documents for the company: incident reports, release notes, policies and monthly reports. They are split into 56 chunks and embedded locally with fastembed, so the agent can search them for causes and dates.
- A LangGraph workflow runs the investigation: gather evidence, calculate, find documents, write the report, check it, and revise if the check fails.
- The report has five parts: Finding, Evidence, Analysis, Confidence and Recommendation.
- `validate_report.py` holds the rule-based checks on the report's wording, for example catching a cause that is stated too strongly. If a check fails, the agent gets another attempt.
- The React dashboard lets you pick a month, start an investigation and watch each step as it happens.
- There is also an MCP server with 8 tools, so something like Claude Desktop can query the same data. Setup notes are in `docs/mcp-setup.md`.

## Tech used

Python, FastAPI, PostgreSQL, LangGraph, Ollama, fastembed, React 18, Vite, MCP, pytest.

## What is in each folder

- `backend/`: the FastAPI API (payment failures, cancellations, failure reasons, tickets, incidents, document search)
- `scripts/`: data and document generators, indexing, the agent (`investigate_graph.py`), the report checks (`validate_report.py`) and the audit trail
- `data/documents/`: the generated incident reports, release notes, policies and monthly reports
- `frontend/`: the React dashboard
- `mcp_server/`: the MCP server and a small test client
- `tests/`: tests for the report checks
- `reports/`: saved investigation reports
- `docs/`: setup notes

The six raw CSV files are about 170 MB, which is too big for GitHub, so they are not in the repo. You generate them with a script (see below).

## Setting it up

You need Python 3.10 or newer, Node.js 20 or newer, PostgreSQL and [Ollama](https://ollama.com).

1. Create the Python environment:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2. Copy `.env.example` to `.env` and fill in your own values (at least `DB_PASSWORD`). Then create a PostgreSQL database called `novaflow`.

3. Generate the data and documents:

```powershell
python scripts/generate_data.py
python scripts/generate_documents.py
```

This writes six CSVs into `data/raw/`. Load each one into the matching table in the `novaflow` database. I used pgAdmin's import tool.

4. Build the document index:

```powershell
python scripts/index_documents.py
```

5. Download the model:

```powershell
ollama pull llama3.1:8b
```

## Running it

I use three terminals.

Backend (runs at http://127.0.0.1:8000, with API docs at /docs):

```powershell
uvicorn backend.main:app --reload
```

Dashboard (Vite prints the address, usually http://localhost:5173):

```powershell
cd frontend
npm install
npm run dev
```

Agent on its own, without the dashboard (optional):

```powershell
python scripts/investigate_graph.py
```

Make sure Ollama is running in the background first.

To run the tests:

```powershell
pytest
```

## Known limitations

- It is slow. On my laptop one investigation takes several minutes, and the small model writes worse than the big hosted ones. That is why the code handles the numbers.
- The rule checks are not perfect. The "root cause overstated" check wrongly flags sentences like "identify the root cause" in the recommendation. The report can also say a check passed when that check never ran. I know about both and chose not to fix them yet.
- The data is synthetic. This shows the method works on data I built for the test. It says nothing about how it would do on real company data.
- The report is not guaranteed to be correct. The wording comes from the model and is only checked by rules, so read the evidence before acting on it. The dashboard says the same thing.

## What is next

GitHub Actions to run the tests on every push, Docker packaging, and some monitoring of the runs.