from typing import List, Dict
from .models import ConsolidatedRecord


class Reporter:
    """Generate summary metrics, trends and report views."""

    def summary_metrics(self, records: List[ConsolidatedRecord]) -> Dict:
        """Generate simple summary metrics from consolidated records.

        Returns a dict with keys:
        - total_lots: int
        - total_defective_inspections: int
        - defects_by_type: Dict[str, int]
        - line_issues: Dict[int, int]  # defective counts per line
        - shipped_batches: int

        This is a minimal implementation intended to satisfy unit tests.
        """
        total_lots = len(records)
        total_defective_inspections = 0
        defects_by_type: Dict[str, int] = {}
        line_issues: Dict[int, int] = {}
        shipped_batches = 0

        for r in records:
            # shipped
            shipping = getattr(r, "shipping", None)
            if shipping and getattr(shipping, "is_shipped", False):
                shipped_batches += 1

            # inspections
            inspections = getattr(r, "inspections", []) or []
            for ins in inspections:
                if getattr(ins, "is_defective", False):
                    total_defective_inspections += 1

                    defect_type = getattr(ins, "defect_type", None)
                    if defect_type:
                        defects_by_type[defect_type] = defects_by_type.get(defect_type, 0) + 1

                    line_no = getattr(r, "line_number", None)
                    if line_no is not None:
                        line_issues[line_no] = line_issues.get(line_no, 0) + 1

        return {
            "total_lots": total_lots,
            "total_defective_inspections": total_defective_inspections,
            "defects_by_type": defects_by_type,
            "line_issues": line_issues,
            "shipped_batches": shipped_batches,
        }

    def trends(self, records: List[ConsolidatedRecord]) -> Dict:
        """Identify trending defect types or lines (stub)."""
        raise NotImplementedError

    def anomalies(self, records: List[ConsolidatedRecord]) -> List[Dict]:
        """Highlight anomalies for quick review (stub)."""
        raise NotImplementedError
