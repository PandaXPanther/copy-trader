"""Centralized config loader. Reads .env and exposes typed settings."""
from __future__ import annotations
import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / ".env")


def _f(key: str, default: float) -> float:
    raw = os.getenv(key)
    return float(raw) if raw not in (None, "") else default


def _i(key: str, default: int) -> int:
    raw = os.getenv(key)
    return int(raw) if raw not in (None, "") else default


def _s(key: str, default: str) -> str:
    raw = os.getenv(key)
    return raw if raw not in (None, "") else default


@dataclass(frozen=True)
class Settings:
    discord_webhook: str
    hl_api_base: str
    hl_ws_url: str

    paper_starting_equity_usd: float
    paper_max_position_pct: float
    paper_daily_loss_limit_pct: float
    paper_max_leverage: float
    paper_max_funding_apr_pct: float
    paper_per_wallet_cap_pct: float

    scorer_lookback_days: int
    scorer_min_trades: int
    scorer_refresh_minutes: int

    log_level: str
    log_dir: Path
    data_dir: Path


def load() -> Settings:
    s = Settings(
        discord_webhook=_s("DISCORD_WEBHOOK_URL", ""),
        hl_api_base=_s("HL_API_BASE", "https://api.hyperliquid.xyz"),
        hl_ws_url=_s("HL_WS_URL", "wss://api.hyperliquid.xyz/ws"),
        paper_starting_equity_usd=_f("PAPER_STARTING_EQUITY_USD", 10000),
        paper_max_position_pct=_f("PAPER_MAX_POSITION_PCT", 10),
        paper_daily_loss_limit_pct=_f("PAPER_DAILY_LOSS_LIMIT_PCT", 5),
        paper_max_leverage=_f("PAPER_MAX_LEVERAGE", 10),
        paper_max_funding_apr_pct=_f("PAPER_MAX_FUNDING_APR_PCT", 200),
        paper_per_wallet_cap_pct=_f("PAPER_PER_WALLET_CAP_PCT", 25),
        scorer_lookback_days=_i("SCORER_LOOKBACK_DAYS", 90),
        scorer_min_trades=_i("SCORER_MIN_TRADES", 20),
        scorer_refresh_minutes=_i("SCORER_REFRESH_MINUTES", 360),
        log_level=_s("LOG_LEVEL", "INFO"),
        log_dir=Path(_s("LOG_DIR", str(_PROJECT_ROOT / "logs"))),
        data_dir=Path(_s("DATA_DIR", str(_PROJECT_ROOT / "data"))),
    )
    s.log_dir.mkdir(parents=True, exist_ok=True)
    s.data_dir.mkdir(parents=True, exist_ok=True)
    return s


SETTINGS = load()
