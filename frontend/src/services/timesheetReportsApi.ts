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

export const getOrgSummaryReport = async (weeksBack: number = 12): Promise<TimesheetOrgSummaryReport[]> => {
  const response = await api.get<TimesheetOrgSummaryReport[]>('/timesheets/reports/org-summary', {
    params: { weeks_back: weeksBack },
  });
  return response.data;
};
