from __future__ import annotations

from typing import Any, Optional

from display_inspector.rules import iter_rules, load_rules
from display_inspector.schema import Finding, Observations, PhotoQuality, Report


def _obs_group(observations: Observations, category_id: str) -> Any:
    return getattr(observations, category_id)


def _field_value(group: Any, name: str) -> Optional[bool]:
    return getattr(group, name, None)


def _present(group: Any) -> Optional[bool]:
    return getattr(group, "present", None)


def _undetermined_reason(
    quality: PhotoQuality,
    observations: Observations,
    present: Optional[bool],
    object_label: str,
    missing_fields: list[str],
) -> str:
    if not quality.usable:
        return "；".join(quality.issues) or "照片有效性不足"
    if observations.occluded:
        return "画面存在遮挡，相关细节无法确认"
    if observations.display_out_of_frame:
        return f"{object_label}局部出画，无法完整核验"
    if present is False:
        return f"画面中未见{object_label}，该组规则不适用"
    if present is None:
        return f"无法确认画面中是否存在{object_label}，建议人工复核"
    if missing_fields:
        return "可见信息不足，无法核验：" + "、".join(missing_fields)
    return "视觉证据不足，建议人工复核"


def _area_for(category: str, evidence: str) -> str:
    if evidence:
        return evidence.split("。")[0][:40]
    return f"{category}区域"


def apply_deterministic_overlays(observations: Observations) -> Observations:
    """Apply rule-table facts that must not depend on model opinion."""
    folded = observations.folded
    if folded.max_stack_count is not None and folded.max_stack_count > 6:
        folded.stack_count_in_range = False
    mannequin = observations.mannequin
    if mannequin.feet_visible is False and mannequin.shoes_paired_if_feet_visible is None:
        mannequin.shoes_paired_if_feet_visible = True
    accessories = observations.accessories
    if accessories.shoes_present is False:
        accessories.shoes_paired = None
        accessories.present = True if accessories.present is None else accessories.present
    display_present = any(
        [
            observations.hanging.present,
            observations.folded.present,
            observations.mannequin.present,
            observations.accessories.present,
        ]
    )
    if observations.price_tag.present is False and display_present:
        if observations.price_tag.present_for_each_group is None:
            observations.price_tag.present_for_each_group = False
    return observations


