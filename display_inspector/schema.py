from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

Status = Literal["合规", "不合规", "无法判断", "不适用"]
Severity = Literal["高", "中", "低"]
OverallStatus = Literal["合规", "不合规", "无法判断"]


class PhotoQuality(BaseModel):
    usable: bool
    blurry: bool = False
    too_dark: bool = False
    overexposed: bool = False
    too_small: bool = False
    laplacian_var: float = 0.0
    brightness: float = 0.0
    issues: list[str] = Field(default_factory=list)
    note: str = ""


class HangingObs(BaseModel):
    present: Optional[bool] = None
    hanger_direction_consistent: Optional[bool] = None
    hanger_material_consistent: Optional[bool] = None
    hanger_color_consistent: Optional[bool] = None
    spacing_even: Optional[bool] = None
    clothes_hang_vertically: Optional[bool] = None
    grouped_by_category: Optional[bool] = None
    color_sequence_continuous: Optional[bool] = None
    no_large_empty_hangers: Optional[bool] = None
    notes: str = ""


class FoldedObs(BaseModel):
    present: Optional[bool] = None
    fold_width_consistent: Optional[bool] = None
    front_edges_aligned: Optional[bool] = None
    stack_count_in_range: Optional[bool] = None
    max_stack_count: Optional[int] = None
    stack_stable: Optional[bool] = None
    not_touching_floor: Optional[bool] = None
    not_overhanging_shelf: Optional[bool] = None
    notes: str = ""


class MannequinObs(BaseModel):
    present: Optional[bool] = None
    complete_outfit: Optional[bool] = None
    feet_visible: Optional[bool] = None
    shoes_paired_if_feet_visible: Optional[bool] = None
    clothing_smooth: Optional[bool] = None
    price_tags_hidden: Optional[bool] = None
    base_stable: Optional[bool] = None
    notes: str = ""


class AccessoriesObs(BaseModel):
    present: Optional[bool] = None
    shoes_present: Optional[bool] = None
    shoes_paired: Optional[bool] = None
    facing_consistent: Optional[bool] = None
    equally_spaced_aligned: Optional[bool] = None
    not_overhanging_or_blocking_tags: Optional[bool] = None
    notes: str = ""


class PriceTagObs(BaseModel):
    present: Optional[bool] = None
    present_for_each_group: Optional[bool] = None
    upright_forward_unobstructed: Optional[bool] = None
    text_legible: Optional[bool] = None
    notes: str = ""


class CleanlinessObs(BaseModel):
    no_clutter: Optional[bool] = None
    aisles_and_safety_clear: Optional[bool] = None
    fixtures_stable: Optional[bool] = None
    notes: str = ""


class Observations(BaseModel):
    hanging: HangingObs = Field(default_factory=HangingObs)
    folded: FoldedObs = Field(default_factory=FoldedObs)
    mannequin: MannequinObs = Field(default_factory=MannequinObs)
    accessories: AccessoriesObs = Field(default_factory=AccessoriesObs)
    price_tag: PriceTagObs = Field(default_factory=PriceTagObs)
    cleanliness: CleanlinessObs = Field(default_factory=CleanlinessObs)
    occluded: Optional[bool] = None
    display_out_of_frame: Optional[bool] = None
    vision_notes: str = ""


class Finding(BaseModel):
    rule_id: str
    rule_text: str
    category: str
    status: Status
    compliant: Optional[bool] = None
    problem: Optional[str] = None
    area: Optional[str] = None
    severity: Optional[Severity] = None
    suggestion: Optional[str] = None
    undetermined_reason: Optional[str] = None
    evidence: Optional[str] = None


class Report(BaseModel):
    overall_status: OverallStatus
    overall_compliant: Optional[bool] = None
    photo_validity: PhotoQuality
    findings: list[Finding] = Field(default_factory=list)
    issues: list[Finding] = Field(default_factory=list)
    undetermined_items: list[Finding] = Field(default_factory=list)
    summary: str = ""
    rule_source: str = ""
    model_used: str = ""
    images: list[str] = Field(default_factory=list)
    extra: dict[str, Any] = Field(default_factory=dict)
