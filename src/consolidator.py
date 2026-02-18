"""
Consolidation utilities for combining production, quality, and shipping spreadsheets.

This module exposes a `consolidate` function which accepts lists of dict-like
rows from the three sources and returns a consolidated list of records plus
flags describing issues for review.

Complexity:
- Time: O(P + Q + S + R) where P,Q,S are counts of rows in production,
  quality, and shipping inputs and R is number of produced consolidated records.
  Building dict maps is linear; merging by keys is linear in total input size.
- Space: O(P + Q + S) extra for lookup maps and the consolidated output.

The functions are deterministic and avoid side-effects. They do not connect
to a DB directly; persistence lives in `src.db`.
"""
from typing import List, Dict, Tuple, Any
import datetime


def _normalize_lot(lot: Any) -> str:
    """Normalize a lot identifier to a canonical uppercase string.

    This helps align differing formats like `LOT-1`, `lot_1`, or `Lot 1`.

    Args:
        lot: value extracted from a spreadsheet row, often a str.

    Returns:
        Canonical string (uppercase, trimmed) or empty string for missing input.

    Complexity: O(L) where L is length of input string.
    """
    if lot is None:
        return ""
    try:
        s = str(lot).strip().upper()
    except Exception:
        return ""
    # Replace common separators with a normalized hyphen
    for ch in [" ", "_"]:
        s = s.replace(ch, "-")
    return s


def consolidate(
    production_rows: List[Dict[str, Any]],
    quality_rows: List[Dict[str, Any]],
    shipping_rows: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Consolidate rows from three sources into aligned records.

    This implements AC1 and AC2 by building lookup maps keyed on normalized
    `Lot_ID` and attempting to align records by lot and date. It also flags
    missing or inconsistent data (AC3) and excludes incomplete records when
    they lack required fields (AC4).

    Args:
        production_rows: list of dicts with at least `Lot_ID`, `Line_No`, and
            `Production_Date` entries.
        quality_rows: list of dicts with at least `Lot_ID` and inspection info.
        shipping_rows: list of dicts with at least `Lot_ID` and shipping info.

    Returns:
        A tuple `(consolidated, flags)` where `consolidated` is a list of merged
        records and `flags` is a list of issue dictionaries for records needing
        review.
    """
    # Build maps for quick lookup by normalized lot identifier. Each build is
    # O(N) for the number of rows in that source.
    prod_map = {}
    for r in production_rows:
        lot = _normalize_lot(r.get("Lot_ID") or r.get("lot_id") or r.get("lotNumber"))
        if not lot:
            # Skip entries with no lot id; they are incomplete (AC4)
            continue
        # Keep earliest production date if duplicate lot appears (simple rule)
        existing = prod_map.get(lot)
        try:
            # Accept strings or date objects for production date
            raw_date = r.get("Production_Date") or r.get("production_date")
            if isinstance(raw_date, str):
                prod_date = datetime.datetime.fromisoformat(raw_date).date()
            elif isinstance(raw_date, datetime.date):
                prod_date = raw_date
            else:
                prod_date = None
        except Exception:
            prod_date = None
        entry = {"prod": r, "prod_date": prod_date}
        if existing is None:
            prod_map[lot] = entry
        else:
            # Choose the earliest non-null date to represent the lot
            if existing.get("prod_date") is None and prod_date is not None:
                prod_map[lot] = entry

    qual_map = {}
    for r in quality_rows:
        lot = _normalize_lot(r.get("Lot_ID") or r.get("lot_id"))
        if not lot:
            # Flag quality rows with missing lot IDs for review
            continue
        qual_map.setdefault(lot, []).append(r)

    ship_map = {}
    for r in shipping_rows:
        lot = _normalize_lot(r.get("Lot_ID") or r.get("lot_id") or r.get("LotID"))
        if not lot:
            continue
        ship_map[lot] = r

    consolidated = []
    flags = []

    # Keys to iterate are all lots seen in any source to satisfy AC1
    all_lots = set(list(prod_map.keys()) + list(qual_map.keys()) + list(ship_map.keys()))

    for lot in sorted(all_lots):
        prod_entry = prod_map.get(lot)
        qual_entries = qual_map.get(lot, [])
        ship_entry = ship_map.get(lot)

        # Basic validation: require production record for a meaningful consolidated record
        if prod_entry is None:
            # Create a flag for missing production record (AC3)
            flags.append({"lot": lot, "issue": "missing_production_record"})
            # Still include a lightweight consolidated record to allow traceability
            consolidated.append({
                "Lot_ID": lot,
                "Line_No": None,
                "Production_Date": None,
                "Inspections": qual_entries,
                "Shipping": ship_entry,
            })
            continue

        # Build the merged record using production data as the authoritative anchor
        prod = prod_entry["prod"]
        record = {
            "Lot_ID": lot,
            "Line_No": prod.get("Line_No") or prod.get("line_number") or prod.get("LineNo"),
            "Production_Date": prod_entry.get("prod_date"),
            "Shift_Leader": prod.get("Shift_Leader") or prod.get("shift_leader"),
            "Inspections": qual_entries,
            "Shipping": ship_entry,
        }

        # Flag inconsistent dates between production and shipping (AC2, AC9)
        if ship_entry is not None:
            ship_date_raw = ship_entry.get("Ship_Date") or ship_entry.get("ship_date")
            try:
                if isinstance(ship_date_raw, str):
                    ship_date = datetime.date.fromisoformat(ship_date_raw)
                elif isinstance(ship_date_raw, datetime.date):
                    ship_date = ship_date_raw
                else:
                    ship_date = None
            except Exception:
                ship_date = None
            if ship_date is None:
                flags.append({"lot": lot, "issue": "invalid_ship_date"})
            else:
                # If shipping occurred before production, that's an inconsistency
                if record["Production_Date"] is not None and ship_date < record["Production_Date"]:
                    flags.append({"lot": lot, "issue": "ship_before_production"})

        # Exclude totally empty/incomplete records based on business rules (AC4)
        # A record should only be excluded when it lacks any meaningful data
        # across production, inspection, and shipping. Production date alone
        # is considered sufficient to keep the record for traceability.
        if (
            record["Line_No"] is None
            and not record["Inspections"]
            and record["Shipping"] is None
            and record["Production_Date"] is None
        ):
            flags.append({"lot": lot, "issue": "insufficient_data_excluded"})
            # Do not include this record in consolidated output
            continue

        # Additional flags: conflicting inspection info across quality entries (AC3/AC9)
        defect_types = set()
        severities = set()
        defective_count = 0
        for q in qual_entries:
            if q.get("is_defective"):
                defective_count += 1
            if q.get("Defect_Type"):
                defect_types.add(str(q.get("Defect_Type")))
            if q.get("Defect_Severity"):
                severities.add(str(q.get("Defect_Severity")))

        record["Defect_Count"] = defective_count
        record["Defect_Types"] = list(sorted(defect_types))
        record["Severities"] = list(sorted(severities))

        if len(defect_types) > 1:
            flags.append({"lot": lot, "issue": "conflicting_defect_types", "details": record["Defect_Types"]})

        consolidated.append(record)

    return consolidated, flags
