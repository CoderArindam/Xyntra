# 14 — Linux VPS Meeting Bot Deployment Guide

## 1. Executive Summary & Architecture Overview

The **KAIO Meeting Bot** automates live meeting joining, browser audio capture, and post-meeting transcription and task extraction. On a headless **Linux VPS** (Ubuntu 22.04 / 24.04 LTS or Debian 12), physical sound cards and displays are absent.

To enable full browser audio recording without physical hardware, KAIO uses a headless audio and virtual frame buffer pipeline:

```
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│                                     Linux VPS Server                                     │
│                                                                                          │
│  ┌───────────────────────┐         ┌───────────────────────┐                             │
│  │   Xvfb Display :99    │ ──────► │ Playwright Chromium   │                             │
│  │ Virtual Frame Buffer  │         │ Google Meet Session   │                             │
│  └───────────────────────┘         └──────────┬────────────┘                             │
│                                               │                                          │
│                                               │ Audio Playback                           │
│                                               ▼                                          │
│                                    ┌─────────────────────┐                               │
│                                    │ PulseAudio Daemon   │                               │
│                                    │ (Virtual Audio)     │                               │
│                                    └──────────┬──────────┘                               │
│                                               │                                          │
│                                               │ kaio_sink                                │
│                                               ▼                                          │
│                                    ┌─────────────────────┐                               │
│                                    │ Virtual Null-Sink   │                               │
│                                    │ kaio_sink.monitor   │                               │
│                                    └──────────┬──────────┘                               │
│                                               │                                          │
│                                               │ Audio Capture                            │
│                                               ▼                                          │
│                                    ┌─────────────────────┐                               │
│                                    │ FFmpeg Process      │ ──► recording.webm            │
│                                    │ (-f pulse)          │                               │
│                                    └─────────────────────┘                               │
└──────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Dependency Specification

Every dependency required for running KAIO Meeting Bot on a Linux VPS is cataloged below:

| Package / Tool | Component Category | Purpose | System Package / Install Command |
|---|---|---|---|
| **Chromium** | Browser Runtime | Headless web browser instance managed by Playwright to navigate Google Meet rooms | `apt-get install chromium-browser` or `playwright install chromium` |
| **Playwright** | Automation SDK | Python automation library controlling browser lifecycle and DOM interactions | `pip install playwright` |
| **FFmpeg** | Audio Capture | CLI audio engine capturing PulseAudio stream via `-f pulse` to Opus/WebM | `apt-get install ffmpeg` |
| **PulseAudio / PipeWire** | Audio Subsystem | Virtual sound server hosting virtual playback sinks and audio monitors | `apt-get install pulseaudio pulseaudio-utils` |
| **Xvfb** | Display Server | X Virtual Frame Buffer providing headless X11 display environment (`:99`) | `apt-get install xvfb x11-utils` |
| **Alsa & Plugins** | Sound Utilities | Audio loopback & ALSA bridge plugins | `apt-get install alsa-utils libasound2-plugins` |
| **Fonts Suite** | Text Rendering | Multi-language fonts for Google Meet UI rendering (Emoji, CJK, Thai, Arabic) | `apt-get install fonts-liberation fonts-noto-color-emoji` |

---

## 3. Virtual Audio Sink Architecture (`kaio_sink`)

On a Linux VPS, PulseAudio must expose a virtual sound device that acts as a speaker for Chromium and a microphone/source for FFmpeg:

1. **Virtual Sink Creation**:
   ```bash
   pactl load-module module-null-sink sink_name=kaio_sink sink_properties=device.description=KAIO_Virtual_Sink
   ```
2. **Default Output Sink Routing**:
   ```bash
   pactl set-default-sink kaio_sink
   ```
   *Chromium automatically routes tab audio playback to `kaio_sink`.*

3. **Audio Monitor Source Routing**:
   ```bash
   pactl set-default-source kaio_sink.monitor
   ```
   *FFmpeg opens `kaio_sink.monitor` via `-f pulse -i kaio_sink.monitor` to capture meeting audio.*

---

## 4. Deployment Scripts Suite (`deploy/vps/`)

KAIO provides automated shell scripts located in [deploy/vps/](file:///d:/kanban-project/deploy/vps/):

### 4.1 Dependency Installation (`install_dependencies.sh`)
Run once during VPS setup as `root` or `sudo`:
```bash
sudo bash deploy/vps/install_dependencies.sh
```

### 4.2 Startup Script (`start_meeting_bot_env.sh`)
Prepares Xvfb, PulseAudio daemon, creates `kaio_sink` if missing, sets audio defaults, and exports environment variables:
```bash
bash deploy/vps/start_meeting_bot_env.sh
```

### 4.3 Shutdown Script (`stop_meeting_bot_env.sh`)
Unloads virtual audio sink modules, stops Xvfb, and cleans temporary display locks:
```bash
bash deploy/vps/stop_meeting_bot_env.sh
```

### 4.4 Automated Health Check (`health_check.sh`)
Verifies all 6 system requirements before accepting meeting jobs:
```bash
bash deploy/vps/health_check.sh
```

---

## 5. Health Check Diagnostics Matrix

`health_check.sh` executes 6 empirical checks:

```
======================================================================
 KAIO Meeting Bot — Health Check & Audio Diagnostics
======================================================================
 [PASS] Xvfb Display: Process running on display :99
 [PASS] X11 Server: Display :99 is accessible via X11 connection
 [PASS] Audio Server: Audio server active (PulseAudio (on PipeWire))
 [PASS] Virtual Audio Sink: Sink 'kaio_sink' is registered in PulseAudio
 [PASS] Audio Monitor Source: Monitor source 'kaio_sink.monitor' is active for capture
 [PASS] FFmpeg Pulse Device: FFmpeg installed with '-f pulse' capture support
 [PASS] Playwright Module: Playwright Python library installed
 [PASS] Chromium Binary: Chromium binary present at /usr/bin/chromium-browser
======================================================================
 HEALTH CHECK RESULT: OK — All 6 health checks passed!
======================================================================
```

---

## 6. Systemd Daemon Management

To manage KAIO Meeting Bot automatically on Linux VPS startup:

1. Copy systemd unit file:
   ```bash
   sudo cp deploy/vps/kaio-meeting-bot.service /etc/systemd/system/
   ```
2. Reload systemd daemon:
   ```bash
   sudo systemctl daemon-reload
   ```
3. Enable and start service:
   ```bash
   sudo systemctl enable --now kaio-meeting-bot
   ```
4. Verify service status:
   ```bash
   sudo systemctl status kaio-meeting-bot
   ```

---

## 7. Troubleshooting & Common Issues

### Issue 1: `FFmpeg process exited with code 1 (PulseAudio connection failed)`
- **Root Cause**: PulseAudio daemon is not running or `PULSE_SERVER` environment variable is misconfigured.
- **Fix**: Run `bash deploy/vps/start_meeting_bot_env.sh` to restart PulseAudio and recreate `kaio_sink`.

### Issue 2: `Playwright error: Target page, context or browser has been closed (X11 connection refused)`
- **Root Cause**: Xvfb display server is down or `DISPLAY` environment variable is not exported.
- **Fix**: Verify `DISPLAY=:99` is exported and Xvfb process is active (`pgrep Xvfb`).

### Issue 3: Empty WebM Recording File (0 bytes)
- **Root Cause**: Chromium tab audio played into a different PulseAudio sink instead of `kaio_sink`.
- **Fix**: Run `pactl set-default-sink kaio_sink` and `pactl set-default-source kaio_sink.monitor`.
