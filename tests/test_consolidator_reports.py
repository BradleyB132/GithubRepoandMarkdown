import pytest
from datetime import date

from src.consolidator.reports import Reporter
from src.consolidator.models import ConsolidatedRecord
from src.consolidator.models import QualityInspection, ShippingManifest
from datetime import datetime


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


def test_summary_aggregates_multiple_defects_and_shipping():
    """Multiple defective inspections across records should aggregate correctly."""
    insp1 = QualityInspection(
        quality_inspection_id=None,
        production_log_id=None,
        defect_type="TypeA",
        defect_severity="High",
        is_defective=True,
        inspection_count=1,
        inspected_at=datetime.utcnow(),
    )

    insp2 = QualityInspection(
        quality_inspection_id=None,
        production_log_id=None,
        defect_type="TypeA",
        defect_severity="Low",
        is_defective=True,
        inspection_count=1,
        inspected_at=datetime.utcnow(),
    )

    insp3 = QualityInspection(
        quality_inspection_id=None,
        production_log_id=None,
        defect_type="TypeB",
        defect_severity="Medium",
        is_defective=True,
        inspection_count=1,
        inspected_at=datetime.utcnow(),
    )

    ship = ShippingManifest(
        shipping_manifest_id=None,
        production_log_id=None,
        ship_date=None,
        destination="Dest",
        is_shipped=True,
        is_cancelled=False,
    )

    r1 = ConsolidatedRecord(
        lot_number="L1",
        production_date=date.today(),
        line_number=1,
        shift_leader="A",
        inspections=[insp1],
        shipping=None,
    )

    r2 = ConsolidatedRecord(
        lot_number="L2",
        production_date=date.today(),
        line_number=2,
        shift_leader="B",
        inspections=[insp2, insp3],
        shipping=ship,
    )

    reporter = Reporter()
    result = reporter.summary_metrics([r1, r2])

    assert result["total_lots"] == 2
    assert result["total_defective_inspections"] == 3
    assert result["defects_by_type"]["TypeA"] == 2
    assert result["defects_by_type"]["TypeB"] == 1
    assert result["line_issues"][1] == 1
    assert result["line_issues"][2] == 2
    assert result["shipped_batches"] == 1


def test_summary_counts_defective_without_defect_type():
    """Defective inspections without a defect_type should count toward totals and line issues
    but not appear in defects_by_type mapping."""
    insp = QualityInspection(
        quality_inspection_id=None,
        production_log_id=None,
        defect_type=None,
        defect_severity="High",
        is_defective=True,
        inspection_count=1,
        inspected_at=datetime.utcnow(),
    )

    r = ConsolidatedRecord(
        lot_number="L3",
        production_date=date.today(),
        line_number=3,
        shift_leader="C",
        inspections=[insp],
        shipping=None,
    )

    reporter = Reporter()
    result = reporter.summary_metrics([r])

    assert result["total_lots"] == 1
    assert result["total_defective_inspections"] == 1
    assert result["defects_by_type"] == {}
    assert result["line_issues"][3] == 1
