import api from '../lib/axios';

export interface TasksByStatus {
  todo: number;
  in_progress: number;
  review: number;
  done: number;
}

export interface DashboardKPIs {
  total_tasks: number;
  tasks_by_status: TasksByStatus;
  overdue_tasks: number;
  total_boards: number;
  team_size: number;
  pending_proposals_count: number;
  active_meetings_count: number;
}

export interface DashboardBoardSummary {
  id: number;
  name: string;
  project_key?: string;
  description?: string;
  icon?: string;
  color?: string;
  cover_gradient?: string;
  task_count: number;
  completed_task_count: number;
  completion_percentage: number;
  overdue_count: number;
  member_count: number;
  created_at?: string;
}

export interface DashboardActivityItem {
  id: number;
  organization_id: number;
  entity_type: string;
  entity_id: number;
  activity_type: string;
  old_value?: Record<string, any> | null;
  new_value?: Record<string, any> | null;
  metadata?: Record<string, any> | null;
  created_at: string;
  actor_id?: number | null;
  actor_first_name?: string | null;
  actor_last_name?: string | null;
  actor_avatar_url?: string | null;
  actor_email?: string | null;
  target_reference?: string | null;
}

export interface DashboardSummaryResponse {
  kpis: DashboardKPIs;
  boards: DashboardBoardSummary[];
  recent_activity: DashboardActivityItem[];
}

export const getDashboardSummary = async (): Promise<DashboardSummaryResponse> => {
  const response = await api.get('/dashboard/summary');
  return response.data.data;
};
