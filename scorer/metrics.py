"""Per-wallet performance metrics computed from Hyperliquid fill history.

Hyperliquid `userFills` schema (relevant fields):
  coin: str            e.g. "BTC", "ETH"
  px: str              fill price
  sz: str              fill size (positive number, with `side` indicating dir)
  side: "A" | "B"      A = sell (ask), B = buy (bid)
  time: int            ms epoch
  closedPnl: str       realized PnL on this fill (if closing)
  fee: str             fee paid (USDC)
  startPosition: str   position size before this fill
  dir: str             human label e.g. "Open Long", "Close Short"
  hash: str            tx hash

We compute:
  - realized PnL (sum closedPnl - sum fee)
  - trade count, distinct days traded
  - win rate (% of CLOSING fills with positive closedPnl)
  - avg holding time (rough — duration of position runs)
  - max drawdown of equity curve
  - rolling Sharpe (daily PnL series annualized)
  - composite score (0-100)
"""
from __future__ import annotations
from collections import defaultdict
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from statistics import mean, pstdev
from typing import Any

import math


@dataclass
class WalletMetrics:
    address: str
    alias: str | None
    lookback_days: int
    n_fills: int
    n_closing_fills: int
    distinct_days_traded: int
    realized_pnl_usd: float
    fees_paid_usd: float
    net_pnl_usd: float
    win_rate_pct: float
    avg_winner_usd: float
    avg_loser_usd: float
    profit_factor: float
    max_drawdown_usd: float
    max_drawdown_pct: float
    sharpe_annualized: float
    avg_hold_minutes: float
    asset_concentration: dict[str, float]  # coin -> % of volume
    primary_assets: list[str]
    last_fill_at: str | None
    composite_score: float

    def to_row(self) -> dict[str, Any]:
        return asdict(self)


