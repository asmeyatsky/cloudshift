"""Data Transfer Objects for the application boundary."""

from cloudshift.application.dtos.pattern import PatternDTO
from cloudshift.application.dtos.plan import PlanRequest, PlanResult
from cloudshift.application.dtos.report import ReportDTO
from cloudshift.application.dtos.scan import ScanRequest, ScanResult
from cloudshift.application.dtos.transform import TransformRequest, TransformResult
from cloudshift.application.dtos.validation import ValidationRequest, ValidationResult

__all__ = [
    "PatternDTO",
    "PlanRequest",
    "PlanResult",
    "ReportDTO",
    "ScanRequest",
    "ScanResult",
    "TransformRequest",
    "TransformResult",
    "ValidationRequest",
    "ValidationResult",
]
