#!/usr/bin/env bash
# One-shot deploy script. Intended to be run on the VPS (or by OpenClaw via SSH).
#
# Usage:
#   sudo bash scripts/deploy.sh
#
# Assumes the repo has been cloned to /opt/copy-trader.

set -euo pipefail
ROOT=/opt/copy-trader
cd "$ROOT"

echo "==> Installing system deps"
apt-get update -y
apt-get install -y python3 python3-venv python3-pip

echo "==> Creating virtualenv"
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

echo "==> Ensuring .env exists"
if [ ! -f .env ]; then
  cp .env.example .env
  echo "!! .env created from template — EDIT IT before starting services."
fi

echo "==> Installing systemd units"
install -m 0644 scripts/copytrader-scorer.service  /etc/systemd/system/
install -m 0644 scripts/copytrader-paper.service   /etc/systemd/system/
install -m 0644 scripts/copytrader-summary.service /etc/systemd/system/
install -m 0644 scripts/copytrader-summary.timer   /etc/systemd/system/
systemctl daemon-reload

echo "==> Enabling timer"
systemctl enable --now copytrader-summary.timer

echo
echo "Deploy complete. Next steps:"
echo "  1) Edit /opt/copy-trader/.env (Discord webhook etc.)"
echo "  2) Drop the research seed file: /opt/copy-trader/data/seed_wallets.json"
echo "     (or run:  .venv/bin/python -m scripts.import_seed /path/to/seed_wallets.json )"
echo "  3) systemctl enable --now copytrader-scorer copytrader-paper"
echo "  4) journalctl -u copytrader-paper -f"
