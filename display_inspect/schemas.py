"""检查报告的结构化输出。"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

CompliantStatus = Literal["合规", "不合规", "无法判断"]
Severity = Literal["高", "中", "低", "无法判断"]


class PhotoQuality(BaseModel):
    filename: str = ""
    width: int = 0
    height: int = 0
    mean_brightness: float = 0
    edge_strength: float = 0
    too_dark: bool = False
    too_bright: bool = False
    blurry: bool = False
    issues: list[str] = Field(default_factory=list)
    notes: str = ""


class Finding(BaseModel):
    category: str
    compliant: CompliantStatus
    issue: str
    standard: str
    region: str
    severity: Severity
    suggestion: str
    visible_in_photo: bool = True


class InspectionReport(BaseModel):
    inspection_id: str
    store_id: str = ""
    store_name: str = ""
    created_at: str
    overall: CompliantStatus
    summary: str
    photo_quality: list[PhotoQuality] = Field(default_factory=list)
    findings: list[Finding] = Field(default_factory=list)
    image_count: int = 0
    model: str = ""
    uncertain: bool = False

    def to_public_dict(self) -> dict[str, Any]:
        return self.model_dump()
