"""Validation script to test the Google authentication flow."""

import argparse
import asyncio
import sys
import shutil
from pathlib import Path

# Ensure backend root is in sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.meeting.bot.browser.factory import BrowserFactory
from app.meeting.bot.browser.google_auth import GoogleAuthService
from app.meeting.config import meeting_config

async def main() -> None:
    parser = argparse.ArgumentParser(description="Test Google Login Automation.")
    parser.add_argument("--clean-profile", action="store_true", help="Delete existing browser profile before launching.")
    args = parser.parse_args()

    print("=================================================")
    print("Google Authentication Validation")
    print("=================================================\n")

    profile_dir = Path(meeting_config.PROFILE_DIR)
    
    if args.clean_profile:
        print("Cleaning up old browser profile...")
        if profile_dir.exists():
            shutil.rmtree(profile_dir, ignore_errors=True)
            print("✓ Profile deleted.")

    print("\nLaunching Chromium...")
    try:
        session = await BrowserFactory.create(
            profile_dir=str(profile_dir),
            headless=meeting_config.HEADLESS,
        )
    except Exception as e:
        print(f"✗ Failed to launch browser: {e}")
        sys.exit(1)

    print("✓ Browser running.")

    context = session.context
    page = context.pages[0] if context.pages else await context.new_page()

    auth_service = GoogleAuthService(
        email=meeting_config.GOOGLE_EMAIL,
        password=meeting_config.GOOGLE_PASSWORD,
    )

    print("\nEnsuring Authentication...")
    try:
        await auth_service.ensure_authenticated(page)
        print("✓ Authentication successful.")
    except Exception as e:
        print(f"✗ Authentication failed: {e}")
    finally:
        print("\nClosing browser...")
        try:
            await context.close()
            await session.playwright.stop()
        except Exception as e:
            print(f"Error during cleanup: {e}")

if __name__ == "__main__":
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8")
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nCancelled.")
        sys.exit(0)
