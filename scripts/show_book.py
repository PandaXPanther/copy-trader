"""Pretty-print current paper book state."""
from __future__ import annotations
import asyncio
from tabulate import tabulate
from common.hl_client import HLClient
from paper.book import Book


async def main() -> None:
    book = Book.load_or_new()
    client = HLClient()
    try:
        mids = await client.all_mids()
    finally:
        await client.close()
    marks = {k: float(v) for k, v in mids.items()}

    print(f"Starting equity:  ${book.starting_equity:,.2f}")
    print(f"Realized PnL:     ${book.realized_pnl:+,.2f}")
    print(f"Fees paid:        ${book.fees_paid:,.2f}")
    print(f"Equity (cash):    ${book.equity:,.2f}")
    print(f"Equity (mark):    ${book.equity_with_unrealized(marks):,.2f}")
    print(f"Open positions:   {len(book.positions)}\n")
    rows = []
    for k, p in book.positions.items():
        mp = marks.get(p.coin, p.entry_px)
        u = p.unrealized(mp)
        rows.append([k, p.side, p.coin, f"{p.size:.4f}",
                     f"${p.entry_px:.4f}", f"${mp:.4f}",
                     f"${p.notional_usd:,.0f}", f"${u:+,.2f}"])
    if rows:
        print(tabulate(rows, headers=[
            "key", "side", "coin", "size", "entry", "mark", "notional", "uPnL"]))


if __name__ == "__main__":
    asyncio.run(main())
