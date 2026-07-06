import api from '../lib/axios';

export interface User {
  id: number;
  email: string;
  first_name: string | null;
  last_name: string | null;
  avatar_url: string | null;
}

export interface BoardMember extends User {
  joined_at: string;
}

export const getUsers = async (): Promise<User[]> => {
  const response = await api.get('/users');
  return response.data.data;
};

export const getBoardMembers = async (boardId: number): Promise<BoardMember[]> => {
  const response = await api.get(`/boards/${boardId}/members`);
  return response.data.data;
};

export interface UserUpdatePayload {
  first_name?: string | null;
  last_name?: string | null;
  avatar_url?: string | null;
}

export const updateProfile = async (payload: UserUpdatePayload): Promise<User> => {
  const response = await api.patch('/users/me', payload);
  return response.data.data;
};

export const changePassword = async (current_password: string, new_password: string): Promise<void> => {
  await api.put('/users/me/password', { current_password, new_password });
};

export const uploadAvatar = async (file: File): Promise<string> => {
  const formData = new FormData();
  formData.append('file', file);
  
  const response = await api.post('/users/me/avatar', formData, {
    headers: {
      'Content-Type': undefined,
    },
  });
  return response.data.data.avatar_url;
};

export const deleteAvatar = async (): Promise<void> => {
  await api.delete('/users/me/avatar');
};