def build_report(
    *,
    quality: PhotoQuality,
    observations: Observations,
    model_used: str,
    images: list[str],
) -> Report:
    catalog = load_rules()
    observations = apply_deterministic_overlays(observations)
    findings: list[Finding] = []

    for rule in iter_rules():
        group = _obs_group(observations, rule["category_id"])
        present = _present(group)
        notes = (getattr(group, "notes", "") or "").strip()
        evidence = notes or observations.vision_notes or None
        special = rule.get("special")

        if not quality.usable:
            findings.append(
                Finding(
                    rule_id=rule["id"],
                    rule_text=rule["text"],
                    category=rule["category"],
                    status="无法判断",
                    compliant=None,
                    problem=None,
                    area=None,
                    severity=None,
                    suggestion="请重新拍摄清晰、亮度足够、陈列完整入画的照片后再检。",
                    undetermined_reason=_undetermined_reason(
                        quality, observations, present, rule["object_label"], []
                    ),
                    evidence=quality.note,
                )
            )
            continue

        if present is False and rule["category_id"] not in ("cleanliness", "price_tag"):
            # 清洁与安全、价签在有陈列入画时仍需判断；其余对象未入镜则不适用。
            findings.append(
                Finding(
                    rule_id=rule["id"],
                    rule_text=rule["text"],
                    category=rule["category"],
                    status="不适用",
                    compliant=None,
                    undetermined_reason=f"画面中未见{rule['object_label']}",
                    evidence=evidence,
                )
            )
            continue

        if rule["id"] == "A01" and _field_value(group, "shoes_present") is False:
            findings.append(
                Finding(
                    rule_id=rule["id"],
                    rule_text=rule["text"],
                    category=rule["category"],
                    status="不适用",
                    undetermined_reason="画面中未见鞋类，仅见其他配件或未陈列鞋",
                    evidence=evidence,
                )
            )
            continue


        if special == "content_illegible":
            text_legible = _field_value(group, "text_legible")
            tag_present = _field_value(group, "present_for_each_group")
            if tag_present is False:
                # 没有价签时，文字内容无从判断，由 T01 承担「缺价签」；T03 标无法判断。
                findings.append(
                    Finding(
                        rule_id=rule["id"],
                        rule_text=rule["text"],
                        category=rule["category"],
                        status="无法判断",
                        undetermined_reason="内容无法判断",
                        evidence=evidence,
                    )
                )
                continue
            if text_legible is True:
                findings.append(
                    Finding(
                        rule_id=rule["id"],
                        rule_text=rule["text"],
                        category=rule["category"],
                        status="合规",
                        compliant=True,
                        area=_area_for(rule["category"], notes),
                        evidence=evidence,
                    )
                )
                continue
            findings.append(
                Finding(
                    rule_id=rule["id"],
                    rule_text=rule["text"],
                    category=rule["category"],
                    status="无法判断",
                    compliant=None,
                    problem=rule.get("problem"),
                    area=_area_for(rule["category"], notes),
                    severity=None,
                    suggestion=rule.get("suggestion"),
                    undetermined_reason="内容无法判断",
                    evidence=evidence,
                )
            )
            continue

        fields: list[str] = list(rule.get("observation_all_true") or rule.get("observation_fields") or [])
        values = [_field_value(group, name) for name in fields]

        if present is None and all(v is None for v in values):
            findings.append(
                Finding(
                    rule_id=rule["id"],
                    rule_text=rule["text"],
                    category=rule["category"],
                    status="无法判断",
                    undetermined_reason=_undetermined_reason(
                        quality, observations, present, rule["object_label"], fields
                    ),
                    evidence=evidence,
                )
            )
            continue

        if any(v is False for v in values):
            findings.append(
                Finding(
                    rule_id=rule["id"],
                    rule_text=rule["text"],
                    category=rule["category"],
                    status="不合规",
                    compliant=False,
                    problem=rule.get("problem"),
                    area=_area_for(rule["category"], notes),
                    severity=rule.get("severity"),
                    suggestion=rule.get("suggestion"),
                    evidence=evidence,
                )
            )
            continue

        if any(v is None for v in values):
            missing = [name for name, value in zip(fields, values) if value is None]
            findings.append(
                Finding(
                    rule_id=rule["id"],
                    rule_text=rule["text"],
                    category=rule["category"],
                    status="无法判断",
                    undetermined_reason=_undetermined_reason(
                        quality, observations, present, rule["object_label"], missing
                    ),
                    evidence=evidence,
                )
            )
            continue

        findings.append(
            Finding(
                rule_id=rule["id"],
                rule_text=rule["text"],
                category=rule["category"],
                status="合规",
                compliant=True,
                area=_area_for(rule["category"], notes),
                evidence=evidence,
            )
        )

    judged = [f for f in findings if f.status in ("合规", "不合规")]
    issues = [f for f in findings if f.status == "不合规"]
    undetermined = [f for f in findings if f.status == "无法判断"]

    if not quality.usable:
        overall: str = "无法判断"
        overall_compliant = None
    elif issues:
        overall = "不合规"
        overall_compliant = False
    elif not judged:
        overall = "无法判断"
        overall_compliant = None
    else:
        overall = "合规"
        overall_compliant = True

    high = sum(1 for f in issues if f.severity == "高")
    mid = sum(1 for f in issues if f.severity == "中")
    low = sum(1 for f in issues if f.severity == "低")
    if overall == "合规":
        summary = f"按题目规则核验，可见检查项均合规（共 {len(judged)} 项）。"
    elif overall == "无法判断":
        summary = quality.note if not quality.usable else (
            f"可见信息不足以形成整店结论，{len(undetermined)} 项输出「无法判断」，建议人工复核或补拍。"
        )
    else:
        summary = (
            f"按题目规则核验为不合规：高 {high} 项、中 {mid} 项、低 {low} 项；"
            f"另有 {len(undetermined)} 项无法判断。"
        )

    return Report(
        overall_status=overall,  # type: ignore[arg-type]
        overall_compliant=overall_compliant,
        photo_validity=quality,
        findings=findings,
        issues=issues,
        undetermined_items=undetermined,
        summary=summary,
        rule_source=catalog["source"],
        model_used=model_used,
        images=images,
        extra={"severity_definition": catalog["severity_definition"]},
    )


