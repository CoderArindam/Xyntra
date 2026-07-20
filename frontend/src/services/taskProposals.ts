import api from '../lib/axios';

export interface TaskProposal {
  id: string;
  org_id: number;
  org_name?: string;
  board_id?: number | null;
  board_name?: string;
  board_confidence?: number | null;
  board_source?: 'llm_matched' | 'meeting_default' | 'manager_assigned' | null;
  meeting_session_id: string;
  meeting_url?: string;
  meeting_started_at?: string;
  title: string;
  description?: string;
  priority?: string | null;
  due_date?: string | null;
  confidence_score?: number;
  source_transcript_quote?: string;
  status: 'pending' | 'approved' | 'rejected';
  raw_llm_payload?: any;
  created_at: string;

  suggested_assignee_id?: number | null;
  suggested_assignee_email?: string;
  suggested_assignee_first_name?: string;
  suggested_assignee_last_name?: string;
  suggested_assignee_display_name?: string;
  suggested_assignee_avatar_url?: string;

  reviewed_by?: number | null;
  reviewer_email?: string;
  reviewer_first_name?: string;
  reviewer_last_name?: string;
  reviewer_display_name?: string;
  reviewer_avatar_url?: string;
  reviewed_at?: string;

  created_task_id?: number | null;
}

export const listProposalsByMeeting = async (sessionId: string): Promise<TaskProposal[]> => {
  const response = await api.get(`/meeting/${sessionId}/proposals`);
  return response.data.data;
};

export const getProposal = async (id: string): Promise<TaskProposal> => {
  const response = await api.get(`/proposals/${id}`);
  return response.data.data;
};

export const updateProposal = async (
  id: string,
  data: {
    title?: string;
    description?: string;
    suggested_assignee_id?: number | null;
    board_id?: number | null;
    priority?: string | null;
    due_date?: string | null;
  }
): Promise<TaskProposal> => {
  const response = await api.put(`/proposals/${id}`, data);
  return response.data.data;
};

export const approveProposal = async (
  id: string,
  payload?: { board_id?: number | null }
): Promise<any> => {
  const response = await api.post(`/proposals/${id}/approve`, payload || {});
  return response.data.data;
};

export const rejectProposal = async (id: string): Promise<TaskProposal> => {
  const response = await api.post(`/proposals/${id}/reject`);
  return response.data.data;
};

export const listPendingProposalsByBoard = async (boardId: number): Promise<TaskProposal[]> => {
  const response = await api.get(`/boards/${boardId}/proposals`);
  return response.data.data;
};

export const listOrgProposals = async (status: string = 'pending'): Promise<TaskProposal[]> => {
  const response = await api.get('/proposals', { params: { status } });
  return response.data.data;
};
