import api from './axios';

export interface Board {
  id: number;
  organization_id: number;
  name: string;
  project_key: string;
  owner_id: number;
  created_at: string;
  member_count: number;
  task_count: number;
}

export const getBoards = async (): Promise<Board[]> => {
  const response = await api.get('/boards');
  return response.data.data;
};

export const createBoard = async (name: string): Promise<Board> => {
  const response = await api.post('/boards', { name });
  return response.data.data;
};

export const deleteBoard = async (boardId: number): Promise<void> => {
  await api.delete(`/boards/${boardId}`);
};
