import api from '../lib/axios';

export interface TimesheetPolicy {
  org_id: string;
  week_start_day: 'monday' | 'tuesday' | 'wednesday' | 'thursday' | 'friday' | 'saturday' | 'sunday';
  standard_hours_per_day: number;
  standard_hours_per_week: number;
  max_hours_per_day: number;
  overtime_policy: 'none' | 'flag_only' | 'block_submission';
  submission_deadline_days: number;
  allow_future_entry: boolean;
  allow_past_entry_days: number;
  require_task_link: boolean;
  allow_member_recall: boolean;
  org_name: string;
  org_slug: string;
}

export interface ApproverAssignment {
  id: string;
  org_id: string;
  approver_user_id: string;
  approver_name: string;
  approver_email: string;
  assigned_by_name: string;
}

export interface EligibleApprover {
  user_id: string;
  display_name: string;
  email: string;
  role: string;
  is_approver?: boolean;
}

export const getTimesheetPolicy = async (): Promise<TimesheetPolicy> => {
  const response = await api.get<TimesheetPolicy>('/timesheets/policy');
  return response.data;
};

export const updateTimesheetPolicy = async (data: Partial<TimesheetPolicy>): Promise<TimesheetPolicy> => {
  const response = await api.put<TimesheetPolicy>('/timesheets/policy', data);
  return response.data;
};

export const getApproverAssignments = async (): Promise<ApproverAssignment[]> => {
  const response = await api.get<ApproverAssignment[]>('/timesheets/approvers');
  return response.data;
};

export const getEligibleApprovers = async (): Promise<EligibleApprover[]> => {
  const response = await api.get<EligibleApprover[]>('/timesheets/approvers/eligible');
  return response.data;
};

export const getAllManagersWithApproverStatus = async (): Promise<EligibleApprover[]> => {
  const response = await api.get<EligibleApprover[]>('/timesheets/approvers/managers');
  return response.data;
};

export const assignApprover = async (data: {
  approver_user_id: string;
}): Promise<ApproverAssignment> => {
  const response = await api.post<ApproverAssignment>('/timesheets/approvers', data);
  return response.data;
};

export const removeApprover = async (assignmentId: string): Promise<void> => {
  await api.delete(`/timesheets/approvers/${assignmentId}`);
};
