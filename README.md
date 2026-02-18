# Lot Consolidation & Reporting

Short description
-----------------
This project ingests production, quality inspection, and shipping spreadsheets,
consolidates them into aligned records keyed by `Lot_ID`, detects data
inconsistencies, and produces summary metrics and trends suitable for
stakeholder reporting (weekly meeting slides, dashboards, or quick checks).

Design and schema
------------------
Design artifacts live in the `docs/` directory and the PostgreSQL schema and
seed data are in the `db/` directory. The code is intentionally modular:

- `src/consolidator.py` — core consolidation and alignment logic (AC1–AC4)
- `src/report.py` — summary metric and trend computations (AC5–AC8)
- `src/db.py` — lightweight DB helpers for Render/Postgres persistence
- `src/app.py` — minimal Streamlit UI for interactive consolidation and review
- `tests/` — pytest suite mapping tests to acceptance criteria (ACs)

Prerequisites
-------------
- Python 3.12+
- Poetry (optional) or pip

Using Poetry (recommended)
--------------------------
1. Install Poetry: https://python-poetry.org/docs/
2. Create environment and install dependencies:

   poetry install

3. Enter the virtual environment shell:

   poetry shell

Run the Streamlit UI
--------------------
From the project root run:

   streamlit run src/app.py

This opens an interactive browser UI that reads authoritative source data
directly from the project's PostgreSQL database (Render). The app does NOT
accept CSV uploads; instead it loads `production_logs`, `quality_inspections`,
and `shipping_manifests` from the DB and presents consolidated records and
flags as tables. Use the "Load data from database" checkbox in the UI to
control whether the app attempts to connect to the DB in your session.

Running tests
-------------
Run the test suite with pytest:

   poetry run pytest -q

or if using pip/venv:

   python -m venv .venv
   source .venv/bin/activate   # or .venv\Scripts\activate on Windows
   pip install -r requirements.txt   # (or pip install pytest pandas streamlit sqlalchemy psycopg2-binary)
   pytest -q

Quick usage examples (Python REPL)
---------------------------------
Example: consolidate in memory and compute metrics

```python
from src.consolidator import consolidate
from src.report import summary_metrics

prod_rows = [{"Lot_ID": "LOT-1", "Line_No": 3, "Production_Date": "2024-05-01"}]
qual_rows = [{"Lot_ID": "lot_1", "Defect_Type": "Scratch", "is_defective": True}]
ship_rows = [{"Lot_ID": "LOT-1", "Ship_Date": "2024-05-03", "is_shipped": True}]

consolidated, flags = consolidate(prod_rows, qual_rows, ship_rows)
metrics = summary_metrics(consolidated)
print(metrics)
```

Database usage (Render PostgreSQL)
---------------------------------
The app reads source tables from Render/Postgres and also provides helpers
to persist consolidated report rows. Configure the DB connection using one
of these methods (priority order):

- Edit `src/db.py` and set `RENDER_DATABASE_URL_HARDCODED` for quick local
  testing (NOT recommended for production; do not commit credentials).
- Set the environment variable `RENDER_DATABASE_URL`.
- Set the environment variable `DATABASE_URL`.

Install DB packages and initialize schema (once):

   pip install sqlalchemy psycopg2-binary
   python -c "from src.db import get_engine, init_db; init_db(get_engine())"

Persist consolidated results programmatically:

   from src.db import get_engine, persist_consolidated
   from src.consolidator import consolidate
   engine = get_engine()
   consolidated, flags = consolidate(prod_rows, qual_rows, ship_rows)
   persist_consolidated(consolidated, engine)

Files and environment values you may need to change before deploying
-------------------------------------------------------------------
- `src/db.py`: set `RENDER_DATABASE_URL_HARDCODED` for quick local testing OR
  set `RENDER_DATABASE_URL` / `DATABASE_URL` in your Render service environment
  settings. Example format: `postgresql://user:pass@host:5432/dbname`.
- `pyproject.toml`: update `authors`, `description`, and package metadata.
- `db/seed.sql` and `db/schema.sql`: change sample data or schema as required.

Test coverage vs Acceptance Criteria (ACs)
----------------------------------------
Each AC is covered by at least one unit test in `tests/test_consolidation.py`:

- AC1/AC2: `test_consolidate_basic` — consolidation and alignment by `Lot_ID` and dates
- AC3/AC4: `test_incomplete_records` — missing/inconsistent data flagged or excluded
- AC5/AC6/AC7/AC8: `test_summary_and_trends` — summary metrics, trends, and shipped batches
- AC9/AC10: `test_flag_discrepancies` — discrepancy detection and flags
- AC11/AC12: `test_efficiency_and_reduction` — demonstrates reduced manual rows and in-memory reporting

Development notes and security
------------------------------
- The code uses simple, well-documented functions to make it easy for junior
  engineers to follow. See docstrings in `src/*.py` for complexity and behavior.
- Do not commit real DB credentials. Use Render's environment variable settings
  or a secrets store for production.

If you want further help I can:
- Add a `requirements.txt` generated from the Poetry lock file for pip users.
- Wire up a small CI pipeline that runs the tests on push.
- Add richer Streamlit visualizations (charts, filters, downloadable CSVs).

