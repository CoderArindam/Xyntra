"""JavaScript audio capture script injected into the Playwright page.

This script captures meeting audio (all participants) from the browser tab
using the Web Audio API + MediaRecorder + ScriptProcessor PCM dump.
It runs entirely inside the browser context and communicates back to Python
via Playwright's expose_function bridge.

Usage (from Python):
    await page.expose_function("_kaioRecordingChunk", on_chunk_callback)
    await page.expose_function("_kaioRawPcmChunk", on_raw_pcm_callback)
    await page.evaluate(CAPTURE_SCRIPT)
    await page.evaluate("window._kaioStartRecording()")
    # ... meeting runs ...
    await page.evaluate("window._kaioStopRecording()")

The script MUST be evaluated AFTER expose_function callbacks are registered.
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
    let scriptNode = null;
    let dummyGain = null;
    let stream = null;

    window._kaioTimelineEvents = [];

    function recordTimelineEvent(name, details) {
        const evt = {
            event: name,
            timestamp_iso: new Date().toISOString(),
            timestamp_epoch_ms: Date.now(),
            details: details || {}
        };
        window._kaioTimelineEvents.push(evt);
        console.log('[KAIO Timeline]', name, evt);
    }

    function arrayBufferToBase64(buffer) {
        let binary = '';
        const bytes = new Uint8Array(buffer);
        const len = bytes.byteLength;
        for (let i = 0; i < len; i++) {
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
            console.error('[KAIO] Failed to send webm chunk:', err);
        });
    }

    function serializeTrack(track) {
        if (!track) return null;
        let capabilities = {};
        let constraints = {};
        let settings = {};
        try { if (typeof track.getCapabilities === 'function') capabilities = track.getCapabilities() || {}; } catch (_) {}
        try { if (typeof track.getConstraints === 'function') constraints = track.getConstraints() || {}; } catch (_) {}
        try { if (typeof track.getSettings === 'function') settings = track.getSettings() || {}; } catch (_) {}

        return {
            id: track.id || '',
            label: track.label || '',
            kind: track.kind || '',
            enabled: track.enabled !== undefined ? track.enabled : true,
            muted: track.muted !== undefined ? track.muted : false,
            readyState: track.readyState || '',
            settings: settings,
            constraints: constraints,
            capabilities: capabilities
        };
    }

    // ------------------------------------------------------------------ //
    // Public API                                                           //
    // ------------------------------------------------------------------ //

    window._kaioStartRecording = async function (mimeType, timesliceMs) {
        mimeType = mimeType || 'audio/webm;codecs=opus';
        timesliceMs = timesliceMs || 1000;

        try {
            recordTimelineEvent('getDisplayMedia_called', { mimeType: mimeType, timesliceMs: timesliceMs });

            // Capture the tab's audio output — all participants, no mic
            // getDisplayMedia requires video: true, even if we only want audio
            stream = await navigator.mediaDevices.getDisplayMedia({
                video: { displaySurface: "browser" },
                audio: {
                    echoCancellation: false,
                    noiseSuppression: false,
                    sampleRate: 48000,
                    channelCount: 2,
                },
                preferCurrentTab: true
            });

            recordTimelineEvent('stream_received', {
                total_tracks: stream.getTracks().length,
                audio_track_count: stream.getAudioTracks().length,
                video_track_count: stream.getVideoTracks().length
            });

            const allTracks = stream.getTracks().map(serializeTrack);
            const audioTracks = stream.getAudioTracks().map(serializeTrack);
            const videoTracks = stream.getVideoTracks().map(serializeTrack);

            const mainAudioTrack = stream.getAudioTracks()[0];
            const mainVideoTrack = stream.getVideoTracks()[0];

            const displaySurface = mainVideoTrack && mainVideoTrack.getSettings ? mainVideoTrack.getSettings().displaySurface : null;
            const logicalSurface = mainVideoTrack && mainVideoTrack.getSettings ? mainVideoTrack.getSettings().logicalSurface : null;
            const cursor = mainVideoTrack && mainVideoTrack.getSettings ? mainVideoTrack.getSettings().cursor : null;
            const deviceId = mainAudioTrack && mainAudioTrack.getSettings ? mainAudioTrack.getSettings().deviceId : null;
            const groupId = mainAudioTrack && mainAudioTrack.getSettings ? mainAudioTrack.getSettings().groupId : null;

            console.log('[KAIO] Video Tracks:', videoTracks);
            console.log('[KAIO] Audio Tracks:', audioTracks);

            // Stop video track immediately to save CPU/memory
            stream.getVideoTracks().forEach(function(track) {
                track.stop();
            });

            // Wire through AudioContext for verification and raw PCM capture
            audioContext = new AudioContext({ sampleRate: 48000 });
            recordTimelineEvent('audiocontext_created', { sampleRate: audioContext.sampleRate, state: audioContext.state });

            sourceNode = audioContext.createMediaStreamSource(stream);
            destNode = audioContext.createMediaStreamDestination();

            const audioGraphInfo = [
                {
                    node_type: 'MediaStreamAudioSourceNode',
                    number_of_inputs: sourceNode.numberOfInputs,
                    number_of_outputs: sourceNode.numberOfOutputs,
                    channel_count: sourceNode.channelCount || 2,
                    channel_count_mode: sourceNode.channelCountMode || 'max'
                },
                {
                    node_type: 'MediaStreamAudioDestinationNode',
                    number_of_inputs: destNode.numberOfInputs,
                    number_of_outputs: destNode.numberOfOutputs,
                    channel_count: destNode.channelCount || 2,
                    channel_count_mode: destNode.channelCountMode || 'explicit'
                }
            ];

            console.log('[KAIO Audio Graph Source]', audioGraphInfo[0]);
            console.log('[KAIO Audio Graph Dest]', audioGraphInfo[1]);

            // Single path connection
            sourceNode.connect(destNode);

            // Raw PCM dump via ScriptProcessorNode attached to sourceNode
            try {
                scriptNode = audioContext.createScriptProcessor(4096, 2, 2);
                sourceNode.connect(scriptNode);
                
                // Muted gain node to keep scriptNode processing without playing audio locally
                dummyGain = audioContext.createGain();
                dummyGain.gain.value = 0.0;
                scriptNode.connect(dummyGain);
                dummyGain.connect(audioContext.destination);

                scriptNode.onaudioprocess = function (e) {
                    const inputBuffer = e.inputBuffer;
                    const numChannels = inputBuffer.numberOfChannels;
                    const length = inputBuffer.length;
                    const pcmData = new Int16Array(length * numChannels);

                    const left = inputBuffer.getChannelData(0);
                    const right = numChannels > 1 ? inputBuffer.getChannelData(1) : left;

                    for (let i = 0; i < length; i++) {
                        let sL = Math.max(-1, Math.min(1, left[i]));
                        let sR = Math.max(-1, Math.min(1, right[i]));
                        pcmData[i * 2] = sL < 0 ? sL * 0x8000 : sL * 0x7FFF;
                        pcmData[i * 2 + 1] = sR < 0 ? sR * 0x8000 : sR * 0x7FFF;
                    }

                    const b64 = arrayBufferToBase64(pcmData.buffer);
                    if (typeof window._kaioRawPcmChunk === 'function') {
                        window._kaioRawPcmChunk(b64);
                    }
                };
            } catch (pcmErr) {
                console.error('[KAIO] Failed to attach raw PCM ScriptProcessor:', pcmErr);
            }

            // Prefer opus/webm for low-overhead streaming; fall back if unavailable
            const selectedMime = MediaRecorder.isTypeSupported(mimeType)
                ? mimeType
                : 'audio/webm';

            mediaRecorder = new MediaRecorder(destNode.stream, {
                mimeType: selectedMime,
                audioBitsPerSecond: 128000,
            });

            let firstChunkSent = false;
            mediaRecorder.ondataavailable = function (e) {
                if (e.data && e.data.size > 0) {
                    if (!firstChunkSent) {
                        firstChunkSent = true;
                        recordTimelineEvent('first_audio_chunk', { size: e.data.size });
                    }
                    sendChunk(e.data);
                }
            };

            mediaRecorder.onerror = function (e) {
                console.error('[KAIO] MediaRecorder error:', e.error);
            };

            mediaRecorder.start(timesliceMs);
            recordTimelineEvent('mediarecorder_started', { selectedMime: selectedMime });
            console.log('[KAIO] Recording started, mime:', selectedMime);

            return { 
                ok: true, 
                mimeType: selectedMime,
                displaySurface: displaySurface,
                logicalSurface: logicalSurface,
                cursor: cursor,
                deviceId: deviceId,
                groupId: groupId,
                tracks: allTracks,
                audioTracks: audioTracks,
                videoTracks: videoTracks,
                audioGraph: audioGraphInfo,
                timeline: window._kaioTimelineEvents
            };

        } catch (err) {
            console.error('[KAIO] Failed to start recording:', err);
            recordTimelineEvent('start_recording_error', { error: err.toString() });
            return { ok: false, error: err.toString() };
        }
    };

    window._kaioStopRecording = function () {
        return new Promise(function (resolve) {
            recordTimelineEvent('recorder_stopped_requested');
            if (!mediaRecorder || mediaRecorder.state === 'inactive') {
                resolve({ ok: false, error: 'Recorder not active', timeline: window._kaioTimelineEvents });
                return;
            }

            mediaRecorder.onstop = function () {
                recordTimelineEvent('last_chunk_processed');
                recordTimelineEvent('recorder_stopped');

                // Teardown
                if (scriptNode) {
                    try { scriptNode.onaudioprocess = null; scriptNode.disconnect(); } catch (_) {}
                }
                if (dummyGain) {
                    try { dummyGain.disconnect(); } catch (_) {}
                }
                if (sourceNode) { try { sourceNode.disconnect(); } catch (_) {} }
                if (audioContext) { try { audioContext.close(); } catch (_) {} }
                if (stream) {
                    stream.getTracks().forEach(function (t) { t.stop(); });
                }

                mediaRecorder = null;
                audioContext = null;
                sourceNode = null;
                destNode = null;
                scriptNode = null;
                dummyGain = null;
                stream = null;

                console.log('[KAIO] Recording stopped');
                resolve({ ok: true, timeline: window._kaioTimelineEvents });
            };

            mediaRecorder.stop();
        });
    };

    window._kaioRecordingStatus = function () {
        if (!mediaRecorder) return 'inactive';
        return mediaRecorder.state;
    };

    window._kaioGetTimeline = function () {
        return window._kaioTimelineEvents || [];
    };

    console.log('[KAIO] Enhanced audio capture script installed');
})();
"""
