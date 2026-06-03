#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/opt/worldpanel-qc"
APP_USER="worldpanelqc"

if [[ $EUID -ne 0 ]]; then
  echo "Run this script with sudo."
  exit 1
fi

apt-get update
apt-get install -y \
  python3 \
  python3-venv \
  python3-pip \
  libreoffice \
  poppler-utils \
  unzip \
  curl

if ! id "$APP_USER" >/dev/null 2>&1; then
  useradd --system --create-home --shell /usr/sbin/nologin "$APP_USER"
fi

mkdir -p "$APP_DIR"
cp -a "$PWD"/. "$APP_DIR"/
python3 -m venv "$APP_DIR/.venv"
"$APP_DIR/.venv/bin/pip" install --upgrade pip
"$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/requirements.txt"

mkdir -p "$APP_DIR/local_data/uploads" "$APP_DIR/local_data/exports"
chown -R "$APP_USER:$APP_USER" "$APP_DIR"

if [[ ! -f /etc/worldpanel-qc.env ]]; then
  cp "$APP_DIR/deploy/cloud/worldpanel-qc.env.example" /etc/worldpanel-qc.env
  chmod 600 /etc/worldpanel-qc.env
  echo "Created /etc/worldpanel-qc.env. Edit it before starting the service."
fi

cp "$APP_DIR/deploy/cloud/worldpanel-qc.service" /etc/systemd/system/worldpanel-qc.service
systemctl daemon-reload
echo "Install complete. Edit /etc/worldpanel-qc.env, then run:"
echo "  sudo systemctl enable --now worldpanel-qc"
