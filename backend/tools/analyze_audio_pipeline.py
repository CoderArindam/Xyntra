"""Developer Debug Tool — End-to-End Audio Capture & Pipeline Analysis (Phase 0X).

Usage:
    python tools/analyze_audio_pipeline.py [session_id_or_path]

If no session ID is provided, the script analyzes the latest meeting directory in storage/meeting/processed_audio.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Add backend root to sys.path
backend_root = Path(__file__).resolve().parents[1]
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from app.meeting.audio.verification import (
    analyze_speech_activity,
    calculate_audio_metrics,
)
from app.meeting.config import meeting_config


def find_target_directory(param: str | None) -> Path:
    base_dir = Path(meeting_config.PROCESSING_OUTPUT_DIR)
    if param:
        cand = Path(param)
        if cand.is_dir():
            return cand.resolve()
        cand_base = base_dir / param
        if cand_base.is_dir():
            return cand_base.resolve()

    if not base_dir.exists():
        print(f"Error: Base directory '{base_dir}' does not exist.")
        sys.exit(1)

    subdirs = [d for d in base_dir.iterdir() if d.is_dir()]
    if not subdirs:
        print(f"Error: No session directories found in '{base_dir}'.")
        sys.exit(1)

    latest = max(subdirs, key=lambda d: d.stat().st_mtime)
    return latest.resolve()


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze audio pipeline capture stages (Phase 0X)")
    parser.add_argument("session", nargs="?", help="Session ID or path to meeting directory")
    args = parser.parse_args()

    session_dir = find_target_directory(args.session)
    print(f"=" * 80)
    print(f"   AUDIO PIPELINE OBSERVABILITY REPORT — PHASE 0X")
    print(f"=" * 80)
    print(f"Target Directory: {session_dir}")

    # Files to inspect
    files_to_check = {
        "capture_raw.wav": session_dir / "capture_raw.wav",
        "recorded.webm": session_dir / "recorded.webm",
        "recorded_decoded.wav": session_dir / "recorded_decoded.wav",
        "deepgram_input.wav": session_dir / "deepgram_input.wav",
        "deepgram_input.webm": session_dir / "deepgram_input.webm",
    }

    print("\n[1] ARTIFACT FILE PRESENCE & SIZES:")
    print("-" * 80)
    for name, path in files_to_check.items():
        if path.exists():
            size_mb = path.stat().st_size / (1024 * 1024)
            print(f"  [FOUND]   {name:<22} : Present ({size_mb:.3f} MB)")
        else:
            print(f"  [MISSING] {name:<22} : Not found")

    print("\n[2] COMPARATIVE SIGNAL METRICS:")
    print("-" * 80)
    print(f"{'Artifact':<22} | {'Duration (s)':<12} | {'Sample Rate':<11} | {'Channels':<8} | {'RMS Energy':<12} | {'Peak Amp':<10}")
    print("-" * 80)

    for name in ["capture_raw.wav", "recorded_decoded.wav", "deepgram_input.wav"]:
        p = files_to_check[name]
        if p.exists():
            m = calculate_audio_metrics(p)
            print(f"{name:<22} | {m.get('duration', 0):<12.3f} | {m.get('sample_rate', 0):<11} | {m.get('channels', 0):<8} | {m.get('rms', 0):<12.6f} | {m.get('peak_amplitude', 0):<10.6f}")
        else:
            print(f"{name:<22} | {'N/A':<12} | {'N/A':<11} | {'N/A':<8} | {'N/A':<12} | {'N/A':<10}")

    print("\n[3] VOICE ACTIVITY & ENERGY ANALYSIS:")
    print("-" * 80)
    raw_wav = files_to_check["capture_raw.wav"]
    if raw_wav.exists():
        va = analyze_speech_activity(raw_wav)
        print(f"  Speech Duration     : {va.get('speech_duration_seconds')} s / {va.get('total_duration_seconds')} s")
        print(f"  Speech Ratio        : {va.get('speech_ratio') * 100:.2f}%")
        print(f"  Energy Variance     : {va.get('energy_variance')}")
        print(f"  Active Speech Count : {len(va.get('active_speech_windows', []))}")
        if va.get("warnings"):
            print("  Warnings:")
            for w in va["warnings"]:
                print(f"    - [WARNING] {w}")
    else:
        print("  Raw PCM WAV not available for speech activity analysis.")

    print("\n[4] DIAGNOSTIC JSON REPORTS:")
    print("-" * 80)
    json_reports = ["audio_capture_report.json", "audio_pipeline_timeline.json", "browser_launch_debug.json", "audio_capture_debug.json"]
    for jname in json_reports:
        jpath = session_dir / jname
        if jpath.exists():
            print(f"  [FOUND]   {jname} : Present")
            try:
                data = json.loads(jpath.read_text(encoding="utf-8"))
                if jname == "audio_capture_report.json":
                    warnings = data.get("warnings", [])
                    print(f"    - Display Surface : {data.get('display_surface')}")
                    print(f"    - Audio Tracks    : {data.get('audio_tracks')}")
                    print(f"    - Warnings Count  : {len(warnings)}")
                    for w in warnings:
                        print(f"      - [WARNING] {w}")
            except Exception as e:
                print(f"    (Error parsing {jname}: {e})")
        else:
            print(f"  [MISSING] {jname} : Not found")


    print("\n" + "=" * 80)
    print("   END OF ANALYSIS REPORT")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
