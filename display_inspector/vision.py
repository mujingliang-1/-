from __future__ import annotations

import json
import os
import re
from io import BytesIO
from typing import Any, Optional

from PIL import Image

from display_inspector.schema import (
    AccessoriesObs,
    CleanlinessObs,
    FoldedObs,
    HangingObs,
    MannequinObs,
    Observations,
    PriceTagObs,
)

OBSERVATION_INSTRUCTIONS = """你是服装门店陈列检查的视觉核验器。
你只能观察照片里实际看见的内容，把结果填入 JSON。不得用常识猜测整店，不得发明规则。

字段取值：
- true：照片中能清楚看到，且符合该陈述
- false：照片中能清楚看到，且不符合该陈述
- null：看不清、被遮挡、出画、对象可能不在画面中，无法确认

对象未出现在画面中时，该组 present=false，其余字段全部 null。
不要输出 JSON 以外的文字。

JSON 结构：
{
  "occluded": false,
  "display_out_of_frame": false,
  "vision_notes": "一句话描述可见区域",
  "hanging": {
    "present": true,
    "hanger_direction_consistent": true,
    "hanger_material_consistent": true,
    "hanger_color_consistent": true,
    "spacing_even": true,
    "clothes_hang_vertically": true,
    "grouped_by_category": true,
    "color_sequence_continuous": true,
    "no_large_empty_hangers": true,
    "notes": "位置与证据"
  },
  "folded": {
    "present": true,
    "fold_width_consistent": true,
    "front_edges_aligned": true,
    "stack_count_in_range": true,
    "max_stack_count": 4,
    "stack_stable": true,
    "not_touching_floor": true,
    "not_overhanging_shelf": true,
    "notes": "位置与证据"
  },
  "mannequin": {
    "present": true,
    "complete_outfit": true,
    "feet_visible": false,
    "shoes_paired_if_feet_visible": true,
    "clothing_smooth": true,
    "price_tags_hidden": true,
    "base_stable": true,
    "notes": "位置与证据"
  },
  "accessories": {
    "present": false,
    "shoes_present": false,
    "shoes_paired": null,
    "facing_consistent": null,
    "equally_spaced_aligned": null,
    "not_overhanging_or_blocking_tags": null,
    "notes": ""
  },
  "price_tag": {
    "present": true,
    "present_for_each_group": true,
    "upright_forward_unobstructed": true,
    "text_legible": false,
    "notes": "价签位置；文字看不清时 text_legible=false"
  },
  "cleanliness": {
    "no_clutter": true,
    "aisles_and_safety_clear": true,
    "fixtures_stable": true,
    "notes": "垃圾/纸箱/补货袋/污渍/堵通道/货架倾斜等证据"
  }
}

注意：
- no_large_empty_hangers=true 表示没有大面积空衣架；若有大面积空衣架则为 false。
- stack_count_in_range=true 表示每摞都在 3-6 件（含），最多 6 件。
- not_touching_floor=true 表示商品没有触地。
- no_clutter=true 表示没有垃圾、污渍、纸箱、补货袋等杂物。
- aisles_and_safety_clear=true 表示通道、疏散区域、消防设施未被占用。
"""


def resize_for_vision(image: Image.Image, max_side: int = 1280) -> Image.Image:
    image = image.convert("RGB")
    w, h = image.size
    scale = max_side / max(w, h)
    if scale < 1:
        image = image.resize((int(w * scale), int(h * scale)))
    return image


def image_to_jpeg_bytes(image: Image.Image) -> bytes:
    buf = BytesIO()
    resize_for_vision(image).save(buf, format="JPEG", quality=85)
    return buf.getvalue()


