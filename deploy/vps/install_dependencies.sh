#!/usr/bin/env bash
# ==============================================================================
# KAIO Meeting Bot — VPS Dependency Installer Script
# ==============================================================================
# Installs and configures system-level dependencies for running Playwright Chromium,
# FFmpeg, Xvfb virtual frame buffer, and PulseAudio/PipeWire virtual audio sink on Linux VPS.
# ==============================================================================

set -euo pipefail

echo "======================================================================"
echo " KAIO Meeting Bot — Linux VPS Dependency Installer"
echo "======================================================================"

# Check if script is executed as root or with sudo
if [ "$(id -u)" -ne 0 ]; then
    echo "[!] Error: This script must be run as root or using sudo." >&2
    exit 1
fi

echo "[1/5] Updating system package index..."
apt-get update -y

echo "[2/5] Installing core system tools, Xvfb, PulseAudio, and FFmpeg..."
apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    wget \
    gnupg \
    xvfb \
    x11-utils \
    pulseaudio \
    pulseaudio-utils \
    alsa-utils \
    ffmpeg \
    libasound2-plugins \
    procps

echo "[3/5] Installing Chromium browser and Playwright system dependencies..."
apt-get install -y --no-install-recommends \
    chromium-browser \
    libgbm1 \
    libnss3 \
    libatk-bridge2.0-0 \
    libgtk-3-0 \
    libasound2 \
    libxss1 \
    libxtst6 \
    x11-apps \
    fonts-liberation \
    libappindicator3-1 \
    libgdk-pixbuf2.0-0 \
    libnspr4 \
    xdg-utils \
    fonts-noto-color-emoji \
    fonts-ipafont-gothic \
    fonts-wqy-zenhei \
    fonts-thai-tlwg \
    fonts-kacst \
    fonts-freefont-ttf

echo "[4/5] Installing Python wheel & Playwright browser binaries..."
if command -v pip &> /dev/null; then
    pip install --upgrade pip setuptools wheel
    pip install playwright
    playwright install chromium --with-deps || true
else
    echo "[i] Python pip not detected system-wide. Please run 'playwright install chromium' within your Python virtual environment."
fi

echo "[5/5] Configuring PulseAudio daemon defaults for non-interactive VPS..."
mkdir -p /etc/pulse
if [ -f /etc/pulse/default.pa ]; then
    # Ensure module-null-sink auto-loading option is enabled if needed
    if ! grep -q "module-null-sink" /etc/pulse/default.pa; then
        echo "load-module module-null-sink sink_name=kaio_sink sink_properties=device.description=KAIO_Virtual_Sink" >> /etc/pulse/default.pa
    fi
fi

echo "======================================================================"
echo " SUCCESS: All KAIO Meeting Bot dependencies successfully installed!"
echo "======================================================================"