def _f(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


def _bucket_day(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")


def _max_drawdown(equity: list[float]) -> tuple[float, float]:
    """Return (max_dd_usd, max_dd_pct) over an equity-curve list."""
    if not equity:
        return 0.0, 0.0
    peak = equity[0]
    max_dd = 0.0
    max_dd_pct = 0.0
    for v in equity:
        if v > peak:
            peak = v
        dd = peak - v
        if dd > max_dd:
            max_dd = dd
            max_dd_pct = (dd / peak * 100) if peak > 0 else 0.0
    return max_dd, max_dd_pct


def _sharpe(daily_pnl: list[float]) -> float:
    if len(daily_pnl) < 5:
        return 0.0
    mu = mean(daily_pnl)
    sd = pstdev(daily_pnl)
    if sd == 0:
        return 0.0
    return (mu / sd) * math.sqrt(365)


def compute(address: str, alias: str | None, fills: list[dict],
            lookback_days: int) -> WalletMetrics:
    if not fills:
        return WalletMetrics(
            address=address, alias=alias, lookback_days=lookback_days,
            n_fills=0, n_closing_fills=0, distinct_days_traded=0,
            realized_pnl_usd=0, fees_paid_usd=0, net_pnl_usd=0,
            win_rate_pct=0, avg_winner_usd=0, avg_loser_usd=0,
            profit_factor=0, max_drawdown_usd=0, max_drawdown_pct=0,
            sharpe_annualized=0, avg_hold_minutes=0,
            asset_concentration={}, primary_assets=[],
            last_fill_at=None, composite_score=0,
        )

    fills_sorted = sorted(fills, key=lambda x: int(x.get("time", 0)))

    closed_pnls: list[float] = []
    fees = 0.0
    realized = 0.0
    daily_pnl: dict[str, float] = defaultdict(float)
    vol_by_coin: dict[str, float] = defaultdict(float)
    days = set()

    # Track position open times per coin for rough hold-time estimate.
    last_open_time: dict[str, int] = {}
    hold_durations_min: list[float] = []

    for f in fills_sorted:
        t = int(f.get("time", 0))
        coin = f.get("coin", "?")
        px = _f(f.get("px"))
        sz = _f(f.get("sz"))
        fee = _f(f.get("fee"))
        cpnl = _f(f.get("closedPnl"))
        start_pos = _f(f.get("startPosition"))

        fees += fee
        realized += cpnl
        day = _bucket_day(t)
        days.add(day)
        daily_pnl[day] += cpnl - fee
        vol_by_coin[coin] += abs(sz * px)

        # Closing fill = startPosition != 0 (had position before)
        if abs(start_pos) > 1e-9:
            closed_pnls.append(cpnl)
            if coin in last_open_time:
                dur_min = (t - last_open_time[coin]) / 1000 / 60
                if dur_min > 0:
                    hold_durations_min.append(dur_min)
                # If closed fully, drop the timer
                # (rough heuristic — Hyperliquid doesn't always say "fully closed")
                last_open_time.pop(coin, None)
        else:
            last_open_time[coin] = t

    wins = [p for p in closed_pnls if p > 0]
    losses = [p for p in closed_pnls if p < 0]
    win_rate = (len(wins) / len(closed_pnls) * 100) if closed_pnls else 0.0
    avg_w = mean(wins) if wins else 0.0
    avg_l = mean(losses) if losses else 0.0
    pf = (sum(wins) / abs(sum(losses))) if losses else (float("inf") if wins else 0.0)

    # Equity curve from daily net PnL
    sorted_days = sorted(daily_pnl.keys())
    equity_curve: list[float] = []
    running = 0.0
    for d in sorted_days:
        running += daily_pnl[d]
        equity_curve.append(running)
    dd_usd, dd_pct = _max_drawdown(equity_curve)

    daily_series = [daily_pnl[d] for d in sorted_days]
    sharpe = _sharpe(daily_series)

    total_vol = sum(vol_by_coin.values()) or 1.0
    concentration = {c: round(v / total_vol * 100, 2)
                     for c, v in sorted(vol_by_coin.items(), key=lambda x: -x[1])}
    primary = list(concentration.keys())[:3]

    last_t = max(int(f.get("time", 0)) for f in fills_sorted)
    last_iso = datetime.fromtimestamp(last_t / 1000, tz=timezone.utc).isoformat()

    net = realized - fees

    # Composite score (0-100). Weighting reflects what actually matters for copyability:
    #   Sharpe 35, ProfitFactor 25, NetPnL-sign 15, drawdown penalty 15, recency 10
    score = 0.0
    score += max(0.0, min(35.0, sharpe * 12))             # Sharpe ~3 => 36 → capped
    pf_score = 0.0 if pf == 0 else min(25.0, math.log1p(pf) * 12)
    score += pf_score
    score += 15.0 if net > 0 else 0.0
    score -= min(15.0, dd_pct / 4)                         # 60% DD = -15
    score += 15.0
    days_since_last = (datetime.now(timezone.utc).timestamp() - last_t / 1000) / 86400
    if days_since_last > 7:
        score -= min(10.0, days_since_last - 7)
    score = max(0.0, min(100.0, score))

    avg_hold = mean(hold_durations_min) if hold_durations_min else 0.0

    return WalletMetrics(
        address=address, alias=alias, lookback_days=lookback_days,
        n_fills=len(fills_sorted), n_closing_fills=len(closed_pnls),
        distinct_days_traded=len(days),
        realized_pnl_usd=round(realized, 2),
        fees_paid_usd=round(fees, 2),
        net_pnl_usd=round(net, 2),
        win_rate_pct=round(win_rate, 2),
        avg_winner_usd=round(avg_w, 2),
        avg_loser_usd=round(avg_l, 2),
        profit_factor=round(pf, 2) if pf != float("inf") else 999.0,
        max_drawdown_usd=round(dd_usd, 2),
        max_drawdown_pct=round(dd_pct, 2),
        sharpe_annualized=round(sharpe, 2),
        avg_hold_minutes=round(avg_hold, 1),
        asset_concentration=concentration,
        primary_assets=primary,
        last_fill_at=last_iso,
        composite_score=round(score, 2),
    )
