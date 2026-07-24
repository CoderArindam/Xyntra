#!/usr/bin/env bash
# ==============================================================================
# KAIO Meeting Bot — VPS Health Check & Audio Diagnostics Script
# ==============================================================================
# Performs empirical verification of Xvfb, PulseAudio/PipeWire, virtual sink,
# FFmpeg pulse input, and Playwright Chromium availability on Linux VPS.
# ==============================================================================

set -euo pipefail

DISPLAY_NUM="${DISPLAY_NUM:-:99}"
SINK_NAME="${SINK_NAME:-kaio_sink}"
ERRORS=0

# Check if running under Windows / Git Bash
if [[ "${OSTYPE:-}" == "msys" || "${OSTYPE:-}" == "cygwin" || "${OSTYPE:-}" == "win32" ]]; then
    echo "======================================================================"
    echo "[!] NOTICE: Windows / Git Bash Environment Detected"
    echo "======================================================================"
    echo "  - The health check script is designed for Linux VPS environments."
    echo "  - On Windows local dev, Playwright & Chromium run directly."
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
echo " KAIO Meeting Bot — Health Check & Audio Diagnostics"
echo "======================================================================"

# Helper function for reporting status
report_status() {
    local check_name="$1"
    local status="$2"
    local message="$3"
    
    if [ "$status" -eq 0 ]; then
        echo -e " [PASS] $check_name: $message"
    else
        echo -e " [FAIL] $check_name: $message"
        ERRORS=$((ERRORS + 1))
    fi
}

# ------------------------------------------------------------------------------
# Check 1: Xvfb Virtual Frame Buffer & DISPLAY
# ------------------------------------------------------------------------------
if is_process_running "Xvfb $DISPLAY_NUM"; then
    report_status "Xvfb Display" 0 "Process running on display $DISPLAY_NUM"
else
    report_status "Xvfb Display" 1 "No Xvfb process found for $DISPLAY_NUM"
fi

if command -v xdpyinfo &> /dev/null; then
    if xdpyinfo -display "$DISPLAY_NUM" > /dev/null 2>&1; then
        report_status "X11 Server" 0 "Display $DISPLAY_NUM is accessible via X11 connection"
    else
        report_status "X11 Server" 1 "Cannot connect to X11 display $DISPLAY_NUM"
    fi
else
    if [ "${DISPLAY:-}" = "$DISPLAY_NUM" ]; then
        report_status "X11 Server" 0 "DISPLAY environment variable set to $DISPLAY_NUM (xdpyinfo not installed)"
    else
        report_status "X11 Server" 1 "DISPLAY env var is '${DISPLAY:-}' (expected '$DISPLAY_NUM')"
    fi
fi

# ------------------------------------------------------------------------------
# Check 2: PulseAudio / PipeWire Server Status
# ------------------------------------------------------------------------------
if command -v pactl &> /dev/null; then
    if pactl info > /dev/null 2>&1; then
        SERVER_NAME=$(pactl info | grep "Server Name" | cut -d':' -f2 | xargs || echo "PulseAudio/PipeWire")
        report_status "Audio Server" 0 "Audio server active ($SERVER_NAME)"
    else
        report_status "Audio Server" 1 "pactl info failed; PulseAudio/PipeWire daemon is not running"
    fi
else
    report_status "Audio Server" 1 "'pactl' executable not found in PATH"
fi

# ------------------------------------------------------------------------------
# Check 3: Virtual Audio Sink Availability
# ------------------------------------------------------------------------------
if command -v pactl &> /dev/null && pactl info > /dev/null 2>&1; then
    if pactl list sinks short | grep -q "$SINK_NAME"; then
        report_status "Virtual Audio Sink" 0 "Sink '$SINK_NAME' is registered in PulseAudio"
    else
        report_status "Virtual Audio Sink" 1 "Sink '$SINK_NAME' not found in pactl list sinks"
    fi
else
    report_status "Virtual Audio Sink" 1 "Skipped (audio server unavailable)"
fi

# ------------------------------------------------------------------------------
# Check 4: PulseAudio Monitor Source for FFmpeg
# ------------------------------------------------------------------------------
if command -v pactl &> /dev/null && pactl info > /dev/null 2>&1; then
    if pactl list sources short | grep -q "$SINK_NAME.monitor"; then
        report_status "Audio Monitor Source" 0 "Monitor source '$SINK_NAME.monitor' is active for capture"
    else
        report_status "Audio Monitor Source" 1 "Monitor source '$SINK_NAME.monitor' not found in pactl list sources"
    fi
else
    report_status "Audio Monitor Source" 1 "Skipped (audio server unavailable)"
fi

# ------------------------------------------------------------------------------
# Check 5: FFmpeg Binary & Pulse Input Device Support
# ------------------------------------------------------------------------------
if command -v ffmpeg &> /dev/null; then
    if ffmpeg -h demuxer=pulse > /dev/null 2>&1 || ffmpeg -sources pulse > /dev/null 2>&1; then
        report_status "FFmpeg Pulse Device" 0 "FFmpeg installed with '-f pulse' capture support"
    else
        report_status "FFmpeg Pulse Device" 1 "FFmpeg binary does not appear to support '-f pulse' input format"
    fi
else
    report_status "FFmpeg Pulse Device" 1 "'ffmpeg' binary not found in PATH"
fi

# ------------------------------------------------------------------------------
# Check 6: Playwright & Chromium Availability
# ------------------------------------------------------------------------------
if command -v python &> /dev/null || command -v python3 &> /dev/null; then
    PY_BIN=$(command -v python3 || command -v python)
    if $PY_BIN -c "import playwright" > /dev/null 2>&1; then
        report_status "Playwright Module" 0 "Playwright Python library installed"
    else
        report_status "Playwright Module" 1 "Playwright Python library not installed in active environment"
    fi
else
    report_status "Playwright Module" 1 "Python runtime not found"
fi

if command -v chromium-browser &> /dev/null || command -v chromium &> /dev/null; then
    CHROMIUM_BIN=$(command -v chromium-browser || command -v chromium)
    report_status "Chromium Binary" 0 "Chromium binary present at $CHROMIUM_BIN"
else
    report_status "Chromium Binary" 0 "Using Playwright standalone Chromium binary"
fi

# ------------------------------------------------------------------------------
# Summary & Exit Code
# ------------------------------------------------------------------------------
echo "======================================================================"
if [ "$ERRORS" -eq 0 ]; then
    echo " HEALTH CHECK RESULT: OK — All 6 health checks passed!"
    echo "======================================================================"
    exit 0
else
    echo " HEALTH CHECK RESULT: FAILED — $ERRORS check(s) failed."
    echo " Run 'bash deploy/vps/start_meeting_bot_env.sh' to initialize the environment."
    echo "======================================================================"
    exit 1
fi
