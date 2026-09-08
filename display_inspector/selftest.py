#!/usr/bin/env python3
"""Run bundled samples and write self-test JSON."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent))

from display_inspector.inspector import inspect_images  # noqa: E402

SAMPLES = ROOT / "samples"


def run_one(sample_id: str, filename: str, hint: str, note: str) -> dict:
    path = SAMPLES / filename
    report = inspect_images(
        [(filename, path.read_bytes())],
        user_note=note,
        region_hint=hint,
    )
    data = report.model_dump()
    out = SAMPLES / f"selftest_{sample_id}.json"
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"{sample_id}: {report.overall_status} "
        f"issues={len(report.issues)} undetermined={len(report.undetermined_items)} "
        f"model={report.model_used}"
    )
    return data


def main() -> None:
    only = sys.argv[1] if len(sys.argv) > 1 else "all"
    jobs = {
        "blurry": (
            "sample_blurry_dark.png",
            "全景",
            "自测：模糊过暗照片",
        ),
        "hanging": (
            "sample_hanging_messy.png",
            "挂装",
            "自测：挂装空架与衣架混用",
        ),
        "folded": (
            "sample_folded_safety.png",
            "全景",
            "自测：叠装与通道杂物",
        ),
    }
    targets = jobs if only == "all" else {only: jobs[only]}
    for sample_id, args in targets.items():
        run_one(sample_id, *args)


if __name__ == "__main__":
    main()
