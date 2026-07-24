#!/usr/bin/env bash
# ==============================================================================
# KAIO Meeting Bot — VPS Teardown & Shutdown Script
# ==============================================================================
# Gracefully unloads virtual audio sinks, stops PulseAudio daemon, terminates
# Xvfb virtual display server, and cleans lock files.
# ==============================================================================

set -euo pipefail

DISPLAY_NUM="${DISPLAY_NUM:-:99}"
SINK_NAME="${SINK_NAME:-kaio_sink}"

# Check if running under Windows / Git Bash
if [[ "${OSTYPE:-}" == "msys" || "${OSTYPE:-}" == "cygwin" || "${OSTYPE:-}" == "win32" ]]; then
    echo "[!] Notice: Running on Windows / Git Bash. Teardown script is for Linux VPS environments."
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
echo " Stopping KAIO Meeting Bot Environment"
echo "======================================================================"

# ------------------------------------------------------------------------------
# 1. Unload Virtual Audio Sink Module
# ------------------------------------------------------------------------------
echo "[1/3] Unloading virtual audio sink '$SINK_NAME'..."

if command -v pactl &> /dev/null && pactl info > /dev/null 2>&1; then
    MODULE_IDS=$(pactl list modules short | grep "module-null-sink" | grep "$SINK_NAME" | cut -f1 || true)
    if [ -n "$MODULE_IDS" ]; then
        for MOD_ID in $MODULE_IDS; do
            pactl unload-module "$MOD_ID" || true
            echo "  [✓] Unloaded PulseAudio module ID: $MOD_ID"
        done
    else
        echo "  [i] No active virtual sink module found matching '$SINK_NAME'."
    fi
else
    echo "  [i] PulseAudio not running or pactl unavailable."
fi

# ------------------------------------------------------------------------------
# 2. Terminate Xvfb Display Server
# ------------------------------------------------------------------------------
echo "[2/3] Terminating Xvfb display server ($DISPLAY_NUM)..."

if is_process_running "Xvfb $DISPLAY_NUM"; then
    if command -v pkill > /dev/null 2>&1; then
        pkill -f "Xvfb $DISPLAY_NUM" || true
    fi
    sleep 1
    echo "  [✓] Xvfb display server stopped."
else
    echo "  [i] Xvfb display server ($DISPLAY_NUM) was not running."
fi

# ------------------------------------------------------------------------------
# 3. Cleanup Temporary Display Locks & IPC Sockets
# ------------------------------------------------------------------------------
echo "[3/3] Cleaning up temporary locks and display sockets..."

DISP_NO=$(echo "$DISPLAY_NUM" | tr -d ':')
rm -f "/tmp/.X${DISP_NO}-lock"
rm -f "/tmp/.X11-unix/X${DISP_NO}"

echo "======================================================================"
echo " SUCCESS: KAIO Meeting Bot environment stopped cleanly!"
echo "======================================================================"
