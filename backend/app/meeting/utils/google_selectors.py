"""Centralised Google UI selectors.

ALL Google Auth and Google Meet DOM selectors live here.
When Google changes its UI, only this file needs updating.

Sections:
  - Google Auth
  - Meet: Lobby / Pre-join
  - Meet: Meeting Controls
  - Meet: Participant Panel  (used by ParticipantDOM)
  - Meet: Speaker Detection  (used by SpeakerDOM)
  - Meet: State Banners      (used by MeetingDOM)
  - Meet: Error States
"""

from __future__ import annotations


# ------------------------------------------------------------------ #
# Google Account authentication selectors                             #
# ------------------------------------------------------------------ #



GOOGLE_ACCOUNT_URL = "https://accounts.google.com"
GOOGLE_SIGNIN_URL = "https://accounts.google.com/signin"
GOOGLE_MY_ACCOUNT_URL = "https://myaccount.google.com"


# ------------------------------------------------------------------ #
# Google Meet selectors                                                #
# ------------------------------------------------------------------ #

MEET_SELECTORS: dict[str, str] = {

    # ── Lobby / pre-join ─────────────────────────────────────────────
    "join_now_btn":            'button:has-text("Join now")',
    "ask_to_join_btn":         'button:has-text("Ask to join")',
    "join_now_jsname":         'button[jsname="Qx7uuf"]',
    "mic_toggle":              '[aria-label="Turn off microphone"]',
    "mic_toggle_off":          '[aria-label="Turn on microphone"]',
    "cam_toggle":              '[aria-label="Turn off camera"]',
    "cam_toggle_off":          '[aria-label="Turn on camera"]',
    "name_input":              'input[placeholder="Your name"]',

    # ── Cookie / consent banners ─────────────────────────────────────
    "cookie_accept_all":       'button:has-text("Accept all")',
    "cookie_accept":           'button:has-text("I agree")',
    "cookie_reject_all":       'button:has-text("Reject all")',

    # ── Meeting controls ─────────────────────────────────────────────
    "meeting_controls":        '[data-call-collapsed]',
    "leave_btn":               'button[aria-label="Leave call"]',
    "leave_btn_text":          'button:has-text("Leave")',

    # ── In-meeting join indicators (used by confidence-based detector) ─
    # Each selector independently signals the bot is inside the meeting.
    # Note: Mic/Camera/More are ambiguous because they exist in the pre-join lobby too!
    "indicator_leave":         'button[aria-label="Leave call"], button[aria-label="Leave"]',
    "indicator_people":        '[role="button"]:has-text("People"), [role="button"]:has-text("Show everyone"), [aria-label="People"], [aria-label="Show everyone"]',
    "indicator_chat":          'button[aria-label="Chat with everyone"], button[aria-label="Open chat"]',
    "indicator_activities":    'button[aria-label="Activities"]',
    "indicator_toolbar":       '[data-call-collapsed], [jsname="P4eknd"], [jsname="haAclf"]',
    "indicator_captions":      'button[aria-label="Turn on captions"], button[aria-label="Turn off captions"]',
    "indicator_timer":         '[jsname="vRBwBb"], [data-call-duration], [aria-label*="duration"]',

    # ── Waiting room ─────────────────────────────────────────────────
    "waiting_room_text":       'text=/You\'re in the waiting room|Asking to join|You\'ll join the call when someone lets you in/i',
    "waiting_for_host":        'text="Waiting for others to join"',

    # ── Error states ─────────────────────────────────────────────────
    "meeting_not_found":       'text="Check your meeting code and try again"',
    "meeting_ended":           'text="The meeting has ended"',
    "permission_denied":       'text=/Someone in the call denied your request to join/i',
    "network_error":           'text="Can\'t join"',
    "login_required":          'text="Sign in to continue"',
    "empty_meeting_popup":     'text=/No one else|You\'re the only one here|Everyone else has left|You\'re the only person in this call/i',

    # ── Participant panel (ParticipantDOM) ────────────────────────────
    # Each row in the participant list OR video tile
    "participant_list_item":        '[data-participant-id]',

    # Name element inside a participant row/tile
    "participant_name_in_item":     'span.notranslate',

    # The bot's own name tile
    "self_participant_name":        '[data-self-name], [jsname="selfName"]',
    "self_name_fallback":           '[aria-label*="(You)"]',

    # ── Speaker detection (SpeakerDOM) ────────────────────────────────
    # Name of the currently speaking participant
    "speaking_indicator_name":      '[data-speaking-indicator="true"] [data-display-name]',

    # Alternate active-speaker label element
    "active_speaker_label":         '[jsname="active-speaker-name"], .active-speaker-name',

    # Video tile wrapper flagged while participant is speaking
    "speaking_video_tile":          '[data-speaking-indicator="true"]',

    # Name label within any video tile
    "video_tile_name":              '[data-display-name], [jsname="displayName"]',

    # ── Connection / state banners (MeetingDOM) ───────────────────────
    "reconnecting_dialog":          'text="Trying to reconnect"',
    "network_lost_banner":          'text="Your internet connection is unstable"',

    # Bot removed from meeting dialog
    "bot_removed_dialog":           'text=/You\'ve been removed from the meeting|Someone removed you from the meeting/i',

    # Host ended meeting for everyone banner
    "host_ended_meeting":           'text="The host ended the meeting for everyone"',
}

# Meeting URL pattern used by provider factory
GOOGLE_MEET_URL_PATTERN = "meet.google.com"
