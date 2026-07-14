"""JavaScript audio capture script injected into the Playwright page.

This script captures meeting audio (all participants) from the browser tab
using the Web Audio API + MediaRecorder. It runs entirely inside the browser
context and communicates back to Python via Playwright's expose_function bridge.

Usage (from Python):
    await page.expose_function("_kaioRecordingChunk", on_chunk_callback)
    await page.evaluate(CAPTURE_SCRIPT)
    await page.evaluate("window._kaioStartRecording()")
    # ... meeting runs ...
    await page.evaluate("window._kaioStopRecording()")

The script MUST be evaluated AFTER expose_function is registered.
"""

CAPTURE_SCRIPT: str = """
(function () {
    'use strict';

    // Guard: prevent double-injection
    if (window.__kaioRecorderInstalled) return;
    window.__kaioRecorderInstalled = true;

    let mediaRecorder = null;
    let audioContext = null;
    let sourceNode = null;
    let destNode = null;
    let stream = null;

    // ------------------------------------------------------------------ //
    // Internal helpers                                                     //
    // ------------------------------------------------------------------ //

    function arrayBufferToBase64(buffer) {
        let binary = '';
        const bytes = new Uint8Array(buffer);
        for (let i = 0; i < bytes.byteLength; i++) {
            binary += String.fromCharCode(bytes[i]);
        }
        return window.btoa(binary);
    }

    function sendChunk(blob) {
        blob.arrayBuffer().then(function (buf) {
            const b64 = arrayBufferToBase64(buf);
            if (typeof window._kaioRecordingChunk === 'function') {
                window._kaioRecordingChunk(b64);
            }
        }).catch(function (err) {
            console.error('[KAIO] Failed to send chunk:', err);
        });
    }

    // ------------------------------------------------------------------ //
    // Public API                                                           //
    // ------------------------------------------------------------------ //

    window._kaioStartRecording = async function (mimeType, timesliceMs) {
        mimeType = mimeType || 'audio/webm;codecs=opus';
        timesliceMs = timesliceMs || 1000;

        try {
            // Capture the tab's audio output — all participants, no mic
            // getDisplayMedia requires video: true, even if we only want audio
            stream = await navigator.mediaDevices.getDisplayMedia({
                video: true,
                audio: {
                    echoCancellation: false,
                    noiseSuppression: false,
                    sampleRate: 48000,
                    channelCount: 2,
                }
            });

            // Stop the video track immediately to save CPU/memory
            stream.getVideoTracks().forEach(function(track) {
                track.stop();
            });

            // Wire through AudioContext so we can add future processing
            audioContext = new AudioContext({ sampleRate: 48000 });
            sourceNode = audioContext.createMediaStreamSource(stream);
            destNode = audioContext.createMediaStreamDestination();
            sourceNode.connect(destNode);

            // Prefer opus/webm for low-overhead streaming; fall back if unavailable
            const selectedMime = MediaRecorder.isTypeSupported(mimeType)
                ? mimeType
                : 'audio/webm';

            mediaRecorder = new MediaRecorder(destNode.stream, {
                mimeType: selectedMime,
                audioBitsPerSecond: 128000,
            });

            mediaRecorder.ondataavailable = function (e) {
                if (e.data && e.data.size > 0) {
                    sendChunk(e.data);
                }
            };

            mediaRecorder.onerror = function (e) {
                console.error('[KAIO] MediaRecorder error:', e.error);
            };

            mediaRecorder.start(timesliceMs);
            console.log('[KAIO] Recording started, mime:', selectedMime);
            return { ok: true, mimeType: selectedMime };

        } catch (err) {
            console.error('[KAIO] Failed to start recording:', err);
            return { ok: false, error: err.toString() };
        }
    };

    window._kaioStopRecording = function () {
        return new Promise(function (resolve) {
            if (!mediaRecorder || mediaRecorder.state === 'inactive') {
                resolve({ ok: false, error: 'Recorder not active' });
                return;
            }

            mediaRecorder.onstop = function () {
                // Teardown
                if (sourceNode) { try { sourceNode.disconnect(); } catch (_) {} }
                if (audioContext) { try { audioContext.close(); } catch (_) {} }
                if (stream) {
                    stream.getTracks().forEach(function (t) { t.stop(); });
                }
                mediaRecorder = null;
                audioContext = null;
                sourceNode = null;
                destNode = null;
                stream = null;
                console.log('[KAIO] Recording stopped');
                resolve({ ok: true });
            };

            mediaRecorder.stop();
        });
    };

    window._kaioRecordingStatus = function () {
        if (!mediaRecorder) return 'inactive';
        return mediaRecorder.state;
    };

    console.log('[KAIO] Audio capture script installed');
})();
"""