def parse_json_object(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    match = re.search(r"\{.*\}", text, flags=re.S)
    if not match:
        raise ValueError("模型未返回 JSON 对象")
    raw = match.group(0)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        raw2 = re.sub(r",\s*([}\]])", r"\1", raw)
        raw2 = raw2.replace("true", "true").replace("false", "false")
        data = json.loads(raw2)
    if not isinstance(data, dict):
        raise ValueError("JSON 根节点不是对象")
    return data


def observations_from_dict(data: dict[str, Any]) -> Observations:
    def section(name: str, cls):
        payload = data.get(name) or {}
        if not isinstance(payload, dict):
            payload = {}
        known = {k: payload.get(k) for k in cls.model_fields}
        return cls(**known)

    return Observations(
        hanging=section("hanging", HangingObs),
        folded=section("folded", FoldedObs),
        mannequin=section("mannequin", MannequinObs),
        accessories=section("accessories", AccessoriesObs),
        price_tag=section("price_tag", PriceTagObs),
        cleanliness=section("cleanliness", CleanlinessObs),
        occluded=data.get("occluded"),
        display_out_of_frame=data.get("display_out_of_frame"),
        vision_notes=str(data.get("vision_notes") or ""),
    )


class VisionBackend:
    name = "unknown"

    def observe(self, image: Image.Image, user_note: str = "", region_hint: str = "") -> Observations:
        raise NotImplementedError


def _user_prompt(user_note: str, region_hint: str) -> str:
    parts = [OBSERVATION_INSTRUCTIONS]
    if region_hint and region_hint != "全景":
        parts.append(f"拍摄区域提示：{region_hint}。未出现的对象 present=false。")
    if user_note.strip():
        parts.append("门店补充说明（仅作参考，仍以照片可见内容为准）：" + user_note.strip())
    parts.append("请根据这张门店照片输出 JSON。")
    return "\n".join(parts)


DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_VISION_MODEL = "deepseek-flash"
DEFAULT_CLOUD_MODEL = "glm-4v-flash"


class OpenAICompatibleVision(VisionBackend):
    def __init__(self, api_key: str, base_url: Optional[str], model: str):
        from openai import OpenAI

        self.name = f"openai-compatible:{model}"
        self.base_url = base_url.rstrip("/") if base_url else None
        kwargs: dict[str, Any] = {"api_key": api_key}
        if self.base_url:
            kwargs["base_url"] = self.base_url
        self.client = OpenAI(**kwargs)
        self.model = model

    def observe(self, image: Image.Image, user_note: str = "", region_hint: str = "") -> Observations:
        import base64

        jpeg = image_to_jpeg_bytes(image)
        data_url = "data:image/jpeg;base64," + base64.b64encode(jpeg).decode("ascii")
        prompt = _user_prompt(user_note, region_hint)
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                }
            ],
            "temperature": 0,
        }
        try:
            kwargs["response_format"] = {"type": "json_object"}
            resp = self.client.chat.completions.create(**kwargs)
        except Exception:
            kwargs.pop("response_format", None)
            resp = self.client.chat.completions.create(**kwargs)
        text = resp.choices[0].message.content or ""
        return observations_from_dict(parse_json_object(text))


_LOCAL_MODEL = None
_LOCAL_PROCESSOR = None
_LOCAL_ERROR: Optional[str] = None
DEFAULT_LOCAL_VLM = "HuggingFaceTB/SmolVLM2-2.2B-Instruct"


def local_model_status() -> dict[str, Any]:
    return {
        "loaded": _LOCAL_MODEL is not None,
        "error": _LOCAL_ERROR,
        "model_id": os.environ.get("LOCAL_VLM_ID", DEFAULT_LOCAL_VLM),
    }


def load_local_model() -> None:
    global _LOCAL_MODEL, _LOCAL_PROCESSOR, _LOCAL_ERROR
    if _LOCAL_MODEL is not None:
        return
    model_id = os.environ.get("LOCAL_VLM_ID", DEFAULT_LOCAL_VLM)
    try:
        import torch
        from transformers import AutoProcessor

        try:
            from transformers import AutoModelForImageTextToText as ModelCls
        except ImportError:
            from transformers import AutoModelForVision2Seq as ModelCls  # type: ignore

        _LOCAL_PROCESSOR = AutoProcessor.from_pretrained(model_id)
        kwargs: dict[str, Any] = {}
        try:
            _LOCAL_MODEL = ModelCls.from_pretrained(model_id, dtype=torch.float32)
        except TypeError:
            _LOCAL_MODEL = ModelCls.from_pretrained(model_id, torch_dtype=torch.float32)
        _LOCAL_MODEL.eval()
        _LOCAL_ERROR = None
        _ = kwargs
    except Exception as exc:  # noqa: BLE001
        _LOCAL_ERROR = str(exc)
        raise


