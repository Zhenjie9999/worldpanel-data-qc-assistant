#!/usr/bin/env bash
set -euo pipefail

PORT="${1:-8877}"

if ! command -v cloudflared >/dev/null 2>&1; then
  echo "cloudflared is not installed. Install it from Cloudflare first."
  exit 1
fi

cloudflared tunnel --url "http://127.0.0.1:${PORT}"
