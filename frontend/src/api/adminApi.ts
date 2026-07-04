import axiosInstance from './axios';

export interface AdminUser {
  id: number;
  email: string;
  role: string;
  created_at: string;
}

export interface AdminBoard {
  id: number;
  name: string;
  owner_id: number;
  created_at: string;
  member_count: number;
}

export interface AdminBoardMember {
  id: number;
  email: string;
  role: string;
  permission: string;
  joined_at: string;
}

export const adminFetchUsers = async (): Promise<AdminUser[]> => {
  const response = await axiosInstance.get('/admin/users');
  return response.data;
};

export const adminCreateUser = async (data: any): Promise<AdminUser> => {
  const response = await axiosInstance.post('/admin/users', data);
  return response.data;
};

export const adminUpdateUserRole = async (userId: number, role: string): Promise<AdminUser> => {
  const response = await axiosInstance.patch(`/admin/users/${userId}/role`, { role });
  return response.data;
};

export const adminDeleteUser = async (userId: number): Promise<void> => {
  await axiosInstance.delete(`/admin/users/${userId}`);
};

export const adminFetchBoards = async (): Promise<AdminBoard[]> => {
  const response = await axiosInstance.get('/admin/boards');
  return response.data;
};

export const adminFetchBoardMembers = async (boardId: number): Promise<AdminBoardMember[]> => {
  const response = await axiosInstance.get(`/admin/boards/${boardId}/members`);
  return response.data;
};

export const adminAssignUser = async (boardId: number, userId: number, permission: string): Promise<void> => {
  await axiosInstance.post(`/admin/boards/${boardId}/members`, { user_id: userId, permission });
};

export const adminRemoveUser = async (boardId: number, userId: number): Promise<void> => {
  await axiosInstance.delete(`/admin/boards/${boardId}/members/${userId}`);
};
