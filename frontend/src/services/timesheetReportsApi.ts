import api from '../lib/axios';

export interface TimesheetOrgSummaryReport {
  org_id: string;
  week_start_date: string;
  total_members_who_submitted: number;
  total_timesheets_submitted: number;
  total_timesheets_approved: number;
  total_timesheets_rejected: number;
  total_timesheets_pending: number;
  total_hours_logged: number;
  avg_hours_per_member: number;
  compliance_rate: number;
}

export interface TimesheetBoardHoursReport {
  board_id: string;
  board_name: string;
  org_id: string;
  week_start_date: string;
  total_hours_logged: number;
  member_count: number;
}

export interface TimesheetMemberComplianceReport {
  user_id: string;
  org_id: string;
  display_name: string;
  email: string;
  week_start_date: string;
  status: string;
  total_hours: number;
  is_on_time: boolean;
}

export const getOrgSummaryReport = async (weeksBack: number = 12): Promise<TimesheetOrgSummaryReport[]> => {
  const response = await api.get<TimesheetOrgSummaryReport[]>('/timesheets/reports/org-summary', {
    params: { weeks_back: weeksBack },
  });
  return response.data;
};

export const getBoardHoursReport = async (
  weeksBack: number = 8,
  boardId?: string
): Promise<TimesheetBoardHoursReport[]> => {
  const response = await api.get<TimesheetBoardHoursReport[]>('/timesheets/reports/board-hours', {
    params: { weeks_back: weeksBack, board_id: boardId },
  });
  return response.data;
};

export const getMemberComplianceReport = async (): Promise<TimesheetMemberComplianceReport[]> => {
  const response = await api.get<TimesheetMemberComplianceReport[]>('/timesheets/reports/member-compliance');
  return response.data;
};
