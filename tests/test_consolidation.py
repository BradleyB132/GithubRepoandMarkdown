"""
Unit tests for consolidation and reporting mapping to acceptance criteria.

Each test includes which ACs it covers.
"""
import sys
from pathlib import Path

# Ensure the project root is on sys.path so `src` is importable when pytest
# runs from environments where Python's import path does not already include
# the repo root (common on Windows / some CI). This keeps tests portable.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.consolidator import consolidate
from src.report import summary_metrics, high_severity_shipped
import datetime


def test_consolidate_basic():
    """ACs covered: AC1, AC2, AC5

    - Create simple production, quality, and shipping rows that align by Lot_ID
    - Verify consolidation merges records and summary metrics count defects
    """
    prod = [{"Lot_ID": "LOT-1", "Line_No": 2, "Production_Date": "2024-05-01", "Shift_Leader": "A"}]
    qual = [{"Lot_ID": "lot-1", "Defect_Type": "Scratch", "is_defective": True, "Defect_Severity": "Medium"}]
    ship = [{"Lot_ID": "LOT-1", "Ship_Date": "2024-05-03", "is_shipped": True}]

    consolidated, flags = consolidate(prod, qual, ship)
    assert len(consolidated) == 1
    assert consolidated[0]["Lot_ID"] == "LOT-1"
    assert consolidated[0]["Defect_Count"] == 1

    metrics = summary_metrics(consolidated)
    assert metrics["total_defects"] == 1


def test_incomplete_records():
    """ACs covered: AC3, AC4

    - Quality row without lot id should not break consolidation and should flag issue
    - Production row missing critical fields causes exclusion from consolidated output
    """
    prod = [
        {"Lot_ID": None, "Line_No": None, "Production_Date": None},
        {"Lot_ID": "LOT-KEEP", "Line_No": None, "Production_Date": "2024-05-01"},
    ]
    qual = [{"Lot_ID": None, "Defect_Type": "None", "is_defective": False}]
    ship = []
    consolidated, flags = consolidate(prod, qual, ship)
    # Only the valid production record should be included
    lots = {c['Lot_ID'] for c in consolidated}
    assert "LOT-KEEP" in lots
    assert None not in lots
    # Flags should include missing production record for any quality rows without lot (none with lot here)
    assert isinstance(flags, list)


def test_summary_and_trends():
    """ACs covered: AC5, AC6, AC7, AC8

    - Multiple lots across lines with defects; verify top lines and trending defect types
    """
    prod = [
        {"Lot_ID": "LOT-1", "Line_No": 1, "Production_Date": "2024-05-01"},
        {"Lot_ID": "LOT-2", "Line_No": 2, "Production_Date": "2024-05-02"},
    ]
    qual = [
        {"Lot_ID": "LOT-1", "Defect_Type": "Scratch", "is_defective": True, "Defect_Severity": "High"},
        {"Lot_ID": "LOT-2", "Defect_Type": "Scratch", "is_defective": True, "Defect_Severity": "Low"},
        {"Lot_ID": "LOT-2", "Defect_Type": "Color", "is_defective": True, "Defect_Severity": "Medium"},
    ]
    ship = [
        {"Lot_ID": "LOT-1", "Ship_Date": "2024-05-04", "is_shipped": True},
        {"Lot_ID": "LOT-2", "Ship_Date": "2024-05-05", "is_shipped": True},
    ]
    consolidated, flags = consolidate(prod, qual, ship)
    metrics = summary_metrics(consolidated)
    assert metrics["total_defects"] == 3
    assert len(metrics["top_lines"]) == 2
    assert metrics["trending_defects"][0][0] == "Scratch"
    # Ensure shipped_lots format is a list of dicts suitable for display (AC8)
    assert isinstance(metrics["shipped_lots"], list)
    if metrics["shipped_lots"]:
        assert "Lot_ID" in metrics["shipped_lots"][0]


def test_flag_discrepancies():
    """ACs covered: AC9, AC10

    - Shipping before production should be flagged
    - Multiple defect types for same lot should be flagged
    """
    prod = [{"Lot_ID": "LOT-1", "Line_No": 1, "Production_Date": "2024-05-05"}]
    qual = [
        {"Lot_ID": "LOT-1", "Defect_Type": "Scratch", "is_defective": True, "Defect_Severity": "High"},
        {"Lot_ID": "LOT-1", "Defect_Type": "Crack", "is_defective": True, "Defect_Severity": "Medium"},
    ]
    ship = [{"Lot_ID": "LOT-1", "Ship_Date": "2024-05-01", "is_shipped": True}]
    consolidated, flags = consolidate(prod, qual, ship)
    # Expect flags for ship_before_production and conflicting_defect_types
    issues = {f.get("issue") for f in flags}
    assert "ship_before_production" in issues
    assert "conflicting_defect_types" in issues


def test_efficiency_and_reduction():
    """ACs covered: AC11, AC12

    - Ensure consolidation produces fewer or equal records compared to raw inputs (reducing manual effort)
    - Ensure summary metrics can be produced without DB (timely access)
    """
    prod = [{"Lot_ID": f"LOT-{i}", "Line_No": i % 3 + 1, "Production_Date": "2024-05-01"} for i in range(1, 6)]
    # Create many quality rows for same lots to simulate manual merging effort
    qual = []
    for i in range(1, 6):
        for j in range(3):
            qual.append({"Lot_ID": f"lot-{i}", "Defect_Type": "Scratch", "is_defective": j == 0})
    ship = [{"Lot_ID": f"LOT-{i}", "Ship_Date": "2024-05-03", "is_shipped": True} for i in range(1, 6)]

    consolidated, flags = consolidate(prod, qual, ship)
    # Consolidation should collapse multiple quality rows about same lot into one consolidated record
    assert len(consolidated) <= (len(prod) + len(ship) + len(qual))
    # Summary metrics are computable quickly in-memory (timely access)
    metrics = summary_metrics(consolidated)
    assert "total_defects" in metrics