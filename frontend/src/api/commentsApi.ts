import api from './axios';

export interface Comment {
  id: number;
  task_id: number;
  user_id: number;
  user_first_name: string | null;
  user_last_name: string | null;
  user_avatar_url: string | null;
  user_email: string | null;
  content: string;
  parent_comment_id: number | null;
  created_at: string;
}

export const getTaskComments = async (taskId: number): Promise<Comment[]> => {
  const response = await api.get(`/tasks/${taskId}/comments`);
  return response.data.data;
};

export const createComment = async (
  taskId: number,
  data: { content: string; parent_comment_id?: number }
): Promise<Comment> => {
  const response = await api.post(`/tasks/${taskId}/comments`, data);
  return response.data.data;
};

export const deleteComment = async (commentId: number): Promise<void> => {
  await api.delete(`/comments/${commentId}`);
};
