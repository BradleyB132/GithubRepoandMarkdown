from typing import List
from .models import ProductionLog, QualityInspection, ShippingManifest


class SpreadsheetReader:
    """Stub for reading spreadsheets from different teams (quality, shipping, production)."""

    def read_production(self, path: str) -> List[ProductionLog]:
        """Read production spreadsheet and return list of ProductionLog stubs."""
        raise NotImplementedError

    def read_quality(self, path: str) -> List[QualityInspection]:
        """Read quality inspection spreadsheet and return list of QualityInspection stubs."""
        raise NotImplementedError

    def read_shipping(self, path: str) -> List[ShippingManifest]:
        """Read shipping spreadsheet and return list of ShippingManifest stubs."""
        raise NotImplementedError
