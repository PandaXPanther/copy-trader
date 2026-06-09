"""Read/write the watchlist of wallets + their scores."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from .config import SETTINGS


SEED_FILE = SETTINGS.data_dir / "seed_wallets.json"
SCORES_FILE = SETTINGS.data_dir / "wallet_scores.json"
ACTIVE_FILE = SETTINGS.data_dir / "active_wallets.json"


def load_seed() -> list[dict[str, Any]]:
    if not SEED_FILE.exists():
        return []
    data = json.loads(SEED_FILE.read_text())
    return data.get("wallets", []) if isinstance(data, dict) else data


def save_scores(scores: list[dict[str, Any]]) -> None:
    SCORES_FILE.write_text(json.dumps(scores, indent=2, default=str))


def load_scores() -> list[dict[str, Any]]:
    if not SCORES_FILE.exists():
        return []
    return json.loads(SCORES_FILE.read_text())


def save_active(addresses: list[str]) -> None:
    ACTIVE_FILE.write_text(json.dumps({"addresses": addresses}, indent=2))


def load_active() -> list[str]:
    if not ACTIVE_FILE.exists():
        return [w["address"] for w in load_seed()]
    return json.loads(ACTIVE_FILE.read_text()).get("addresses", [])
