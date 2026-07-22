import api from '../lib/axios';
import type { Timesheet } from './timesheetService';

export interface ApprovalQueueItem extends Timesheet {
  days_since_submitted: number;
  is_overdue: boolean;
  boards_involved: string[];
}

export interface ApprovalQueueSummary {
  pending_count: number;
  approved_this_week: number;
  rejected_this_week: number;
  avg_hours_approved: number;
  oldest_pending_days: number | null;
}

export const getApprovalQueue = async (params?: {
  status?: string;
  board_id?: string;
}): Promise<ApprovalQueueItem[]> => {
  const response = await api.get<ApprovalQueueItem[]>('/timesheets/approvals/queue', { params });
  return response.data;
};

export const getApprovalQueueSummary = async (): Promise<ApprovalQueueSummary> => {
  const response = await api.get<ApprovalQueueSummary>('/timesheets/approvals/queue/summary');
  return response.data;
};

export const approveTimesheet = async (
  id: string,
  data: { comment?: string }
): Promise<Timesheet> => {
  const response = await api.post<Timesheet>(`/timesheets/${id}/approve`, data);
  return response.data;
};

export const rejectTimesheet = async (
  id: string,
  data: { comment: string }
): Promise<Timesheet> => {
  const response = await api.post<Timesheet>(`/timesheets/${id}/reject`, data);
  return response.data;
};
