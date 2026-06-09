"""In-memory paper portfolio.

Tracks open positions, equity, realized + unrealized PnL.
Persists state to data/paper_state.json after every update.
"""
from __future__ import annotations
import json
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from common.config import SETTINGS


STATE_FILE: Path = SETTINGS.data_dir / "paper_state.json"
FILLS_LOG: Path = SETTINGS.data_dir / "paper_fills.jsonl"


@dataclass
class Position:
    coin: str
    source_wallet: str
    side: str           # "LONG" or "SHORT"
    size: float         # units (always positive)
    entry_px: float
    leverage: float
    opened_at: str
    notional_usd: float

    def unrealized(self, mark_px: float) -> float:
        if self.side == "LONG":
            return (mark_px - self.entry_px) * self.size
        return (self.entry_px - mark_px) * self.size


@dataclass
class Book:
    starting_equity: float
    realized_pnl: float = 0.0
    fees_paid: float = 0.0
    positions: dict[str, Position] = field(default_factory=dict)  # key = f"{wallet}:{coin}"
    daily_pnl: dict[str, float] = field(default_factory=lambda: defaultdict(float))

    @property
    def equity(self) -> float:
        return self.starting_equity + self.realized_pnl - self.fees_paid

    def equity_with_unrealized(self, marks: dict[str, float]) -> float:
        u = sum(p.unrealized(marks.get(p.coin, p.entry_px)) for p in self.positions.values())
        return self.equity + u

    def today_pnl(self) -> float:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return self.daily_pnl.get(today, 0.0)

    def to_dict(self) -> dict[str, Any]:
        return {
            "starting_equity": self.starting_equity,
            "realized_pnl": self.realized_pnl,
            "fees_paid": self.fees_paid,
            "positions": {k: asdict(p) for k, p in self.positions.items()},
            "daily_pnl": dict(self.daily_pnl),
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Book":
        b = cls(starting_equity=d.get("starting_equity", SETTINGS.paper_starting_equity_usd))
        b.realized_pnl = d.get("realized_pnl", 0.0)
        b.fees_paid = d.get("fees_paid", 0.0)
        b.positions = {k: Position(**v) for k, v in d.get("positions", {}).items()}
        b.daily_pnl = defaultdict(float, d.get("daily_pnl", {}))
        return b

    def save(self) -> None:
        STATE_FILE.write_text(json.dumps(self.to_dict(), indent=2, default=str))

    @classmethod
    def load_or_new(cls) -> "Book":
        if STATE_FILE.exists():
            return cls.from_dict(json.loads(STATE_FILE.read_text()))
        return cls(starting_equity=SETTINGS.paper_starting_equity_usd)


def log_fill(record: dict) -> None:
    record = {**record, "logged_at": datetime.now(timezone.utc).isoformat()}
    with FILLS_LOG.open("a") as f:
        f.write(json.dumps(record, default=str) + "\n")
