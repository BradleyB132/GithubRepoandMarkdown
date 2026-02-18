"""
Database helpers for connecting to a PostgreSQL instance and persisting consolidated data.

This module uses SQLAlchemy for portability and simplicity. It provides an engine
factory and a `persist_consolidated` helper to write consolidated records into
simple reporting tables. For this exercise we keep persistence minimal and safe.

Note: The actual database schema is provided in `db/schema.sql`. This helper
assumes a Render (or other) PostgreSQL URL is supplied via `RENDER_DATABASE_URL`
or `DATABASE_URL` environment variable.

Complexity:
- Time: Persist operations are O(N) where N is number of records; each insert issues
  individual INSERTs (could be bulk-optimized later).
- Space: Uses minimal in-memory buffers; streaming inserts preferred for very large datasets.
"""
from typing import List, Dict, Any, Optional, Tuple
import os

# Note: Imports from SQLAlchemy are deferred to function scope so that importing
# this module does not immediately fail on systems where SQLAlchemy is not
# installed. This makes the package more runnable for parts of the app that
# don't require DB access (e.g., tests of pure consolidation logic).

# Optional hard-coded Render DB URL for quick local development/testing.
# Fill this string with your Render PostgreSQL connection URL if you want
# to bypass reading from environment variables. Example:
#   "postgresql://username:password@your-render-host:5432/dbname"
#
# WARNING: Do NOT commit real credentials to source control. Prefer using
# environment variables (`RENDER_DATABASE_URL` or `DATABASE_URL`) in CI/CD
# and production systems. This variable is provided only for convenience.
RENDER_DATABASE_URL_HARDCODED: str = "postgresql://admin:wpyaKUJEAyK6SV1fDeIRXqQD1kI6Lciz@dpg-d66db2buibrs73e4uu60-a.ohio-postgres.render.com/steelworks_l12w"


