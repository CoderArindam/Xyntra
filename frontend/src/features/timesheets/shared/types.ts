import type { TimesheetEntry } from '../../../services/timesheetService';

export interface BoardRowGroup {
  boardId: string;
  boardName: string;
  rows: {
    taskId?: string;
    taskTitle?: string;
    entryType: string;
    entries: TimesheetEntry[];
  }[];
}

export const ENTRY_TYPE_OPTIONS = [
  { value: 'task', label: 'Task Work Item' },
  { value: 'general', label: 'General Project Work' },
  { value: 'meeting', label: 'Meeting' },
  { value: 'leave', label: 'Leave / Time-off' },
  { value: 'holiday', label: 'Holiday' },
] as const;
