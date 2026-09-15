"""DeepSeek 视觉调用：把门店照片与检查标准交给模型，强制 JSON 输出。"""
from __future__ import annotations

import json
import logging
import re
from typing import Any

from openai import OpenAI

from display_inspect.config import (
    DEEPSEEK_API_KEY,
    DEEPSEEK_BASE_URL,
    DEEPSEEK_MODEL,
    VISION_TIMEOUT,
)
from display_inspect.rules import rules_for_prompt

logger = logging.getLogger("display_inspect")

SYSTEM_PROMPT = """你是服装连锁品牌总部的陈列合规检查 Agent。
你只根据照片中【可见且可确认】的证据做判断，并对照总部统一标准输出结构化结果。

绝对规则：
1. 模糊、过暗、遮挡、局部未入镜时，相关检查项必须输出「无法判断」，禁止猜测，禁止用局部照片推断整店或其他未入镜区域。
2. 画面中未出现的品类（如没有模特、没有叠装），该项 compliant 必须为「无法判断」，issue 写明「画面中未出现该品类，无法判断」，suggestion 写「请补拍该区域清晰照片」。
3. 价签：可判断有无、是否直立/正向/被遮挡；看不清文字时，issue 中关于文字的部分只能写「内容无法判断」，不得编造价格或促销文案。
4. 严重度只能是 高 / 中 / 低 / 无法判断。
   - 高：安全、疏散、消防占用、设施松脱倾斜坠落、商品落地。
   - 中：影响可售性或整洁（大面积空挂、杂物、不成双、悬出层板、吊牌外露、缺价签等）。
   - 低：对齐、间距、色序、衣架一致性等视觉问题。
   - 无法判断：证据不足时必须用这个，不要给高/中/低。
5. 每个类别都要输出一条 finding（七类：照片有效性、挂装、叠装、模特、鞋包配件、价签、清洁与安全）。
6. 若某项合规，issue 写「未见明显问题」，suggestion 写「保持现状」，severity 对合规项用「低」（照片有效性合规也用低）。
7. region 要具体到画面位置（如「左侧挂杆中段」「中岛叠装上层」）；无法判断时 region 写「无法判断」或「未入镜」。
8. standard 必须逐字引用对应检查标准，不要改写。
9. 只输出一个 JSON 对象，不要 Markdown，不要额外解释。

JSON 格式：
{
  "photo_validity": {
    "usable": true,
    "issues": [],
    "notes": ""
  },
  "overall": {
    "compliant": "合规|不合规|无法判断",
    "summary": "一句话总结，不确定时必须出现「无法判断」"
  },
  "findings": [
    {
      "category": "照片有效性",
      "visible_in_photo": true,
      "compliant": "合规",
      "issue": "未见明显问题",
      "standard": "……",
      "region": "全图",
      "severity": "低",
      "suggestion": "保持现状"
    }
  ]
}
"""


def _user_prompt(quality_notes: str, extra: str = "") -> str:
    extra_block = f"\n补充说明：{extra}\n" if extra else ""
    return (
        "请检查下列门店陈列照片。\n"
        f"{rules_for_prompt()}\n\n"
        "本地预检（仅供参考，遮挡/未入镜仍以你看到的画面为准）：\n"
        f"{quality_notes}\n"
        f"{extra_block}\n"
        "请按系统要求输出 JSON。证据不足时相关项必须「无法判断」。"
    )


def _extract_json(text: str) -> dict[str, Any]:
    if not text:
        raise ValueError("模型返回空内容")
    raw = text.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    candidates = [raw]
    match = re.search(r"\{[\s\S]*\}", raw)
    if match:
        candidates.append(match.group(0))
    last_error: Exception | None = None
    for candidate in candidates:
        try:
            data = json.loads(candidate)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError as e:
            last_error = e
            repaired = _repair_json(candidate)
            if repaired:
                try:
                    data = json.loads(repaired)
                    if isinstance(data, dict):
                        return data
                except json.JSONDecodeError as e2:
                    last_error = e2
    raise ValueError(f"模型未返回完整 JSON：{last_error}")


def _repair_json(raw: str) -> str | None:
    text = raw.strip()
    if not text.startswith("{"):
        return None
    # 去掉截断的末尾残片，补齐括号
    text = re.sub(r",\s*$", "", text)
    opens = text.count("{") + text.count("[")
    closes = text.count("}") + text.count("]")
    if opens > closes:
        text += "]" * max(0, text.count("[") - text.count("]"))
        text += "}" * max(0, text.count("{") - text.count("}"))
    return text


def inspect_with_vision(
    image_payloads: list[tuple[str, str]],
    quality_notes: str,
    extra: str = "",
) -> dict[str, Any]:
    """image_payloads: list of (mime, base64_data)."""
    if not DEEPSEEK_API_KEY:
        raise RuntimeError("未配置 DEEPSEEK_API_KEY，无法调用视觉模型。")

    client = OpenAI(
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
        timeout=VISION_TIMEOUT,
    )
    content: list[dict[str, Any]] = [
        {"type": "text", "text": _user_prompt(quality_notes, extra)},
    ]
    for mime, b64 in image_payloads:
        content.append(
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:{mime};base64,{b64}",
                    "detail": "high",
                },
            }
        )

    last_error: Exception | None = None
    for thinking in (True, False):
        extra_body = {"thinking": {"type": "enabled" if thinking else "disabled"}}
        if thinking:
            extra_body["reasoning_effort"] = "low"
        try:
            resp = client.chat.completions.create(
                model=DEEPSEEK_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": content},
                ],
                response_format={"type": "json_object"},
                max_tokens=8192,
                extra_body=extra_body,
            )
            text = (resp.choices[0].message.content or "").strip()
            return _extract_json(text)
        except Exception as e:
            last_error = e
            logger.warning("vision call failed (thinking=%s): %s", thinking, e)
    raise RuntimeError(f"视觉检查失败：{last_error}") from last_error
