import api from '../lib/axios';

export interface MeetingSession {
  id: string;
  session_id: string;
  org_id: number;
  org_name?: string;
  meeting_url: string;
  status: string;
  source: 'manual' | 'google_calendar';
  calendar_event_id?: string | null;
  scheduled_start_time?: string | null;
  started_at?: string | null;
  created_at: string;
  initiated_by_user_id?: number | null;
  initiator_email?: string | null;
  initiator_display_name?: string | null;
  initiator_avatar_url?: string | null;
}

export const joinMeeting = async (
  meetingUrl: string,
  boardId?: number | null
): Promise<{ session_id: string; status: string; state: string; message: string }> => {
  const response = await api.post('/meeting/join', {
    meeting_url: meetingUrl,
    board_id: boardId || undefined,
  });
  return response.data;
};

export const listRecentMeetingSessions = async (): Promise<MeetingSession[]> => {
  const response = await api.get('/meeting/sessions');
  return response.data.data;
};

export const deleteMeetingSession = async (sessionId: string): Promise<void> => {
  await api.delete(`/meeting/session/${sessionId}`);
};
