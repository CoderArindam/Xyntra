import api from '../lib/axios';

export interface Task {
  id: number;
  board_id: number;
  board_name: string;
  organization_id: number;
  task_reference: string;
  column_id: number;
  column_name: string;
  column_type: 'TODO' | 'IN_PROGRESS' | 'DONE';
  is_completed: boolean;
  title: string;
  description?: string;
  priority?: string;
  due_date?: string | null;
  reminder_at?: string | null;
  completed_at?: string | null;
  created_at: string;
  updated_at: string;
  
  assigned_to?: number;
  assignee_email?: string;
  assignee_first_name?: string;
  assignee_last_name?: string;
  assignee_avatar_url?: string;
  
  created_by?: number;
  creator_email?: string;
  creator_first_name?: string;
  creator_last_name?: string;
  creator_avatar_url?: string;
}

export interface Column {
  id: number;
  name: string;
  position: number;
  is_completed: boolean; // Deprecated
  column_type: 'TODO' | 'IN_PROGRESS' | 'DONE';
}

export interface BoardData {
  columns: Column[];
  tasks: Task[];
}

export const getBoardTasks = async (boardId: number | string): Promise<BoardData> => {
  const response = await api.get(`/boards/${boardId}/tasks`);
  return response.data.data;
};


export const createTask = async (taskData: Partial<Task>): Promise<Task> => {
  const response = await api.post('/tasks', taskData);
  return response.data.data;
};

export const updateTaskStatus = async (taskId: number, columnId: number): Promise<Task> => {
  const response = await api.patch(`/tasks/${taskId}`, { column_id: columnId });
  return response.data.data;
};

export const deleteTask = async (taskId: number): Promise<void> => {
  await api.delete(`/tasks/${taskId}`);
};

export const updateTaskAssignee = async (taskId: number, assignedTo: number | null): Promise<Task> => {
  const response = await api.patch(`/tasks/${taskId}/assignee`, { assigned_to: assignedTo });
  return response.data.data;
};

export const updateTask = async (
  taskId: number,
  data: { title?: string; description?: string; priority?: string; column_id?: number; due_date?: string | null; reminder_at?: string | null }
): Promise<Task> => {
  const response = await api.patch(`/tasks/${taskId}`, data);
  return response.data.data;
};

