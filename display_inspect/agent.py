"""陈列检查 Agent：照片预检 → 视觉模型对照标准 → 规则护栏。"""
from __future__ import annotations

import base64
import uuid
from datetime import datetime, timezone

from display_inspect.config import DEEPSEEK_MODEL, VISION_MAX_SIDE, llm_configured
from display_inspect.photo_quality import all_photos_unusable, assess_photo, encode_jpeg, load_rgb
from display_inspect.postprocess import build_report
from display_inspect.schemas import InspectionReport, PhotoQuality
from display_inspect.vision_client import inspect_with_vision


class DisplayInspectionAgent:
    """上传门店照片，输出合规结论、问题、标准、区域、严重度与整改建议。"""

    def run(
        self,
        images: list[tuple[str, bytes]],
        store_id: str = "",
        store_name: str = "",
        extra: str = "",
    ) -> InspectionReport:
        if not images:
            raise ValueError("请至少上传一张门店照片")

        qualities: list[PhotoQuality] = [
            assess_photo(data, filename=filename) for filename, data in images
        ]

        if all_photos_unusable(qualities):
            raw = {
                "overall": {
                    "compliant": "无法判断",
                    "summary": "照片模糊或过暗，相关项无法判断，不能推测整店情况。",
                },
                "findings": [],
            }
        else:
            if not llm_configured():
                raise RuntimeError("未配置 DEEPSEEK_API_KEY")
            payloads = []
            for _filename, data in images:
                jpeg = encode_jpeg(load_rgb(data), max_side=VISION_MAX_SIDE)
                payloads.append(("image/jpeg", base64.b64encode(jpeg).decode("ascii")))
            raw = inspect_with_vision(payloads, self._quality_notes(qualities), extra=extra)

        now = datetime.now(timezone.utc).astimezone()
        return build_report(
            inspection_id=uuid.uuid4().hex[:12],
            created_at=now.strftime("%Y-%m-%d %H:%M:%S"),
            raw=raw,
            qualities=qualities,
            store_id=store_id,
            store_name=store_name,
            image_count=len(images),
            model=DEEPSEEK_MODEL if llm_configured() else "",
        )

    @staticmethod
    def _quality_notes(qualities: list[PhotoQuality]) -> str:
        lines = []
        for i, q in enumerate(qualities, 1):
            extra = "、".join(q.issues) if q.issues else "无明显全局质量问题"
            lines.append(
                f"照片{i}（{q.filename or '未命名'}）：{q.width}x{q.height}，"
                f"亮度 {q.mean_brightness}，边缘强度 {q.edge_strength}，预检：{extra}"
            )
        return "\n".join(lines)