def merge_reports(reports: list[Report]) -> Report:
    if len(reports) == 1:
        return reports[0]
    by_id: dict[str, list[Finding]] = {}
    for report in reports:
        for finding in report.findings:
            by_id.setdefault(finding.rule_id, []).append(finding)

    merged: list[Finding] = []
    for rule in iter_rules():
        group = by_id.get(rule["id"], [])
        if not group:
            continue
        noncomp = next((f for f in group if f.status == "不合规"), None)
        if noncomp:
            merged.append(noncomp)
            continue
        ok = next((f for f in group if f.status == "合规"), None)
        if ok:
            merged.append(ok)
            continue
        undet = next((f for f in group if f.status == "无法判断"), None)
        merged.append(undet or group[0])

    quality = reports[0].photo_validity
    usable_any = any(r.photo_validity.usable for r in reports)
    if usable_any:
        quality = next(r.photo_validity for r in reports if r.photo_validity.usable)

    dummy = Report(
        overall_status="无法判断",
        photo_validity=quality,
        findings=merged,
        issues=[f for f in merged if f.status == "不合规"],
        undetermined_items=[f for f in merged if f.status == "无法判断"],
        model_used=" + ".join(sorted({r.model_used for r in reports})),
        images=[name for r in reports for name in r.images],
        rule_source=reports[0].rule_source,
        extra=reports[0].extra,
    )
    # Rebuild overall/summary via the same policy.
    observations = Observations()
    rebuilt = build_report(
        quality=quality,
        observations=observations,
        model_used=dummy.model_used,
        images=dummy.images,
    )
    rebuilt.findings = merged
    rebuilt.issues = [f for f in merged if f.status == "不合规"]
    rebuilt.undetermined_items = [f for f in merged if f.status == "无法判断"]
    judged = [f for f in merged if f.status in ("合规", "不合规")]
    if not quality.usable:
        rebuilt.overall_status = "无法判断"
        rebuilt.overall_compliant = None
    elif rebuilt.issues:
        rebuilt.overall_status = "不合规"
        rebuilt.overall_compliant = False
    elif not judged:
        rebuilt.overall_status = "无法判断"
        rebuilt.overall_compliant = None
    else:
        rebuilt.overall_status = "合规"
        rebuilt.overall_compliant = True
    high = sum(1 for f in rebuilt.issues if f.severity == "高")
    mid = sum(1 for f in rebuilt.issues if f.severity == "中")
    low = sum(1 for f in rebuilt.issues if f.severity == "低")
    if rebuilt.overall_status == "合规":
        rebuilt.summary = f"多图合并后，可见检查项均合规（共 {len(judged)} 项）。"
    elif rebuilt.overall_status == "无法判断":
        rebuilt.summary = "多图合并后仍不足以形成整店结论，建议补拍或人工复核。"
    else:
        rebuilt.summary = (
            f"多图合并后为不合规：高 {high} 项、中 {mid} 项、低 {low} 项；"
            f"另有 {len(rebuilt.undetermined_items)} 项无法判断。"
        )
    rebuilt.rule_source = dummy.rule_source
    rebuilt.model_used = dummy.model_used
    rebuilt.images = dummy.images
    rebuilt.extra = dummy.extra
    return rebuilt
