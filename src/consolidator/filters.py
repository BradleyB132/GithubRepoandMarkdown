from typing import List
from .models import ConsolidatedRecord


class RecordFilter:
    """Filter out irrelevant or incomplete records."""

    def exclude_incomplete(self, records: List[ConsolidatedRecord]) -> List[ConsolidatedRecord]:
        """Exclude records missing essential fields (stub)."""
        raise NotImplementedError

    def filter_by_date_range(self, records: List[ConsolidatedRecord], start_date, end_date) -> List[ConsolidatedRecord]:
        """Return records within date range (stub)."""
        raise NotImplementedError
