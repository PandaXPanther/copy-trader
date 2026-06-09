"""Pretty-print the latest wallet scores from data/wallet_scores.json."""
from __future__ import annotations
import json
from tabulate import tabulate
from common.config import SETTINGS


def main() -> None:
    p = SETTINGS.data_dir / "wallet_scores.json"
    if not p.exists():
        print("No scores yet — run `python -m scorer.run`")
        return
    rows = json.loads(p.read_text())
    rows.sort(key=lambda r: r["composite_score"], reverse=True)
    table = [[
        i + 1,
        (r.get("alias") or r["address"][:10])[:18],
        f"{r['composite_score']:.1f}",
        f"${r['net_pnl_usd']:,.0f}",
        f"{r['sharpe_annualized']:.2f}",
        f"{r['max_drawdown_pct']:.1f}%",
        f"{r['win_rate_pct']:.0f}%",
        r["n_closing_fills"],
        ", ".join(r.get("primary_assets", [])[:3]),
    ] for i, r in enumerate(rows)]
    print(tabulate(table, headers=[
        "#", "alias", "score", "netPnL", "Sharpe", "maxDD", "win%", "trades", "assets",
    ]))


if __name__ == "__main__":
    main()