def parse_tristate(text: str) -> Optional[bool]:
    t = text.strip().lower()
    if any(k in t for k in ("unsure", "unknown", "not sure", "无法", "不确定", "cannot tell")):
        return None
    t = re.sub(r"[^a-z\u4e00-\u9fff]+", " ", t).strip()
    if t.startswith(("yes", "true", "是", "有", "可见")):
        return True
    if t.startswith(("no", "false", "否", "没有", "不可见")):
        return False
    return None


class LocalSmolVLM(VisionBackend):
    """Local VLM uses short YES/NO questions. Python rule engine maps answers to rule_id."""

    def __init__(self) -> None:
        load_local_model()
        self.name = local_model_status()["model_id"] + "+vqa"

    def _generate(self, image: Image.Image, prompt: str, max_new_tokens: int = 8) -> str:
        import torch

        assert _LOCAL_MODEL is not None and _LOCAL_PROCESSOR is not None
        messages = [
            {
                "role": "user",
                "content": [{"type": "image"}, {"type": "text", "text": prompt}],
            }
        ]
        input_text = _LOCAL_PROCESSOR.apply_chat_template(messages, add_generation_prompt=True)
        inputs = _LOCAL_PROCESSOR(text=input_text, images=[image], return_tensors="pt")
        with torch.no_grad():
            generated = _LOCAL_MODEL.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                do_sample=False,
            )
        prompt_len = inputs["input_ids"].shape[1]
        return _LOCAL_PROCESSOR.batch_decode(generated[:, prompt_len:], skip_special_tokens=True)[0]

    def _ask(self, image: Image.Image, question: str) -> Optional[bool]:
        prompt = question.strip() + " Answer with one word: YES, NO, or UNSURE."
        raw = self._generate(image, prompt, max_new_tokens=6)
        return parse_tristate(raw)

    def observe(self, image: Image.Image, user_note: str = "", region_hint: str = "") -> Observations:
        image = resize_for_vision(image, max_side=640)
        obs = Observations(vision_notes="本地模型按短问答逐项观察，未覆盖字段保持无法判断。")
        if region_hint == "挂装":
            focus = "hanging"
        elif region_hint == "叠装":
            focus = "folded"
        else:
            focus = "auto"

        hanging = self._ask(image, "Are hanging clothes on a rail clearly visible in this photo?")
        folded = self._ask(image, "Are folded stacks of clothing on a table or shelf clearly visible?")
        mannequin = self._ask(image, "Is a mannequin clearly visible?")
        clutter = self._ask(image, "Are there trash, stains, cardboard boxes, or plastic restock bags in the sales area?")
        blocked = self._ask(image, "Do boxes or bags block the walkway or evacuation path?")

        obs.hanging.present = hanging
        obs.folded.present = folded
        obs.mannequin.present = mannequin
        obs.accessories.present = False if focus in ("hanging", "folded") else None
        if clutter is True:
            obs.cleanliness.no_clutter = False
        elif clutter is False:
            obs.cleanliness.no_clutter = True
        if blocked is True:
            obs.cleanliness.aisles_and_safety_clear = False
        elif blocked is False:
            obs.cleanliness.aisles_and_safety_clear = True
        obs.cleanliness.fixtures_stable = True if clutter is not None else None

        if hanging:
            empty = self._ask(image, "Is there a large cluster of empty hangers on the rail?")
            mixed = self._ask(image, "Are hangers mixed, for example black plastic together with silver metal?")
            if empty is True:
                obs.hanging.no_large_empty_hangers = False
            elif empty is False:
                obs.hanging.no_large_empty_hangers = True
            if mixed is True:
                obs.hanging.hanger_material_consistent = False
                obs.hanging.hanger_color_consistent = False
            elif mixed is False:
                obs.hanging.hanger_material_consistent = True
                obs.hanging.hanger_color_consistent = True

        if folded:
            messy = self._ask(image, "Are the folded stacks uneven, leaning, or messy?")
            overhang = self._ask(image, "Does any garment hang off the shelf edge or touch the floor?")
            if messy is True:
                obs.folded.fold_width_consistent = False
                obs.folded.front_edges_aligned = False
                obs.folded.stack_stable = False
            elif messy is False:
                obs.folded.fold_width_consistent = True
                obs.folded.front_edges_aligned = True
                obs.folded.stack_stable = True
            if overhang is True:
                obs.folded.not_overhanging_shelf = False
                obs.folded.not_touching_floor = False
            elif overhang is False:
                obs.folded.not_overhanging_shelf = True
                obs.folded.not_touching_floor = True

        if mannequin:
            complete = self._ask(image, "Does the mannequin wear both a top and a bottom?")
            obs.mannequin.complete_outfit = complete
            obs.mannequin.base_stable = True

        tags = self._ask(image, "Are price tags clearly visible next to the displayed products?")
        obs.price_tag.present = tags
        if tags is True:
            obs.price_tag.present_for_each_group = True
            readable = self._ask(image, "Can the price tag text be read clearly?")
            obs.price_tag.text_legible = readable
            obs.price_tag.upright_forward_unobstructed = True if readable is not False else None
        elif tags is False:
            obs.price_tag.present_for_each_group = False
            obs.price_tag.text_legible = None

        notes = []
        if user_note.strip():
            notes.append("门店说明：" + user_note.strip())
        if region_hint:
            notes.append("拍摄区域：" + region_hint)
        obs.vision_notes = "；".join(notes) or obs.vision_notes
        return obs


