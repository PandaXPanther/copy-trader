"""Once-a-day Discord summary of paper book performance."""
from __future__ import annotations
import asyncio
from datetime import datetime, timezone
from common.logging_setup import setup
from common.discord import send as discord_send, embed, COLOR_BLUE
from common.hl_client import HLClient
from .book import Book


async def main() -> None:
    setup("summary")
    book = Book.load_or_new()
    client = HLClient()
    try:
        mids = await client.all_mids()
    finally:
        await client.close()
    marks = {k: float(v) for k, v in mids.items()}
    eq_now = book.equity_with_unrealized(marks)
    ret_pct = ((eq_now - book.starting_equity) / book.starting_equity * 100) if book.starting_equity else 0
    open_lines = [
        f"{p.side} {p.coin} ${p.notional_usd:,.0f} (uPnL ${p.unrealized(marks.get(p.coin, p.entry_px)):+,.0f})"
        for p in book.positions.values()
    ] or ["(no open positions)"]
    fields = [
        {"name": "Starting equity", "value": f"${book.starting_equity:,.0f}", "inline": True},
        {"name": "Equity now", "value": f"${eq_now:,.2f}", "inline": True},
        {"name": "Return", "value": f"{ret_pct:+.2f}%", "inline": True},
        {"name": "Realized PnL", "value": f"${book.realized_pnl:+,.2f}", "inline": True},
        {"name": "Fees paid", "value": f"${book.fees_paid:,.2f}", "inline": True},
        {"name": "Today PnL", "value": f"${book.today_pnl():+,.2f}", "inline": True},
        {"name": f"Open positions ({len(book.positions)})", "value": "\n".join(open_lines)[:1000]},
    ]
    await discord_send(embeds=[embed(
        f"📊 Paper book — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%MZ')}",
        "", color=COLOR_BLUE, fields=fields,
    )])


if __name__ == "__main__":
    asyncio.run(main())
