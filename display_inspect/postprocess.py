"""规则护栏：补齐类别、强制「无法判断」、校准严重度与总评。"""
from __future__ import annotations

from display_inspect.rules import (
    CATEGORIES,
    HIGH_ISSUE_KEYWORDS,
    MEDIUM_ISSUE_KEYWORDS,
    standard_for_category,
)
from display_inspect.schemas import Finding, InspectionReport, PhotoQuality

UNCLEAR = "无法判断"
UNCLEAR_SUGGESTION = "请补拍该区域清晰、完整、无遮挡的照片后再检查，勿凭推测整改。"


def _norm_status(value: object) -> str:
    text = str(value or "").strip()
    if text in ("合规", "不合规", "无法判断"):
        return text
    if any(k in text for k in ("无法", "不确定", "看不清", "未入镜", "无法判断")):
        return UNCLEAR
    if any(k in text for k in ("不合规", "违规", "不通过", "否")):
        return "不合规"
    if any(k in text for k in ("合规", "通过", "是")):
        return "合规"
    return UNCLEAR


def _norm_severity(value: object) -> str:
    text = str(value or "").strip()
    if text in ("高", "中", "低", "无法判断"):
        return text
    lowered = text.lower()
    if lowered in ("high", "3"):
        return "高"
    if lowered in ("medium", "mid", "2"):
        return "中"
    if lowered in ("low", "1"):
        return "低"
    return UNCLEAR


def _calibrate_severity(category: str, issue: str, suggestion: str, current: str, compliant: str) -> str:
    if compliant == UNCLEAR:
        return UNCLEAR
    blob = f"{category}{issue}{suggestion}"
    if any(k in blob for k in HIGH_ISSUE_KEYWORDS):
        return "高"
    if current in ("高", "中", "低"):
        if current == "高" and not any(k in blob for k in HIGH_ISSUE_KEYWORDS) and category != "清洁与安全":
            # 保留模型判断，除非明显是视觉对齐类
            if any(k in blob for k in ("对齐", "间距", "色序", "衣架颜色", "衣架方向")):
                return "低"
        return current
    if any(k in blob for k in MEDIUM_ISSUE_KEYWORDS):
        return "中"
    if compliant == "合规":
        return "低"
    return "低"


def _force_unclear_finding(category: str, reason: str) -> Finding:
    return Finding(
        category=category,
        compliant=UNCLEAR,
        issue=reason if UNCLEAR in reason else f"{reason}，{UNCLEAR}",
        standard=standard_for_category(category),
        region=UNCLEAR,
        severity=UNCLEAR,
        suggestion=UNCLEAR_SUGGESTION,
        visible_in_photo=False,
    )


def _parse_finding(item: dict, category: str) -> Finding:
    visible = item.get("visible_in_photo")
    if isinstance(visible, str):
        visible = visible.lower() not in ("false", "0", "no", "否")
    visible = True if visible is None else bool(visible)

    compliant = _norm_status(item.get("compliant"))
    issue = str(item.get("issue") or "").strip() or UNCLEAR
    region = str(item.get("region") or "").strip() or UNCLEAR
    suggestion = str(item.get("suggestion") or "").strip() or UNCLEAR_SUGGESTION
    standard = str(item.get("standard") or "").strip() or standard_for_category(category)

    if not visible:
        compliant = UNCLEAR
        if UNCLEAR not in issue:
            issue = f"画面中未出现该品类或无法看清，{UNCLEAR}"
        region = region if region else UNCLEAR
        suggestion = UNCLEAR_SUGGESTION

    if category == "价签" and any(k in issue for k in ("看不清", "模糊", "无法辨认")) and "内容无法判断" not in issue:
        if "文字" in issue or "价格" in issue or "内容" in issue:
            issue = issue.rstrip("。") + "；内容无法判断"

    if any(k in issue for k in ("无法判断", "无法看清", "未入镜", "看不清整店")):
        if compliant == "合规":
            compliant = UNCLEAR

    severity = _calibrate_severity(
        category,
        issue,
        suggestion,
        _norm_severity(item.get("severity")),
        compliant,
    )
    return Finding(
        category=category,
        compliant=compliant,  # type: ignore[arg-type]
        issue=issue,
        standard=standard,
        region=region,
        severity=severity,  # type: ignore[arg-type]
        suggestion=suggestion,
        visible_in_photo=bool(visible),
    )


