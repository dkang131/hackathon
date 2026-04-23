"""Menu persistence — load/save drinks from JSON."""

import json
import os
from pathlib import Path

from .models import Drink

# Use workspace root as base
_BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_MENU_PATH = _BASE_DIR / "data" / "menu.json"


def load_menu(path: Path | str = DEFAULT_MENU_PATH) -> list[Drink]:
    """Load drinks from JSON file. Falls back to empty list if file missing."""
    path = Path(path)
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return [Drink(**item) for item in raw]


def save_menu(drinks: list[Drink], path: Path | str = DEFAULT_MENU_PATH) -> None:
    """Save drinks to JSON file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = [
        {
            "name": d.name,
            "description": d.description,
            "moods": d.moods,
            "caffeine_level": d.caffeine_level,
            "temperature": d.temperature,
            "price": d.price,
        }
        for d in drinks
    ]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
