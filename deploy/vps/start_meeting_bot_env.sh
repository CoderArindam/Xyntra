#!/usr/bin/env bash
# ==============================================================================
# KAIO Meeting Bot — VPS Startup & Audio Setup Script
# ==============================================================================
# Initializes Xvfb display server, starts PulseAudio/PipeWire daemon, creates
# virtual audio sink (kaio_sink), and sets default audio monitor source.
# ==============================================================================

set -euo pipefail

DISPLAY_NUM="${DISPLAY_NUM:-:99}"
SCREEN_RESOLUTION="${SCREEN_RESOLUTION:-1920x1080x24}"
SINK_NAME="${SINK_NAME:-kaio_sink}"
SINK_DESC="${SINK_DESC:-KAIO_Virtual_Audio_Sink}"

# Check if running under Windows / Git Bash
if [[ "${OSTYPE:-}" == "msys" || "${OSTYPE:-}" == "cygwin" || "${OSTYPE:-}" == "win32" ]]; then
    echo "======================================================================"
    echo "[!] NOTICE: Windows / Git Bash Environment Detected"
    echo "======================================================================"
    echo "  - The VPS environment script is designed for Linux VPS (Ubuntu/Debian)."
    echo "  - Xvfb display servers and PulseAudio null-sinks are NOT required on Windows."
    echo "  - On Windows local development, simply run the backend directly:"
    echo "      uvicorn app.main:app --port 8000"
    echo "======================================================================"
    exit 0
fi

# Helper function to check running process
is_process_running() {
    local pattern="$1"
    if command -v pgrep > /dev/null 2>&1; then
        pgrep -f "$pattern" > /dev/null 2>&1
    else
        ps -ef | grep -v grep | grep -q "$pattern"
    fi
}

echo "======================================================================"
echo " Starting KAIO Meeting Bot Environment"
echo "======================================================================"

# ------------------------------------------------------------------------------
# 1. Virtual Frame Buffer (Xvfb) Display Setup
# ------------------------------------------------------------------------------
echo "[1/4] Checking Xvfb Virtual Frame Buffer display ($DISPLAY_NUM)..."

if is_process_running "Xvfb $DISPLAY_NUM"; then
    echo "  [✓] Xvfb display $DISPLAY_NUM is already running."
else
    echo "  [+] Starting Xvfb on display $DISPLAY_NUM with resolution $SCREEN_RESOLUTION..."
    Xvfb "$DISPLAY_NUM" -screen 0 "$SCREEN_RESOLUTION" -ac +extension RANDR > /dev/null 2>&1 &
    sleep 1
    if is_process_running "Xvfb $DISPLAY_NUM"; then
        echo "  [✓] Xvfb display $DISPLAY_NUM initialized successfully."
    else
        echo "  [!] Error: Failed to start Xvfb display $DISPLAY_NUM." >&2
        exit 1
    fi
fi

export DISPLAY="$DISPLAY_NUM"

# ------------------------------------------------------------------------------
# 2. Audio Server (PulseAudio / PipeWire) Setup
# ------------------------------------------------------------------------------
echo "[2/4] Checking PulseAudio / PipeWire audio server..."

if command -v pactl &> /dev/null; then
    if ! pactl info > /dev/null 2>&1; then
        echo "  [+] Starting PulseAudio daemon..."
        pulseaudio --start --exit-idle-time=-1 || true
        sleep 1
    fi
    
    if pactl info > /dev/null 2>&1; then
        echo "  [✓] Audio server is active and responding."
    else
        echo "  [!] Warning: PulseAudio daemon could not be reached via pactl." >&2
    fi
else
    echo "  [!] Error: 'pactl' utility not found. Please run install_dependencies.sh first." >&2
    exit 1
fi

# ------------------------------------------------------------------------------
# 3. Virtual Audio Sink & Monitor Setup
# ------------------------------------------------------------------------------
echo "[3/4] Ensuring virtual audio sink '$SINK_NAME' is present..."

if pactl list sinks short | grep -q "$SINK_NAME"; then
    echo "  [✓] Virtual audio sink '$SINK_NAME' already exists."
else
    echo "  [+] Creating virtual audio sink '$SINK_NAME'..."
    MODULE_ID=$(pactl load-module module-null-sink sink_name="$SINK_NAME" sink_properties=device.description="$SINK_DESC")
    echo "  [✓] Virtual audio sink loaded (Module ID: $MODULE_ID)."
fi

# Set default sink so Chromium automatically routes browser tab audio output to kaio_sink
echo "  [+] Setting default PulseAudio sink to '$SINK_NAME'..."
pactl set-default-sink "$SINK_NAME" || true

# Set default source to kaio_sink.monitor so FFmpeg reads system audio cleanly
echo "  [+] Setting default PulseAudio source to '$SINK_NAME.monitor'..."
pactl set-default-source "$SINK_NAME.monitor" || true

# ------------------------------------------------------------------------------
# 4. Verify Audio Routing Readiness
# ------------------------------------------------------------------------------
echo "[4/4] Verifying browser audio capture pipeline readiness..."

DEFAULT_SINK=$(pactl info | grep "Default Sink" | cut -d':' -f2 | xargs || true)
DEFAULT_SOURCE=$(pactl info | grep "Default Source" | cut -d':' -f2 | xargs || true)

echo "  - Active DISPLAY:        $DISPLAY"
echo "  - Default Pulse Sink:    $DEFAULT_SINK"
echo "  - Default Pulse Source:  $DEFAULT_SOURCE"

export RECORDING_PULSE_SOURCE="$SINK_NAME.monitor"
export MEETING_HEADLESS=true

echo "======================================================================"
echo " SUCCESS: KAIO Meeting Bot environment is ready for recording!"
echo "======================================================================"
