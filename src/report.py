"""
Reporting utilities for generating summary metrics and trends from consolidated data.

This module provides functions to compute defect counts per line, trending defect types,
and quick checks such as whether high-severity defects have shipped.

Complexity:
- Time: O(N + M) where N is number of consolidated records and M is total number
  of inspections aggregated. Most operations are linear scans and grouping.
- Space: O(K) where K is number of unique grouping keys (e.g., lines, defect types).
"""
from typing import List, Dict, Any, Tuple
from collections import defaultdict, Counter
import datetime


def summary_metrics(consolidated: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute summary metrics such as defect counts per production line and shipped batches.

    Covers AC5, AC7 by returning structures suitable for filterable and sortable UIs.

    Args:
        consolidated: output from `consolidate` containing merged records.

    Returns:
        Dictionary containing aggregated metrics, trending defect counts, and shipped summary.
    """
    # Group defects by line and defect type (AC5)
    defects_by_line = defaultdict(Counter)
    shipped_lots = []
    total_defects = 0

    for rec in consolidated:
        line = rec.get("Line_No") or "Unknown"
        # Count defects aggregated in the consolidated record
        defect_count = rec.get("Defect_Count", 0) or 0
        total_defects += defect_count
        for d in rec.get("Defect_Types", []):
            defects_by_line[line][d] += 1

        # shipped info
        ship = rec.get("Shipping")
        if ship and (ship.get("is_shipped") or ship.get("Is_Shipped") or ship.get("isShipped")):
            shipped_lots.append({"Lot_ID": rec.get("Lot_ID"), "Ship_Date": ship.get("Ship_Date") or ship.get("ship_date")})

    # Build top-lines report (AC6)
    top_lines = []
    for line, counter in defects_by_line.items():
        total_line_defects = sum(counter.values())
        top_lines.append({"line": line, "total_defects": total_line_defects, "by_type": dict(counter)})

    # Trends: simple top N defect types overall
    overall_defect_counter = Counter()
    for line_counter in defects_by_line.values():
        overall_defect_counter.update(line_counter)

    trending = overall_defect_counter.most_common(10)

    return {
        "total_defects": total_defects,
        "top_lines": sorted(top_lines, key=lambda x: x["total_defects"], reverse=True),
        "trending_defects": trending,
        "shipped_lots": shipped_lots,
    }


def high_severity_shipped(consolidated: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Return list of lots with High or Critical defects that have shipped (AC6, AC8).

    Args:
        consolidated: merged records.

    Returns:
        List of records for lots where high severity defect exists and shipping shows shipped.
    """
    results = []
    for rec in consolidated:
        severities = rec.get("Severities") or []
        if any(s.lower() in ("high", "critical") for s in severities):
            ship = rec.get("Shipping")
            if ship and (ship.get("is_shipped") or ship.get("Is_Shipped") or ship.get("isShipped")):
                results.append({"Lot_ID": rec.get("Lot_ID"), "Severities": severities, "Shipping": ship})
    return results
