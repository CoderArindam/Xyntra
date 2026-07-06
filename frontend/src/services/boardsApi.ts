import api from '../lib/axios';

export interface Board {
  id: number;
  organization_id: number;
  name: string;
  project_key: string;
  owner_id: number;
  description?: string | null;
  icon?: string | null;
  color?: string | null;
  cover_gradient?: string | null;
  default_assignee_id?: number | null;
  project_lead_id?: number | null;
  archived_at?: string | null;
  created_at: string;
  member_count: number;
  task_count: number;
}

export const getBoards = async (): Promise<Board[]> => {
  const response = await api.get('/boards?include_archived=true');
  return response.data.data;
};

export const createBoard = async (boardData: Partial<Board>): Promise<Board> => {
  const response = await api.post('/boards', boardData);
  return response.data.data;
};

export const deleteBoard = async (boardId: number): Promise<void> => {
  await api.delete(`/boards/${boardId}`);
};
