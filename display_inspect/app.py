"""门店陈列合规检查 API。"""
from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from display_inspect.agent import DisplayInspectionAgent
from display_inspect.config import MAX_IMAGE_BYTES, MAX_IMAGES, llm_configured, DEEPSEEK_MODEL
from display_inspect.rules import public_rules_payload
from display_inspect import store as inspect_store

logger = logging.getLogger("display_inspect")
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="门店陈列合规检查 Agent", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ALLOWED_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "image/gif",
}
ALLOWED_SUFFIX = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


@app.get("/health")
def health():
    return {"status": "ok", "service": "display-inspect"}


@app.get("/api/inspect/status")
def inspect_status():
    return {
        "llm_configured": llm_configured(),
        "model": DEEPSEEK_MODEL if llm_configured() else "",
        "max_images": MAX_IMAGES,
    }


@app.get("/api/inspect/rules")
def inspect_rules():
    return public_rules_payload()


@app.post("/api/inspect")
async def create_inspection(
    files: list[UploadFile] = File(...),
    store_id: str = Form(""),
    store_name: str = Form(""),
    note: str = Form(""),
):
    if not files:
        raise HTTPException(status_code=400, detail="请上传至少一张门店照片")
    if len(files) > MAX_IMAGES:
        raise HTTPException(status_code=400, detail=f"最多上传 {MAX_IMAGES} 张照片")

    images: list[tuple[str, bytes]] = []
    for f in files:
        name = f.filename or "photo.jpg"
        suffix = Path(name).suffix.lower()
        content_type = (f.content_type or "").lower()
        if content_type not in ALLOWED_TYPES and suffix not in ALLOWED_SUFFIX:
            raise HTTPException(status_code=400, detail=f"不支持的文件类型：{name}")
        data = await f.read()
        if not data:
            raise HTTPException(status_code=400, detail=f"空文件：{name}")
        if len(data) > MAX_IMAGE_BYTES:
            raise HTTPException(status_code=400, detail=f"{name} 超过大小限制")
        images.append((name, data))

    try:
        report = DisplayInspectionAgent().run(
            images,
            store_id=store_id.strip(),
            store_name=store_name.strip(),
            extra=note.strip(),
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except Exception as e:
        logger.exception("inspection failed")
        raise HTTPException(status_code=502, detail=f"检查失败：{e}") from e

    inspect_store.save_images(report.inspection_id, images)
    inspect_store.save_report(report)
    return report.to_public_dict()


@app.get("/api/inspect/history")
def inspect_history(limit: int = 50):
    return {"items": inspect_store.list_reports(limit=min(limit, 200))}


@app.get("/api/inspect/{inspection_id}")
def inspect_detail(inspection_id: str):
    report = inspect_store.get_report(inspection_id)
    if not report:
        raise HTTPException(status_code=404, detail="记录不存在")
    return report


@app.get("/api/inspect/{inspection_id}/image/{index}")
def inspect_image(inspection_id: str, index: int):
    path = inspect_store.get_image_path(inspection_id, index)
    if not path:
        raise HTTPException(status_code=404, detail="图片不存在")
    return FileResponse(path)


_FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"
_FRONTEND_INDEX = _FRONTEND_DIST / "index.html"

if (_FRONTEND_DIST / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=_FRONTEND_DIST / "assets"), name="assets")


@app.get("/")
def serve_index():
    if _FRONTEND_INDEX.is_file():
        return FileResponse(_FRONTEND_INDEX)
    return {
        "service": "display-inspect",
        "hint": "前端未构建。运行 cd frontend && npm run build 后重启，或开发时用 npm run dev（5173）。",
    }


@app.get("/{full_path:path}")
def serve_spa(full_path: str):
    if full_path.startswith("api/") or full_path == "health":
        raise HTTPException(status_code=404, detail="Not Found")
    if _FRONTEND_INDEX.is_file():
        return FileResponse(_FRONTEND_INDEX)
    raise HTTPException(status_code=404, detail="frontend not built")
