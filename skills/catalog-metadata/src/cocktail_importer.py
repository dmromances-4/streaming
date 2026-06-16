"""Importación de datos de cócteles desde YAML."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from config import settings
from db.repository import CatalogRepository
from skill_telemetry import log


async def import_cocktails_dir(
    repo: CatalogRepository,
    cocktails_dir: str | None = None,
) -> dict[str, int]:
    path = Path(cocktails_dir or settings.cocktails_dir)
    if not path.is_dir():
        log.warning("cocktails_dir_missing", path=str(path))
        return {"imported": 0, "skipped": 0}

    imported = 0
    skipped = 0

    for yaml_file in sorted(path.glob("*.yaml")):
        data = yaml.safe_load(yaml_file.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            skipped += 1
            continue

        title_id = data.get("title_id")
        cocktails = data.get("cocktails", [])
        if not title_id or not cocktails:
            skipped += 1
            continue

        title = await repo.get_title(title_id)
        if not title:
            log.warning("cocktail_title_missing", title_id=title_id)
            skipped += 1
            continue

        for entry in cocktails:
            if not isinstance(entry, dict) or "id" not in entry:
                continue
            await repo.upsert_cocktail(
                {
                    "id": entry["id"],
                    "title_id": title_id,
                    "name": entry.get("name", entry["id"]),
                    "ingredients": [i.lower() for i in entry.get("ingredients", [])],
                    "recipe": entry.get("recipe", []),
                    "timestamp_seconds": entry.get("timestamp_seconds"),
                    "scene": entry.get("scene"),
                }
            )
            imported += 1

    log.info("cocktails_imported", imported=imported, skipped=skipped)
    return {"imported": imported, "skipped": skipped}
