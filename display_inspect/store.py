"""检查记录本地存储（SQLite + 图片目录）。"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from display_inspect.config import DATA_DIR, DB_PATH
from display_inspect.schemas import InspectionReport


def _connect() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS inspections (
            id TEXT PRIMARY KEY,
            store_id TEXT,
            store_name TEXT,
            created_at TEXT,
            overall TEXT,
            summary TEXT,
            report_json TEXT,
            image_count INTEGER
        )
        """
    )
    conn.commit()
    return conn


def image_dir(inspection_id: str) -> Path:
    path = DATA_DIR / inspection_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_images(inspection_id: str, images: list[tuple[str, bytes]]) -> list[str]:
    folder = image_dir(inspection_id)
    names: list[str] = []
    for i, (filename, data) in enumerate(images):
        ext = Path(filename).suffix.lower()
        if ext not in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
            ext = ".jpg"
        name = f"{i}{ext}"
        (folder / name).write_bytes(data)
        names.append(name)
    return names


def save_report(report: InspectionReport) -> None:
    conn = _connect()
    conn.execute(
        """
        INSERT OR REPLACE INTO inspections
        (id, store_id, store_name, created_at, overall, summary, report_json, image_count)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            report.inspection_id,
            report.store_id,
            report.store_name,
            report.created_at,
            report.overall,
            report.summary,
            json.dumps(report.to_public_dict(), ensure_ascii=False),
            report.image_count,
        ),
    )
    conn.commit()
    conn.close()


def list_reports(limit: int = 50) -> list[dict[str, Any]]:
    conn = _connect()
    rows = conn.execute(
        "SELECT id, store_id, store_name, created_at, overall, summary, image_count "
        "FROM inspections ORDER BY created_at DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_report(inspection_id: str) -> dict[str, Any] | None:
    conn = _connect()
    row = conn.execute(
        "SELECT report_json FROM inspections WHERE id = ?",
        (inspection_id,),
    ).fetchone()
    conn.close()
    if not row:
        return None
    return json.loads(row["report_json"])


def get_image_path(inspection_id: str, index: int) -> Path | None:
    folder = DATA_DIR / inspection_id
    if not folder.is_dir():
        return None
    files = sorted(p for p in folder.iterdir() if p.is_file())
    if index < 0 or index >= len(files):
        return None
    return files[index]
