"""Audio Verification and Observability Helper Module (Phase 0X).

Provides signal processing, WAV creation, metrics calculation, waveform/spectrogram
generation, speech activity analysis, and automated report generation.
"""

from __future__ import annotations

import json
import math
import struct
import wave
from pathlib import Path
from typing import Any, Dict, List, Tuple

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend for server environments
import matplotlib.pyplot as plt
import numpy as np
from scipy.io import wavfile
from scipy.signal import spectrogram

from app.meeting.logger import get_logger

log = get_logger("audio.verification")


def write_pcm16_wav(
    file_path: Path | str,
    pcm_bytes: bytes,
    sample_rate: int = 48000,
    channels: int = 2,
) -> Path:
    """Write raw 16-bit signed PCM byte data into an uncompressed WAV file."""
    path = Path(file_path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)

    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)  # 16-bit = 2 bytes
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_bytes)

    log.info("verification.wav_created", path=str(path), size_bytes=len(pcm_bytes))
    return path


def calculate_audio_metrics(wav_path: Path | str) -> Dict[str, Any]:
    """Calculate mono/stereo, sample rate, duration, RMS, and peak amplitude for a WAV file."""
    path = Path(wav_path).resolve()
    if not path.exists() or path.stat().st_size == 0:
        return {
            "exists": False,
            "duration": 0.0,
            "sample_rate": 0,
            "channels": 0,
            "rms": 0.0,
            "peak_amplitude": 0.0,
            "num_samples": 0,
        }

    try:
        sample_rate, data = wavfile.read(str(path))
        if data.size == 0:
            return {
                "exists": True,
                "duration": 0.0,
                "sample_rate": sample_rate,
                "channels": 1 if data.ndim == 1 else data.shape[1],
                "rms": 0.0,
                "peak_amplitude": 0.0,
                "num_samples": 0,
            }

        channels = 1 if data.ndim == 1 else data.shape[1]
        num_frames = data.shape[0]
        duration = num_frames / float(sample_rate) if sample_rate > 0 else 0.0

        # Convert to float [-1.0, 1.0] for RMS calculation
        if data.dtype == np.int16:
            norm_data = data.astype(np.float32) / 32768.0
        elif data.dtype == np.int32:
            norm_data = data.astype(np.float32) / 2147483648.0
        elif data.dtype == np.uint8:
            norm_data = (data.astype(np.float32) - 128.0) / 128.0
        else:
            norm_data = data.astype(np.float32)

        peak = float(np.max(np.abs(norm_data)))
        rms = float(np.sqrt(np.mean(norm_data ** 2)))

        return {
            "exists": True,
            "duration": round(duration, 3),
            "sample_rate": int(sample_rate),
            "channels": int(channels),
            "rms": round(rms, 6),
            "peak_amplitude": round(peak, 6),
            "num_samples": int(num_frames),
        }
    except Exception as exc:
        log.error("verification.calculate_metrics_failed", path=str(path), error=str(exc))
        return {
            "exists": True,
            "error": str(exc),
            "duration": 0.0,
            "sample_rate": 0,
            "channels": 0,
            "rms": 0.0,
            "peak_amplitude": 0.0,
            "num_samples": 0,
        }


def generate_waveform_plot(wav_path: Path | str, output_image_path: Path | str, title: str) -> Path:
    """Generate and save waveform plot (PNG) for a WAV file."""
    path = Path(wav_path).resolve()
    out_path = Path(output_image_path).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(10, 4), dpi=100)

    try:
        if path.exists() and path.stat().st_size > 44:
            sample_rate, data = wavfile.read(str(path))
            if data.ndim > 1:
                data = data[:, 0]  # Take first channel for waveform visualization

            times = np.linspace(0, len(data) / sample_rate, num=len(data))
            ax.plot(times, data, color="#1a73e8", alpha=0.8, linewidth=0.5)
            ax.set_xlabel("Time (seconds)")
            ax.set_ylabel("Amplitude")
            ax.set_title(title)
            ax.grid(True, linestyle="--", alpha=0.5)
        else:
            ax.text(0.5, 0.5, "Empty or Missing Audio File", ha="center", va="center")
    except Exception as exc:
        ax.text(0.5, 0.5, f"Error reading audio: {exc}", ha="center", va="center")

    plt.tight_layout()
    fig.savefig(str(out_path))
    plt.close(fig)
    log.info("verification.waveform_saved", path=str(out_path))
    return out_path


