#!/bin/bash
# StockPulse Setup Script
# Run this once to set up the environment

set -e

echo "========================================"
echo "  StockPulse - Setup"
echo "========================================"
echo ""

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "[1/5] Creating virtual environment..."
    python -m venv venv
else
    echo "[1/5] Virtual environment already exists."
fi

# Activate virtual environment
echo "[2/5] Activating virtual environment..."
if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
    source venv/Scripts/activate
else
    source venv/bin/activate
fi

# Install dependencies
echo "[3/5] Installing dependencies..."
pip install -r requirements.txt --quiet

# Copy .env.example to .env if it doesn't exist
if [ ! -f ".env" ]; then
    echo "[4/5] Creating .env from .env.example..."
    cp .env.example .env
else
    echo "[4/5] .env already exists, skipping."
fi

# Create necessary directories
echo "[5/5] Creating directories..."
mkdir -p data logs

echo ""
echo "========================================"
echo "  Setup Complete!"
echo "========================================"
echo ""
echo "  To start StockPulse:"
echo "    python run.py"
echo ""
echo "  Optional: Configure WhatsApp notifications"
echo "  ─────────────────────────────────────────"
echo "  1. Send 'I allow callmebot to send me messages'"
echo "     to +34 644 52 74 88 on WhatsApp"
echo "  2. You'll receive your API key instantly"
echo "  3. Edit .env and set:"
echo "     WHATSAPP_PHONE=+32xxxxxxxxx"
echo "     CALLMEBOT_API_KEY=your_key_here"
echo "  4. Set notifications.whatsapp.enabled: true in config.yaml"
echo ""
