"""总部统一陈列检查标准。供 Agent 提示词、后处理与前端「检查标准」页共用。"""
from __future__ import annotations

from typing import Any

CATEGORIES: list[str] = [
    "照片有效性",
    "挂装",
    "叠装",
    "模特",
    "鞋包配件",
    "价签",
    "清洁与安全",
]

COMPLIANT_VALUES = ("合规", "不合规", "无法判断")
SEVERITY_VALUES = ("高", "中", "低", "无法判断")

RULES: list[dict[str, Any]] = [
    {
        "id": "photo.validity",
        "category": "照片有效性",
        "title": "照片必须可检",
        "standard": "照片应清晰、曝光正常、陈列主体完整入镜、无大面积遮挡。模糊、过暗、遮挡、局部未入镜时，相关项必须输出「无法判断」，不能推测整店情况。",
        "severity_hint": "中",
        "checks": ["是否模糊", "是否过暗", "是否被遮挡", "是否局部未入镜"],
    },
    {
        "id": "hang.consistency",
        "category": "挂装",
        "title": "衣架与分组一致",
        "standard": "同组衣架方向、材质和颜色一致；间距均匀；衣物自然垂直；按品类与连续色序分组；不得大面积空挂。",
        "severity_hint": "低",
        "checks": ["衣架方向/材质/颜色", "间距", "衣物垂直", "品类与色序", "空挂"],
    },
    {
        "id": "fold.alignment",
        "category": "叠装",
        "title": "折叠整齐且不超件",
        "standard": "同堆折叠宽度与前沿对齐；每堆 3–6 件、最多 6 件；堆放平稳；商品不得落地或悬出层板。",
        "severity_hint": "低",
        "checks": ["宽度与前沿对齐", "每堆件数 3–6（最多 6）", "堆放平稳", "落地或悬出层板"],
    },
    {
        "id": "mannequin.complete",
        "category": "模特",
        "title": "模特着装完整稳固",
        "standard": "上下装完整；露脚时鞋应成双；衣物平整、吊牌不外露；模特与底座稳固。",
        "severity_hint": "中",
        "checks": ["上下装完整", "露脚成双鞋", "衣物平整", "吊牌不外露", "模特与底座稳固"],
    },
    {
        "id": "acc.alignment",
        "category": "鞋包配件",
        "title": "鞋包配件成双对齐",
        "standard": "鞋应成双、方向一致；商品等距对齐；不得悬出层板或遮挡价签。",
        "severity_hint": "中",
        "checks": ["成双", "方向一致", "等距对齐", "悬出层板", "遮挡价签"],
    },
    {
        "id": "price.tag",
        "category": "价签",
        "title": "价签齐全可读",
        "standard": "每个陈列组有价签；价签直立、正向、无遮挡；看不清文字时仅能判断「内容无法判断」。",
        "severity_hint": "中",
        "checks": ["每组有价签", "直立正向", "无遮挡", "文字是否可读"],
    },
    {
        "id": "safety.clean",
        "category": "清洁与安全",
        "title": "场地清洁且通道畅通",
        "standard": "无垃圾、污渍、纸箱、补货袋等杂物；通道、疏散区域和消防设备不得被占用；货架、层板、挂杆不得松脱或倾斜。",
        "severity_hint": "高",
        "checks": ["杂物", "通道/疏散/消防占用", "货架层板挂杆松脱或倾斜"],
    },
]

SEVERITY_GUIDE = {
    "高": "安全、疏散、设施坠落、商品落地",
    "中": "影响陈列可售性或整洁（空挂、杂物、不成双、悬出层板、吊牌外露等）",
    "低": "对齐、间距、色序、一致性等视觉问题",
}

HIGH_ISSUE_KEYWORDS = (
    "落地",
    "掉落",
    "坠落",
    "消防",
    "疏散",
    "安全出口",
    "堵塞通道",
    "占用通道",
    "占用疏散",
    "松脱",
    "倾斜",
    "倒塌",
    "摇晃不稳",
)
MEDIUM_ISSUE_KEYWORDS = (
    "空挂",
    "杂物",
    "垃圾",
    "污渍",
    "纸箱",
    "补货袋",
    "悬出",
    "吊牌外露",
    "不成双",
    "单只",
    "缺鞋",
    "上下装不完整",
    "缺价签",
    "无价签",
    "遮挡价签",
    "不稳固",
)


def rules_for_prompt() -> str:
    lines = ["【检查标准】"]
    for rule in RULES:
        lines.append(f"- {rule['category']}｜{rule['title']}：{rule['standard']}")
    lines.append("【严重度】")
    for level, desc in SEVERITY_GUIDE.items():
        lines.append(f"- {level}：{desc}")
    return "\n".join(lines)


def standard_for_category(category: str) -> str:
    for rule in RULES:
        if rule["category"] == category:
            return str(rule["standard"])
    return ""


def public_rules_payload() -> dict[str, Any]:
    return {
        "categories": CATEGORIES,
        "severity": SEVERITY_GUIDE,
        "rules": RULES,
    }
