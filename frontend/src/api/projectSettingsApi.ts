import api from './axios';
import type { Board } from './boardsApi';

export interface ProjectSettingsUpdate {
  name?: string;
  description?: string;
  icon?: string;
  color?: string;
  cover_gradient?: string;
  default_assignee_id?: number | null;
  project_lead_id?: number | null;
}

export interface ProjectStatistics {
  total_tasks: number;
  completed_tasks: number;
  overdue_tasks: number;
  members_count: number;
  columns_count: number;
  last_activity: string | null;
}

export interface ProjectSettingsResponse {
  settings: Board;
  statistics: ProjectStatistics;
}

export const getProjectSettings = async (boardId: number): Promise<ProjectSettingsResponse> => {
  const { data } = await api.get<{ data: ProjectSettingsResponse }>(`/boards/${boardId}/settings`);
  return data.data;
};

export const updateProjectSettings = async (boardId: number, updates: ProjectSettingsUpdate): Promise<ProjectSettingsResponse> => {
  const { data } = await api.patch<{ data: ProjectSettingsResponse }>(`/boards/${boardId}/settings`, updates);
  return data.data;
};

export const archiveProject = async (boardId: number): Promise<ProjectSettingsResponse> => {
  const { data } = await api.post<{ data: ProjectSettingsResponse }>(`/boards/${boardId}/archive`);
  return data.data;
};
