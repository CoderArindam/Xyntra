import api from './axios';
import { type Task } from './tasksApi';

export interface MyWorkSummary {
  assigned: number;
  due_today: number;
  overdue: number;
  completed_this_week: number;
}

export interface MyTask extends Task {
  board_name: string;
  column_name: string;
  is_completed: boolean;
}

export const getMyWorkSummary = async (): Promise<MyWorkSummary> => {
  const response = await api.get('/my-work/summary');
  return response.data.data;
};

export const getMyTasks = async (params?: {
  due?: string;
  sort?: string;
  limit?: number;
  offset?: number;
}): Promise<MyTask[]> => {
  const response = await api.get('/my-work/tasks', { params });
  return response.data.data;
};