def generate_spectrogram_plot(wav_path: Path | str, output_image_path: Path | str, title: str) -> Path:
    """Generate and save spectrogram plot (PNG) for a WAV file."""
    path = Path(wav_path).resolve()
    out_path = Path(output_image_path).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(10, 4), dpi=100)

    try:
        if path.exists() and path.stat().st_size > 44:
            sample_rate, data = wavfile.read(str(path))
            if data.ndim > 1:
                data = data[:, 0]

            frequencies, times, Sxx = spectrogram(data, sample_rate, nperseg=1024)
            # Log scale for power spectrogram
            Sxx_log = 10 * np.log10(Sxx + 1e-10)
            im = ax.pcolormesh(times, frequencies, Sxx_log, shading="gouraud", cmap="viridis")
            fig.colorbar(im, ax=ax, label="dB")
            ax.set_ylabel("Frequency (Hz)")
            ax.set_xlabel("Time (seconds)")
            ax.set_title(title)
        else:
            ax.text(0.5, 0.5, "Empty or Missing Audio File", ha="center", va="center")
    except Exception as exc:
        ax.text(0.5, 0.5, f"Error rendering spectrogram: {exc}", ha="center", va="center")

    plt.tight_layout()
    fig.savefig(str(out_path))
    plt.close(fig)
    log.info("verification.spectrogram_saved", path=str(out_path))
    return out_path


def analyze_speech_activity(
    wav_path: Path | str,
    energy_threshold: float = 0.005,
    frame_ms: int = 30,
) -> Dict[str, Any]:
    """Perform deterministic voice activity analysis on a WAV file.

    Returns active speech windows, silence windows, speech ratio, and energy variance.
    """
    path = Path(wav_path).resolve()
    if not path.exists() or path.stat().st_size <= 44:
        return {
            "active_speech_windows": [],
            "silence_windows": [],
            "speech_duration_seconds": 0.0,
            "total_duration_seconds": 0.0,
            "speech_ratio": 0.0,
            "energy_variance": 0.0,
            "warnings": ["WAV file missing or empty"],
        }

    try:
        sample_rate, data = wavfile.read(str(path))
        if data.ndim > 1:
            data = data[:, 0]

        if data.dtype == np.int16:
            norm = data.astype(np.float32) / 32768.0
        else:
            norm = data.astype(np.float32)

        frame_samples = int(sample_rate * (frame_ms / 1000.0))
        if frame_samples <= 0:
            frame_samples = 1440

        num_frames = len(norm) // frame_samples
        frame_energies = []

        for i in range(num_frames):
            frame = norm[i * frame_samples : (i + 1) * frame_samples]
            rms = float(np.sqrt(np.mean(frame ** 2)))
            frame_energies.append(rms)

        frame_energies = np.array(frame_energies)
        active_mask = frame_energies > energy_threshold

        active_windows = []
        silence_windows = []

        current_active = False
        start_t = 0.0

        for i, is_active in enumerate(active_mask):
            t = i * (frame_ms / 1000.0)
            if is_active and not current_active:
                current_active = True
                start_t = t
            elif not is_active and current_active:
                current_active = False
                active_windows.append({"start": round(start_t, 3), "end": round(t, 3)})

        if current_active:
            active_windows.append({"start": round(start_t, 3), "end": round(num_frames * (frame_ms / 1000.0), 3)})

        total_duration = len(norm) / float(sample_rate)
        speech_duration = sum(w["end"] - w["start"] for w in active_windows)
        speech_ratio = speech_duration / total_duration if total_duration > 0 else 0.0
        energy_variance = float(np.var(frame_energies)) if len(frame_energies) > 0 else 0.0

        warnings = []
        if speech_ratio < 0.05:
            warnings.append("Low speech energy detected in audio recording")
        if energy_variance < 1e-6:
            warnings.append("Flat line or near-silent audio signal")

        return {
            "active_speech_windows": active_windows,
            "silence_windows": silence_windows,
            "speech_duration_seconds": round(speech_duration, 3),
            "total_duration_seconds": round(total_duration, 3),
            "speech_ratio": round(speech_ratio, 4),
            "energy_variance": round(energy_variance, 8),
            "warnings": warnings,
        }
    except Exception as exc:
        log.error("verification.speech_activity_failed", path=str(path), error=str(exc))
        return {
            "active_speech_windows": [],
            "silence_windows": [],
            "speech_duration_seconds": 0.0,
            "total_duration_seconds": 0.0,
            "speech_ratio": 0.0,
            "energy_variance": 0.0,
            "warnings": [f"Analysis error: {exc}"],
        }
