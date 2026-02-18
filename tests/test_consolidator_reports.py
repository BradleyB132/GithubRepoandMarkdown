import pytest
from datetime import date

from src.consolidator.reports import Reporter
from src.consolidator.models import ConsolidatedRecord


def test_summary_metrics_returns_expected_summary():
    """Provide a sample consolidated record and assert a minimal summary is returned."""
    sample = ConsolidatedRecord(
        lot_number="LOT-001",
        production_date=date.today(),
        line_number=1,
        shift_leader="Alice",
        inspections=[],
        shipping=None,
    )

    reporter = Reporter()
    result = reporter.summary_metrics([sample])

    assert isinstance(result, dict)
    assert result["total_lots"] == 1
    assert result["total_defective_inspections"] == 0
    assert result["defects_by_type"] == {}
    assert result["line_issues"] == {}
    assert result["shipped_batches"] == 0


def test_trends_not_implemented():
    reporter = Reporter()
    with pytest.raises(NotImplementedError):
        reporter.trends([])


def test_anomalies_not_implemented():
    reporter = Reporter()
    with pytest.raises(NotImplementedError):
        reporter.anomalies([])
