from typing import List, Dict
from .models import ConsolidatedRecord


class Reporter:
    """Generate summary metrics, trends and report views."""

    def summary_metrics(self, records: List[ConsolidatedRecord]) -> Dict:
        """Generate counts like defect counts, line issues, shipped batches (stub)."""
        raise NotImplementedError

    def trends(self, records: List[ConsolidatedRecord]) -> Dict:
        """Identify trending defect types or lines (stub)."""
        raise NotImplementedError

    def anomalies(self, records: List[ConsolidatedRecord]) -> List[Dict]:
        """Highlight anomalies for quick review (stub)."""
        raise NotImplementedError
