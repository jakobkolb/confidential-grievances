#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="grievance-bot"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$PROJECT_DIR/.env"
UV_BIN="$HOME/.local/bin/uv"

if [ ! -f "$ENV_FILE" ]; then
    echo "Error: $ENV_FILE not found. Copy .env.example and fill in your values first."
    exit 1
fi

if [ ! -x "$UV_BIN" ]; then
    echo "Error: uv not found at $UV_BIN. Run scripts/setup.sh first."
    exit 1
fi

echo "Creating systemd service: $SERVICE_NAME"

sudo tee /etc/systemd/system/${SERVICE_NAME}.service > /dev/null <<EOF
[Unit]
Description=Grievance Mediation Telegram Bot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$PROJECT_DIR
EnvironmentFile=$ENV_FILE
ExecStart=$UV_BIN run python -m src.bot.app
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"
sudo systemctl start "$SERVICE_NAME"

echo "Service installed and started."
echo "  Status:  sudo systemctl status $SERVICE_NAME"
echo "  Logs:    sudo journalctl -u $SERVICE_NAME -f"
echo "  Stop:    sudo systemctl stop $SERVICE_NAME"
