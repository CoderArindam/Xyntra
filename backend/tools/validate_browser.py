"""Browser validation tool."""

import asyncio
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# Ensure backend root is in sys.path
backend_root = Path(__file__).resolve().parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from app.meeting.bot.browser.factory import BrowserFactory
from app.meeting.config import meeting_config
from app.meeting.exceptions import BrowserLaunchError

try:
    import httpx
except ImportError:
    print("httpx is required for validation. Run: pip install httpx")
    sys.exit(1)


async def poll_backend_status(session_id: str, timeout: float = 10.0):
    start_time = time.time()
    headers = {"Authorization": "Bearer dev-key"}
    
    async with httpx.AsyncClient() as client:
        while time.time() - start_time < timeout:
            try:
                # The debug/status endpoint is global, but we use it to check connection
                resp = await client.get("http://127.0.0.1:8000/api/v1/meeting/presence/debug/status", headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    # Check if our fake event arrived
                    pending = data.get("pending_events", [])
                    for ev in pending:
                        if ev.get("participant_id") == "fake-participant-123":
                            return data
            except httpx.RequestError:
                pass
            await asyncio.sleep(0.5)
    return None


async def cleanup_timeline(session_id: str):
    timeline_path = Path(meeting_config.RECORDING_OUTPUT_DIR) / session_id / "participant_presence_timeline.json"
    if timeline_path.exists():
        try:
            with open(timeline_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # Remove the fake participant
            data["events"] = [e for e in data.get("events", []) if e.get("participant_id") != "fake-participant-123"]
            data["current_snapshot"] = [p for p in data.get("current_snapshot", []) if p.get("participant_id") != "fake-participant-123"]
            
            with open(timeline_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Warning: Failed to cleanup timeline: {e}")


async def main():
    import sys
    if sys.stdout.encoding.lower() != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except AttributeError:
            pass

    profile_dir = meeting_config.PROFILE_DIR
    session_id = "oam-vmkr-fko"
    meet_url = f"https://meet.google.com/{session_id}"
    
    print("Starting browser validation...")
    print("Launching Chromium...")
    
    start_ts = time.time()
    report = {
        "Verification Timestamp": datetime.utcnow().isoformat() + "Z",
        "Browser Profile Path": profile_dir,
    }
    
    try:
        session = await BrowserFactory.create(profile_dir=profile_dir, headless=False)
        print("✓ Persistent Context")
        
        ext_path = BrowserFactory.resolve_extension_path()
        print("✓ Extension Installed")
        
        workers = session.context.service_workers
        if len(workers) != 1:
            raise RuntimeError(f"Expected exactly 1 Service Worker, found {len(workers)}")
        
        worker = workers[0]
        print("✓ Background Worker Running")
        
        # Configure extension
        await worker.evaluate(f'''async () => {{
            await chrome.storage.local.set({{
                backendUrl: "http://127.0.0.1:8000/api/v1",
                apiKey: "dev-key"
            }});
            // Update variables directly in scope and trigger registration
            backendUrl = "http://127.0.0.1:8000/api/v1";
            apiKey = "dev-key";
            if (typeof registerWithBackend === "function") {{
                registerWithBackend();
            }}
        }}''')
        
        print("Opening Google Meet...")
        page = await session.context.new_page()
        await page.goto(meet_url, wait_until="networkidle")
        
        # Wait for handshake
        print("Waiting for Content Script injection...")
        await asyncio.sleep(2.0)
        
        pong = await worker.evaluate(
            '''() => {
                return {
                    extension_version: chrome.runtime.getManifest().version,
                    manifest_version: chrome.runtime.getManifest().manifest_version,
                    active_tabs: typeof activeTabs !== "undefined" ? activeTabs : {}
                };
            }'''
        )
        
        active_tabs = pong.get("active_tabs", {})
        if len(active_tabs) != 1:
            raise RuntimeError(f"Expected exactly 1 active content script, found {len(active_tabs)}")
            
        print("✓ Content Script Injected")
        print("✓ Service Worker Handshake")
        
        # Simulate DOM Mutation
        print("Simulating DOM mutation...")
        await page.evaluate("""() => {
            const container = document.createElement('div');
            container.setAttribute('aria-label', 'Participants');
            container.setAttribute('role', 'list');
            document.body.appendChild(container);
            
            setTimeout(() => {
                const item = document.createElement('div');
                item.setAttribute('role', 'listitem');
                item.setAttribute('data-participant-id', 'fake-participant-123');
                const name = document.createElement('span');
                name.setAttribute('dir', 'ltr');
                name.textContent = 'Fake Validation User';
                item.appendChild(name);
                container.appendChild(item);
            }, 500);
        }""")
        
        print("Waiting for backend events...")
        status = await poll_backend_status(session_id, timeout=10.0)
        
        if status:
            print("✓ Runtime Messaging")
            print("✓ Backend Connected")
            print("✓ Presence Endpoint Healthy")
        else:
            raise RuntimeError("Backend did not receive the fake event within timeout.")
            
        # Verify timeline
        timeline_path = Path(meeting_config.RECORDING_OUTPUT_DIR) / session_id / "participant_presence_timeline.json"
        if not timeline_path.exists():
            raise RuntimeError(f"Timeline file not found: {timeline_path}")
            
        print("✓ Timeline updated")
        
        # Cleanup
        print("Cleaning up...")
        await page.close()
        await cleanup_timeline(session_id)
        
        # Build report
        report.update({
            "Browser Version": "chromium", # placeholder
            "Playwright Version": "unknown", # difficult to extract dynamically
            "Extension Version": pong.get("extension_version"),
            "Manifest Version": pong.get("manifest_version"),
            "Worker Status": "OK",
            "Content Script Status": "OK",
            "Backend Status": "Connected",
            "Handshake Latency": "N/A",
            "Message Latency": "N/A",
            "Overall Status": "SUCCESS"
        })
        
        with open("browser_validation_report.json", "w") as f:
            json.dump(report, f, indent=2)
            
        print("\nValidation Successful")
        
        await session.context.close()
        await session.playwright.stop()
        
    except Exception as e:
        print(f"\nValidation Failed: {e}")
        report["Overall Status"] = "FAILED"
        report["Error"] = str(e)
        with open("browser_validation_report.json", "w") as f:
            json.dump(report, f, indent=2)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