def _overall_from_findings(findings: list[Finding], photo_unusable: bool) -> str:
    statuses = [f.compliant for f in findings if f.category != "照片有效性"]
    photo = next((f for f in findings if f.category == "照片有效性"), None)
    if any(s == "不合规" for s in statuses):
        return "不合规"
    if photo and photo.compliant == "不合规" and photo_unusable:
        return UNCLEAR
    if statuses and all(s == UNCLEAR for s in statuses):
        return UNCLEAR
    if any(s == UNCLEAR for s in statuses) and not any(s == "不合规" for s in statuses):
        # 可见项都合规、部分无法判断：总评无法判断（不能声称整店合规）
        visible_ok = [f for f in findings if f.category != "照片有效性" and f.compliant == "合规"]
        if visible_ok and all(
            f.compliant in ("合规", UNCLEAR) for f in findings if f.category != "照片有效性"
        ):
            return UNCLEAR
        return UNCLEAR
    if statuses and all(s == "合规" for s in statuses):
        return "合规"
    return UNCLEAR


def build_report(
    *,
    inspection_id: str,
    created_at: str,
    raw: dict,
    qualities: list[PhotoQuality],
    store_id: str = "",
    store_name: str = "",
    image_count: int = 0,
    model: str = "",
) -> InspectionReport:
    photo_unusable = bool(qualities) and all(q.too_dark or q.blurry for q in qualities)
    raw_findings = raw.get("findings") if isinstance(raw.get("findings"), list) else []
    by_cat: dict[str, dict] = {}
    for item in raw_findings:
        if not isinstance(item, dict):
            continue
        cat = str(item.get("category") or "").strip()
        if cat in CATEGORIES:
            by_cat[cat] = item

    findings: list[Finding] = []
    for category in CATEGORIES:
        if photo_unusable and category != "照片有效性":
            reasons = []
            for q in qualities:
                reasons.extend(q.issues)
            reason = "、".join(dict.fromkeys(reasons)) or "照片质量不足"
            findings.append(
                _force_unclear_finding(
                    category,
                    f"照片{reason}，相关项{UNCLEAR}，不能推测整店情况",
                )
            )
            continue
        if category in by_cat:
            findings.append(_parse_finding(by_cat[category], category))
        else:
            findings.append(
                _force_unclear_finding(category, f"模型未给出该类别结论，{UNCLEAR}")
            )

    if photo_unusable:
        issues = []
        for q in qualities:
            issues.extend(q.issues)
        issue_text = "、".join(dict.fromkeys(issues)) or "质量不足"
        findings[0] = Finding(
            category="照片有效性",
            compliant="不合规",
            issue=f"照片{issue_text}，不具备可靠巡检条件",
            standard=standard_for_category("照片有效性"),
            region="全图",
            severity="中",
            suggestion="请在光线充足处重新拍摄清晰、完整、无遮挡的陈列照片。",
            visible_in_photo=True,
        )

    overall_raw = ""
    overall_obj = raw.get("overall")
    if isinstance(overall_obj, dict):
        overall_raw = str(overall_obj.get("compliant") or "")
        summary = str(overall_obj.get("summary") or "").strip()
    else:
        summary = str(raw.get("summary") or "").strip()
        overall_raw = str(raw.get("compliant") or "")

    overall = _overall_from_findings(findings, photo_unusable)
    if _norm_status(overall_raw) == "不合规" and overall != UNCLEAR:
        overall = "不合规"

    if not summary:
        bad = [f for f in findings if f.compliant == "不合规"]
        unclear = [f for f in findings if f.compliant == UNCLEAR]
        if overall == "合规":
            summary = "可见陈列项均符合总部标准。"
        elif overall == "不合规":
            summary = "发现 " + "；".join(f.issue for f in bad[:3])
        else:
            summary = "部分或全部项目证据不足，无法判断整店是否合规。" + (
                " " + "；".join(f.issue for f in unclear[:2]) if unclear else ""
            )

    if overall == UNCLEAR and UNCLEAR not in summary:
        summary = summary.rstrip("。") + "。无法判断。"

    uncertain = overall == UNCLEAR or any(f.compliant == UNCLEAR for f in findings)

    return InspectionReport(
        inspection_id=inspection_id,
        store_id=store_id,
        store_name=store_name,
        created_at=created_at,
        overall=overall,  # type: ignore[arg-type]
        summary=summary,
        photo_quality=qualities,
        findings=findings,
        image_count=image_count,
        model=model,
        uncertain=uncertain,
    )
