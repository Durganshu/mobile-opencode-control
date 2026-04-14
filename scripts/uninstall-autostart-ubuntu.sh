#!/usr/bin/env bash
set -euo pipefail

if [[ "$EUID" -ne 0 ]]; then
  echo "Run this script with sudo:"
  echo "  sudo ./scripts/uninstall-autostart-ubuntu.sh"
  exit 1
fi

if ! command -v systemctl >/dev/null 2>&1; then
  echo "systemctl is required but not found."
  exit 1
fi

SERVICE_PREFIX="mobile-opencode-control"
SYSTEMD_DIR="/etc/systemd/system"

systemctl disable --now "${SERVICE_PREFIX}.target" >/dev/null 2>&1 || true
systemctl disable --now "${SERVICE_PREFIX}-frontend.service" >/dev/null 2>&1 || true
systemctl disable --now "${SERVICE_PREFIX}-backend.service" >/dev/null 2>&1 || true
systemctl disable --now "${SERVICE_PREFIX}-opencode.service" >/dev/null 2>&1 || true

rm -f "$SYSTEMD_DIR/${SERVICE_PREFIX}.target"
rm -f "$SYSTEMD_DIR/${SERVICE_PREFIX}-frontend.service"
rm -f "$SYSTEMD_DIR/${SERVICE_PREFIX}-backend.service"
rm -f "$SYSTEMD_DIR/${SERVICE_PREFIX}-opencode.service"

systemctl daemon-reload

echo "Removed autostart services for ${SERVICE_PREFIX}."
