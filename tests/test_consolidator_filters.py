import pytest

from src.consolidator.filters import RecordFilter


def test_exclude_incomplete_raises():
    f = RecordFilter()
    with pytest.raises(NotImplementedError):
        f.exclude_incomplete([])


def test_filter_by_date_range_raises():
    f = RecordFilter()
    with pytest.raises(NotImplementedError):
        f.filter_by_date_range([], None, None)
