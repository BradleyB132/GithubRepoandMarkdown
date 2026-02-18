import pytest

from src.consolidator.reports import Reporter


def test_summary_metrics_not_implemented():
    reporter = Reporter()
    with pytest.raises(NotImplementedError):
        reporter.summary_metrics([])


def test_trends_not_implemented():
    reporter = Reporter()
    with pytest.raises(NotImplementedError):
        reporter.trends([])


def test_anomalies_not_implemented():
    reporter = Reporter()
    with pytest.raises(NotImplementedError):
        reporter.anomalies([])
