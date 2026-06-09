"""Risk filters applied before each copy attempt."""
from __future__ import annotations
from dataclasses import dataclass
from common.config import SETTINGS
from .book import Book


@dataclass
class RiskDecision:
    allow: bool
    reason: str
    size_usd: float = 0.0
    leverage: float = 0.0


def evaluate_open(
    book: Book,
    *,
    coin: str,
    source_wallet: str,
    source_notional_usd: float,
    source_equity_usd: float,
    source_leverage: float,
    funding_apr_pct: float,
    marks: dict[str, float],
) -> RiskDecision:
    """Decide whether to open + how big.

    Sizing rule (proportional):
      pct_of_source_equity = source_notional / source_equity
      our_notional = min(
        pct_of_source_equity * our_equity,
        max_position_pct * our_equity,
      )
      capped by leverage and per-wallet exposure.
    """
    eq = book.equity_with_unrealized(marks)

    # Daily loss limit
    if book.today_pnl() <= -eq * SETTINGS.paper_daily_loss_limit_pct / 100:
        return RiskDecision(False, "daily_loss_limit_hit")

    # Funding filter
    if funding_apr_pct > SETTINGS.paper_max_funding_apr_pct:
        return RiskDecision(False, f"funding_too_high({funding_apr_pct:.0f}%)")

    if source_equity_usd <= 0:
        return RiskDecision(False, "source_equity_unknown")

    pct = source_notional_usd / source_equity_usd
    our_notional = pct * eq
    cap_notional = eq * SETTINGS.paper_max_position_pct / 100
    our_notional = min(our_notional, cap_notional)

    # Per-wallet cap (sum of notional of open positions sourced from this wallet)
    wallet_exposure = sum(
        p.notional_usd for p in book.positions.values()
        if p.source_wallet == source_wallet
    )
    wallet_cap = eq * SETTINGS.paper_per_wallet_cap_pct / 100
    remaining_wallet_capacity = max(0.0, wallet_cap - wallet_exposure)
    our_notional = min(our_notional, remaining_wallet_capacity)

    if our_notional < 10:  # too tiny to bother
        return RiskDecision(False, "size_below_threshold")

    lev = min(source_leverage, SETTINGS.paper_max_leverage)
    return RiskDecision(True, "ok", size_usd=our_notional, leverage=lev)
