import pytest

from src.consolidator.io import SpreadsheetReader


def test_read_production_not_implemented():
    reader = SpreadsheetReader()
    with pytest.raises(NotImplementedError):
        reader.read_production('path')


def test_read_quality_not_implemented():
    reader = SpreadsheetReader()
    with pytest.raises(NotImplementedError):
        reader.read_quality('path')


def test_read_shipping_not_implemented():
    reader = SpreadsheetReader()
    with pytest.raises(NotImplementedError):
        reader.read_shipping('path')
