import api from '../lib/axios';

export interface Attachment {
  id: number;
  task_id: number;
  uploaded_by: number;
  file_name: string;
  file_url: string;
  created_at: string;
}

export const getTaskAttachments = async (taskId: number): Promise<Attachment[]> => {
  const response = await api.get(`/tasks/${taskId}/attachments`);
  return response.data;
};

export const createAttachment = async (
  taskId: number,
  data: { file_name: string; file_url: string }
): Promise<Attachment> => {
  const response = await api.post(`/tasks/${taskId}/attachments`, data);
  return response.data;
};
