"""DeepSeek 视觉模型与存储路径配置。密钥只从环境变量或 .env 读取，禁止写入代码。"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "").strip()
DEEPSEEK_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/")
DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-flash")

DATA_DIR = Path(os.environ.get("INSPECT_DATA_DIR", str(PROJECT_ROOT / "data" / "inspections")))
DB_PATH = Path(os.environ.get("INSPECT_DB_PATH", str(DATA_DIR / "inspections.db")))

MAX_IMAGES = int(os.environ.get("INSPECT_MAX_IMAGES", "8"))
MAX_IMAGE_BYTES = int(os.environ.get("INSPECT_MAX_IMAGE_BYTES", str(12 * 1024 * 1024)))
VISION_MAX_SIDE = int(os.environ.get("INSPECT_VISION_MAX_SIDE", "1600"))
VISION_TIMEOUT = float(os.environ.get("INSPECT_VISION_TIMEOUT", "180"))


def llm_configured() -> bool:
    return bool(DEEPSEEK_API_KEY)
