from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

RULES_PATH = Path(__file__).resolve().parent / "rules.yaml"


@lru_cache(maxsize=1)
def load_rules() -> dict[str, Any]:
    with RULES_PATH.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError("rules.yaml 格式无效")
    return data


def iter_rules() -> list[dict[str, Any]]:
    catalog = load_rules()
    rows: list[dict[str, Any]] = []
    for category in catalog["categories"]:
        for rule in category["rules"]:
            rows.append(
                {
                    **rule,
                    "category_id": category["id"],
                    "category": category["name"],
                    "object_label": category.get("object_label", category["name"]),
                }
            )
    return rows


def rules_public_view() -> dict[str, Any]:
    catalog = load_rules()
    return {
        "source": catalog["source"],
        "severity_definition": catalog["severity_definition"],
        "photo_validity": catalog["photo_validity"],
        "categories": [
            {
                "id": c["id"],
                "name": c["name"],
                "rules": [
                    {
                        "id": r["id"],
                        "text": r["text"],
                        "severity": r["severity"],
                    }
                    for r in c["rules"]
                ],
            }
            for c in catalog["categories"]
        ],
    }
