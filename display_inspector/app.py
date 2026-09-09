from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from display_inspector.inspector import inspect_images
from display_inspector.rules import rules_public_view
from display_inspector.vision import load_local_model, local_model_status

ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"
SAMPLES = ROOT / "samples"

SAMPLE_META = {
    "hanging": {
        "id": "hanging",
        "title": "挂装样例（空架 / 色序混乱）",
        "filename": "sample_hanging_messy.png",
        "hint": "挂装",
        "note": "自测样例：挂装杆中段大面积空衣架，品类与颜色混排。",
    },
    "folded": {
        "id": "folded",
        "title": "叠装与清洁安全样例",
        "filename": "sample_folded_safety.png",
        "hint": "全景",
        "note": "自测样例：叠装不齐、商品探出、纸箱与补货袋占通道。",
    },
    "blurry": {
        "id": "blurry",
        "title": "模糊过暗样例",
        "filename": "sample_blurry_dark.png",
        "hint": "全景",
        "note": "自测样例：照片模糊且过暗，应整单无法判断。",
    },
}

app = FastAPI(title="服装门店陈列检查助手", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/assets", StaticFiles(directory=STATIC), name="assets")
app.mount("/samples", StaticFiles(directory=SAMPLES), name="samples")


@app.on_event("startup")
def _startup() -> None:
    from display_inspector.vision import skip_local_vlm

    has_cloud = bool(os.environ.get("VISION_API_KEY") or os.environ.get("OPENAI_API_KEY"))
    if not has_cloud and not skip_local_vlm():
        threading.Thread(target=_warmup_local, daemon=True).start()


def _warmup_local() -> None:
    try:
        load_local_model()
    except Exception:
        pass


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")


@app.get("/api/health")
def health() -> dict:
    from display_inspector.vision import skip_local_vlm

    has_cloud = bool(os.environ.get("VISION_API_KEY") or os.environ.get("OPENAI_API_KEY"))
    return {
        "ok": True,
        "name": "服装门店陈列检查助手",
        "cloud_vision_configured": has_cloud,
        "skip_local_vlm": skip_local_vlm(),
        "local_vlm": local_model_status(),
    }


@app.get("/api/rules")
def rules() -> dict:
    return rules_public_view()


@app.get("/api/samples")
def list_samples() -> dict:
    items = []
    for meta in SAMPLE_META.values():
        path = SAMPLES / meta["filename"]
        items.append({**meta, "available": path.exists(), "url": f"/samples/{meta['filename']}"})
    return {"samples": items}


def _vision_from_headers(
    x_vision_api_key: Optional[str],
    x_vision_base_url: Optional[str],
    x_vision_model: Optional[str],
) -> tuple[Optional[str], Optional[str], Optional[str]]:
    return (
        (x_vision_api_key or "").strip() or None,
        (x_vision_base_url or "").strip() or None,
        (x_vision_model or "").strip() or None,
    )


@app.post("/api/inspect")
async def inspect(
    files: list[UploadFile] = File(...),
    note: str = Form(""),
    region: str = Form("全景"),
    vision_api_key: str = Form(""),
    vision_base_url: str = Form(""),
    vision_model: str = Form(""),
    x_vision_api_key: Optional[str] = Header(default=None),
    x_vision_base_url: Optional[str] = Header(default=None),
    x_vision_model: Optional[str] = Header(default=None),
):
    if not files:
        raise HTTPException(400, "请至少上传一张门店照片")
    payload: list[tuple[str, bytes]] = []
    for item in files:
        content = await item.read()
        if not content:
            continue
        if len(content) > 12 * 1024 * 1024:
            raise HTTPException(400, f"{item.filename} 超过 12MB 限制")
        payload.append((item.filename or "upload.jpg", content))
    if not payload:
        raise HTTPException(400, "上传文件为空")
    key, url, model = _vision_from_headers(x_vision_api_key, x_vision_base_url, x_vision_model)
    key = vision_api_key.strip() or key
    url = vision_base_url.strip() or url
    model = vision_model.strip() or model
    try:
        report = inspect_images(
            payload,
            user_note=note,
            region_hint=region,
            api_key=key,
            base_url=url,
            model=model,
        )
    except Exception as exc:  # noqa: BLE001
        return JSONResponse(
            status_code=500,
            content={
                "error": "检查失败",
                "detail": str(exc),
                "hint": "可在页面中填写 OpenAI 兼容视觉接口（如智谱 GLM-4V），或等待本地视觉模型加载完成。",
            },
        )
    return report.model_dump()


@app.post("/api/inspect-sample/{sample_id}")
async def inspect_sample(
    sample_id: str,
    live: bool = False,
    x_vision_api_key: Optional[str] = Header(default=None),
    x_vision_base_url: Optional[str] = Header(default=None),
    x_vision_model: Optional[str] = Header(default=None),
):
    meta = SAMPLE_META.get(sample_id)
    if not meta:
        raise HTTPException(404, "未知样例")
    path = SAMPLES / meta["filename"]
    if not path.exists():
        raise HTTPException(404, "样例文件不存在")
    cache = SAMPLES / f"selftest_{sample_id}.json"
    if cache.exists() and not live:
        data = json.loads(cache.read_text(encoding="utf-8"))
        data["sample"] = meta
        data["from_selftest_cache"] = True
        return data
    key, url, model = _vision_from_headers(x_vision_api_key, x_vision_base_url, x_vision_model)
    try:
        report = inspect_images(
            [(meta["filename"], path.read_bytes())],
            user_note=meta["note"],
            region_hint=meta["hint"],
            api_key=key,
            base_url=url,
            model=model,
        )
    except Exception as exc:  # noqa: BLE001
        return JSONResponse(status_code=500, content={"error": "检查失败", "detail": str(exc)})
    data = report.model_dump()
    data["sample"] = meta
    data["from_selftest_cache"] = False
    return data