def get_engine() -> Any:
    """Create a SQLAlchemy engine using environment variables.

    Looks for `RENDER_DATABASE_URL` first then `DATABASE_URL`.

    Returns:
        SQLAlchemy Engine instance.
    """
    # Prefer an explicit hard-coded override when provided (useful for
    # local development). If it's empty, fall back to environment variables.
    url = RENDER_DATABASE_URL_HARDCODED or os.environ.get("RENDER_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("Database URL not set in environment (RENDER_DATABASE_URL or DATABASE_URL)")
    # Import create_engine locally so importing this module does not fail
    # when SQLAlchemy is not installed. This defers the hard dependency until
    # the DB is actually used at runtime.
    from sqlalchemy import create_engine

    # Use future engine for SQLAlchemy 2.0 style
    engine = create_engine(url, future=True)
    return engine


def init_db(engine: Any) -> None:
    """Initialize DB schema from `db/schema.sql` file.

    This will execute SQL statements found in the project's `db/schema.sql`.

    Args:
        engine: SQLAlchemy engine to use for executing schema statements.

    Resources are closed properly by using engine.begin() context manager.
    """
    here = os.path.dirname(__file__)
    schema_path = os.path.join(here, "..", "db", "schema.sql")
    if not os.path.exists(schema_path):
        raise RuntimeError(f"Schema file not found: {schema_path}")
    with open(schema_path, "r", encoding="utf8") as f:
        sql = f.read()
    # Use a transaction to execute the schema script atomically
    # Import `text` locally to avoid top-level SQLAlchemy dependency during import
    from sqlalchemy import text

    with engine.begin() as conn:
        conn.execute(text(sql))


def persist_consolidated(consolidated: List[Dict[str, Any]], engine: Optional[Any] = None) -> None:
    """Persist consolidated records into a simple reporting table.

    This function is intentionally lightweight and demonstrates how to write
    consolidated results to the DB. It writes into a `report_consolidated` table
    (created if missing). For production usage, schema and migrations should be used.

    Args:
        consolidated: list of merged records produced by `consolidate`.
        engine: optional SQLAlchemy engine; if not provided, `get_engine()` is used.

    Complexity: O(N) inserts for N records. Consider bulk operations for large N.
    """
    from sqlalchemy import Table, Column, Integer, String, MetaData, Date, Boolean, JSON

    if engine is None:
        engine = get_engine()

    meta = MetaData()
    # Define a small report table; idempotent create
    report_table = Table(
        "report_consolidated",
        meta,
        Column("id", Integer, primary_key=True),
        Column("lot_id", String(100), nullable=False, unique=True),
        Column("line_no", Integer),
        Column("production_date", Date),
        Column("shift_leader", String(200)),
        Column("payload", JSON),
    )
    # Create table if not exists
    meta.create_all(engine)

    # Insert or update each record; ensure connections are closed via begin()
    with engine.begin() as conn:
        for rec in consolidated:
            # Upsert-like behavior: Try update then insert if no rows affected
            payload = {
                "Defect_Count": rec.get("Defect_Count"),
                "Defect_Types": rec.get("Defect_Types"),
                "Severities": rec.get("Severities"),
                "Inspections": rec.get("Inspections"),
                "Shipping": rec.get("Shipping"),
            }
            lot = rec.get("Lot_ID")
            stmt_update = text(
                "UPDATE report_consolidated SET line_no = :line_no, production_date = :production_date, shift_leader = :shift_leader, payload = :payload WHERE lot_id = :lot"
            )
            result = conn.execute(
                stmt_update,
                {
                    "line_no": rec.get("Line_No"),
                    "production_date": rec.get("Production_Date"),
                    "shift_leader": rec.get("Shift_Leader"),
                    "payload": payload,
                    "lot": lot,
                },
            )
            if result.rowcount == 0:
                stmt_insert = text(
                    "INSERT INTO report_consolidated (lot_id, line_no, production_date, shift_leader, payload) VALUES (:lot, :line_no, :production_date, :shift_leader, :payload)"
                )
                conn.execute(
                    stmt_insert,
                    {
                        "lot": lot,
                        "line_no": rec.get("Line_No"),
                        "production_date": rec.get("Production_Date"),
                        "shift_leader": rec.get("Shift_Leader"),
                        "payload": payload,
                    },
                )


def fetch_source_rows(engine: Optional[Any] = None) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Fetch raw source rows from the database and return them in the same
    shape expected by `consolidate`.

    This helper reads `production_logs`, `quality_inspections`, and
    `shipping_manifests` tables and maps column names to the keys used by
    the in-memory consolidation logic. It is intended for the Streamlit app
    to load authoritative data from Render/Postgres rather than user uploads.

    Returns:
        Tuple of (production_rows, quality_rows, shipping_rows). Each is a
        list of dictionaries. Dates are returned as ISO strings for
        compatibility with the consolidator's parsing logic.

    Complexity: Performs three SELECT queries; network/DB cost is O(N) in
    the number of rows returned. Resources are closed via engine.begin().
    """
    from sqlalchemy import text

    if engine is None:
        engine = get_engine()

    production_rows: List[Dict[str, Any]] = []
    quality_rows: List[Dict[str, Any]] = []
    shipping_rows: List[Dict[str, Any]] = []

    # Use a single connection for all reads; engine.begin() ensures the
    # connection is released back to the pool and closed properly.
    with engine.begin() as conn:
        # Read production logs and normalize column names
        prod_q = text("SELECT lot_number as Lot_ID, line_number as Line_No, production_date as Production_Date, shift_leader as Shift_Leader FROM production_logs")
        res = conn.execute(prod_q)
        for row in res.mappings():
            # Convert date objects to ISO strings to be parsable by consolidator
            prod = dict(row)
            pd = prod.get("Production_Date")
            if pd is not None:
                try:
                    prod["Production_Date"] = pd.isoformat()
                except Exception:
                    prod["Production_Date"] = str(pd)
            production_rows.append(prod)

        # Read quality inspections
        qual_q = text("SELECT qi.quality_inspection_id as Inspection_ID, pl.lot_number as Lot_ID, qi.defect_type as Defect_Type, qi.defect_severity as Defect_Severity, qi.is_defective as is_defective, qi.inspection_count as inspection_count FROM quality_inspections qi JOIN production_logs pl ON qi.production_log_id = pl.production_log_id")
        res = conn.execute(qual_q)
        for row in res.mappings():
            quality_rows.append(dict(row))

        # Read shipping manifests
        ship_q = text("SELECT pl.lot_number as Lot_ID, sm.ship_date as Ship_Date, sm.destination as Destination, sm.is_shipped as is_shipped, sm.is_cancelled as is_cancelled FROM shipping_manifests sm JOIN production_logs pl ON sm.production_log_id = pl.production_log_id")
        res = conn.execute(ship_q)
        for row in res.mappings():
            ship = dict(row)
            sd = ship.get("Ship_Date")
            if sd is not None:
                try:
                    ship["Ship_Date"] = sd.isoformat()
                except Exception:
                    ship["Ship_Date"] = str(sd)
            shipping_rows.append(ship)

    return production_rows, quality_rows, shipping_rows
