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

GOOGLE_AUTH_SELECTORS: dict[str, str] = {
    "email_input":              'input[type="email"]',
    "password_input":           'input[type="password"]',
    "email_next":               "#identifierNext",
    "password_next":            "#passwordNext",
    "account_avatar":           'a[aria-label^="Google Account"]',
    "error_wrong_password":     '.LXRPh',
    "error_account_not_found":  '.o6cuMc',
    "security_challenge":       '#challengePickerList',
    "account_chooser":          '[data-profileindex]',
    "account_chooser_text":     "Choose an account",
    "cookie_consent_text":      "Accept all",
    "suspicious_login_text_1":  "Suspicious activity",
    "suspicious_login_text_2":  "Verify it's you",
    "captcha":                  'iframe[src*="recaptcha"], iframe[title*="recaptcha"]',
    "all_headings":             'h1, h2, h3',
    "all_buttons":              'button, [role="button"]',
    "all_inputs":               'input',
}

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
    "indicator_leave":         'button[aria-label="Leave call"], button[aria-label="Leave"]',
    "indicator_mic":           'button[aria-label="Turn off microphone"], button[aria-label="Turn on microphone"], button[data-is-muted]',
    "indicator_camera":        'button[aria-label="Turn off camera"], button[aria-label="Turn on camera"]',
    "indicator_more_options":  'button[aria-label="More options"], button[aria-label="More"]',
    "indicator_people":        'button[aria-label="People"], button[aria-label="Show everyone"]',
    "indicator_chat":          'button[aria-label="Chat with everyone"], button[aria-label="Open chat"]',
    "indicator_activities":    'button[aria-label="Activities"]',
    "indicator_toolbar":       '[data-call-collapsed], [jsname="P4eknd"], [jsname="haAclf"]',
    "indicator_captions":      'button[aria-label="Turn on captions"], button[aria-label="Turn off captions"]',
    "indicator_timer":         '[jsname="vRBwBb"], [data-call-duration], [aria-label*="duration"]',

    # ── Waiting room ─────────────────────────────────────────────────
    "waiting_room_text":       'text="You\'re in the waiting room"',
    "waiting_for_host":        'text="Waiting for others to join"',

    # ── Error states ─────────────────────────────────────────────────
    "meeting_not_found":       'text="Check your meeting code and try again"',
    "meeting_ended":           'text="The meeting has ended"',
    "permission_denied":       'text="You can\'t join this video call"',
    "network_error":           'text="Can\'t join"',
    "login_required":          'text="Sign in to continue"',

    # ── Participant panel (ParticipantDOM) ────────────────────────────
    # Button that opens the People side panel
    "participants_panel_btn":       '[aria-label="People"]',
    "participants_panel_btn_v2":    'button[data-panel-id="participants"]',

    # Container present when panel is open
    "participant_panel_container":  '[data-panel-id="participants"], [jsname="participants-panel"]',

    # Each row in the participant list
    "participant_list_item":        '[data-participant-id], [jsname="participant-item"]',

    # Name element inside a participant row
    "participant_name_in_item":     '[data-display-name], [jsname="displayName"], .participant-name',

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
