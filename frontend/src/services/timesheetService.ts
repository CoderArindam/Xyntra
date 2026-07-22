import api from '../lib/axios';

export interface Timesheet {
  id: string;
  org_id: string;
  user_id: string;
  submitter_name: string;
  submitter_email: string;
  week_start_date: string;
  week_end_date: string;
  status: 'DRAFT' | 'SUBMITTED' | 'APPROVED' | 'REJECTED' | string;
  total_hours: number;
  standard_hours_per_week: number;
  entry_count: number;
  submitted_at?: string | null;
  reviewed_at?: string | null;
  approver_id?: string | null;
  approver_name?: string | null;
  approver_comment?: string | null;
  member_note?: string | null;
}

export interface TimesheetEntry {
  id: string;
  timesheet_id: string;
  board_id?: string | null;
  board_name?: string | null;
  task_id?: string | null;
  task_title?: string | null;
  entry_date: string;
  hours: number;
  entry_type: 'task' | 'meeting' | 'general' | 'leave' | 'holiday' | string;
  description?: string | null;
  is_overtime: boolean;
}

export interface TimesheetAudit {
  id: string;
  actor_name: string;
  actor_email: string;
  from_status?: string | null;
  to_status: string;
  comment?: string | null;
  created_at: string;
}

export interface TimesheetDetail extends Timesheet {
  entries: TimesheetEntry[];
  audit_log: TimesheetAudit[];
}

export interface CreateTimesheetRequest {
  week_start_date: string;
}

export interface UpsertEntryRequest {
  board_id?: string | null;
  task_id?: string | null;
  entry_date: string;
  hours: number;
  entry_type: 'task' | 'meeting' | 'general' | 'leave' | 'holiday' | string;
  description?: string | null;
}

export const getMyTimesheets = async (params?: {
  status?: string;
  week_start_date?: string;
}): Promise<Timesheet[]> => {
  const response = await api.get<Timesheet[]>('/timesheets', { params });
  return response.data;
};

export const createTimesheet = async (data: CreateTimesheetRequest): Promise<Timesheet> => {
  const response = await api.post<Timesheet>('/timesheets', data);
  return response.data;
};

export const getTimesheetDetail = async (id: string): Promise<TimesheetDetail> => {
  const response = await api.get<TimesheetDetail>(`/timesheets/${id}`);
  return response.data;
};

export const upsertEntry = async (
  timesheetId: string,
  data: UpsertEntryRequest
): Promise<TimesheetEntry> => {
  const response = await api.post<TimesheetEntry>(`/timesheets/${timesheetId}/entries`, data);
  return response.data;
};

export const deleteEntry = async (timesheetId: string, entryId: string): Promise<void> => {
  await api.delete(`/timesheets/${timesheetId}/entries/${entryId}`);
};

export const submitTimesheet = async (
  id: string,
  data: { member_note?: string; approver_id?: string }
): Promise<Timesheet> => {
  const response = await api.post<Timesheet>(`/timesheets/${id}/submit`, data);
  return response.data;
};

export const recallTimesheet = async (
  id: string,
  data: { reason: string }
): Promise<Timesheet> => {
  const response = await api.post<Timesheet>(`/timesheets/${id}/recall`, data);
  return response.data;
};
