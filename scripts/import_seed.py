"""Import a seed_wallets.json (from research) into data/ and validate it."""
from __future__ import annotations
import json
import sys
from pathlib import Path

from common.config import SETTINGS


def main(src: str) -> None:
    src_p = Path(src)
    if not src_p.exists():
        print(f"ERROR: {src} not found", file=sys.stderr); sys.exit(1)
    data = json.loads(src_p.read_text())
    wallets = data.get("wallets") if isinstance(data, dict) else data
    if not isinstance(wallets, list) or not wallets:
        print("ERROR: no wallets array", file=sys.stderr); sys.exit(1)

    cleaned = []
    seen = set()
    for w in wallets:
        addr = (w.get("address") or "").lower().strip()
        if not addr.startswith("0x") or len(addr) != 42:
            print(f"skip invalid address: {w.get('address')}")
            continue
        if addr in seen:
            continue
        seen.add(addr)
        cleaned.append({**w, "address": addr})

    out = {"generated_at": data.get("generated_at"),
           "methodology": data.get("methodology"),
           "wallets": cleaned}
    dst = SETTINGS.data_dir / "seed_wallets.json"
    dst.write_text(json.dumps(out, indent=2))
    print(f"Imported {len(cleaned)} wallets → {dst}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "seed_wallets.json")
