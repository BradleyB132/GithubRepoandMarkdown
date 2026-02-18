from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class ProductionLog:
    production_log_id: Optional[int]
    lot_number: str
    line_number: int
    production_date: date
    shift_leader: str


@dataclass
class QualityInspection:
    quality_inspection_id: Optional[int]
    production_log_id: Optional[int]
    defect_type: Optional[str]
    defect_severity: Optional[str]
    is_defective: bool
    inspection_count: int
    inspected_at: Optional[date]


@dataclass
class ShippingManifest:
    shipping_manifest_id: Optional[int]
    production_log_id: Optional[int]
    ship_date: Optional[date]
    destination: Optional[str]
    is_shipped: bool
    is_cancelled: bool


@dataclass
class ConsolidatedRecord:
    lot_number: str
    production_date: date
    line_number: int
    shift_leader: str
    inspections: list
    shipping: Optional[ShippingManifest]