class VisionNotConfigured(RuntimeError):
    """Cloud deploy has no local VLM and no API key."""


def skip_local_vlm() -> bool:
    flag = os.environ.get("SKIP_LOCAL_VLM", "").strip().lower()
    if flag in {"1", "true", "yes", "on"}:
        return True
    return bool(os.environ.get("RENDER"))


def cloud_vision_configured() -> bool:
    return bool(
        (os.environ.get("VISION_API_KEY") or "").strip()
        or (os.environ.get("DEEPSEEK_API_KEY") or "").strip()
        or (os.environ.get("OPENAI_API_KEY") or "").strip()
    )


def configured_vision_model() -> Optional[str]:
    explicit = (
        (os.environ.get("VISION_MODEL") or "").strip()
        or (os.environ.get("OPENAI_MODEL") or "").strip()
    )
    if explicit:
        return explicit
    url = (os.environ.get("VISION_BASE_URL") or os.environ.get("OPENAI_BASE_URL") or "").lower()
    if (os.environ.get("DEEPSEEK_API_KEY") or "").strip() or "deepseek.com" in url:
        return DEEPSEEK_VISION_MODEL
    return None


def resolve_backend(
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    model: Optional[str] = None,
) -> VisionBackend:
    deepseek_env_key = (os.environ.get("DEEPSEEK_API_KEY") or "").strip()
    key = (
        api_key
        or os.environ.get("VISION_API_KEY")
        or deepseek_env_key
        or os.environ.get("OPENAI_API_KEY")
        or ""
    ).strip()
    url = (
        base_url
        or os.environ.get("VISION_BASE_URL")
        or os.environ.get("OPENAI_BASE_URL")
        or ""
    ).strip() or None
    explicit_model = (
        model
        or os.environ.get("VISION_MODEL")
        or os.environ.get("OPENAI_MODEL")
        or ""
    ).strip()
    using_deepseek = bool(
        (deepseek_env_key and key == deepseek_env_key)
        or (url and "deepseek.com" in url.lower())
        or explicit_model.startswith("deepseek-")
    )
    if using_deepseek:
        url = url or DEEPSEEK_BASE_URL
        model_name = explicit_model or DEEPSEEK_VISION_MODEL
    else:
        model_name = explicit_model or DEFAULT_CLOUD_MODEL
    if key:
        return OpenAICompatibleVision(key, url, model_name)
    if skip_local_vlm():
        raise VisionNotConfigured(
            "云端部署未配置 VISION_API_KEY。内置样例仍可查看；上传新照片请在页面填写 DeepSeek / 智谱等 OpenAI 兼容 Key，或在 Render 环境变量中设置。"
        )
    return LocalSmolVLM()
