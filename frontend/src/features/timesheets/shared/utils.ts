import type { TimesheetDetail } from '../../../services/timesheetService';
import type { BoardRowGroup } from './types';

/** Build week Date objects from a week_start_date string. */
export function buildWeekDates(weekStartDate: string): Date[] {
  const dates: Date[] = [];
  const start = new Date(weekStartDate + 'T00:00:00');
  for (let i = 0; i < 7; i++) {
    const d = new Date(start);
    d.setDate(start.getDate() + i);
    dates.push(d);
  }
  return dates;
}

/** Format a Date to a YYYY-MM-DD string. */
export function toDateStr(date: Date): string {
  const yyyy = date.getFullYear();
  const mm = String(date.getMonth() + 1).padStart(2, '0');
  const dd = String(date.getDate()).padStart(2, '0');
  return `${yyyy}-${mm}-${dd}`;
}

/** Format week_start_date for top week tabs (e.g. "July 20-26" or "July 27-Aug 2"). */
export function formatWeekTabLabel(weekStartDate: string): string {
  if (!weekStartDate) return '';
  const start = new Date(weekStartDate + 'T00:00:00');
  const end = new Date(start);
  end.setDate(start.getDate() + 6);

  const startMonth = start.toLocaleDateString('en-US', { month: 'short' });
  const endMonth = end.toLocaleDateString('en-US', { month: 'short' });

  if (startMonth === endMonth) {
    return `${startMonth} ${start.getDate()}-${end.getDate()}`;
  }
  return `${startMonth} ${start.getDate()}-${endMonth} ${end.getDate()}`;
}

/** Format week_start_date for main header pill (e.g. "Week of July 20 - July 26, 2026"). */
export function formatWeekHeaderLabel(weekStartDate: string): string {
  if (!weekStartDate) return '';
  const start = new Date(weekStartDate + 'T00:00:00');
  const end = new Date(start);
  end.setDate(start.getDate() + 6);

  const startMonth = start.toLocaleDateString('en-US', { month: 'long' });
  const endMonth = end.toLocaleDateString('en-US', { month: 'long' });
  const year = start.getFullYear();

  if (startMonth === endMonth) {
    return `Week of ${startMonth} ${start.getDate()} - ${end.getDate()}, ${year}`;
  }
  return `Week of ${startMonth} ${start.getDate()} - ${endMonth} ${end.getDate()}, ${year}`;
}

/** Group timesheet entries by board and work item. */
export function groupEntriesByBoard(detail: TimesheetDetail): BoardRowGroup[] {
  const boardGroupsMap = new Map<string, BoardRowGroup>();

  detail.entries.forEach((entry) => {
    const bId = entry.board_id || 'general';
    const bName = entry.board_name || (bId === 'general' ? 'General & Time-off' : 'Unknown Board');

    if (!boardGroupsMap.has(bId)) {
      boardGroupsMap.set(bId, { boardId: bId, boardName: bName, rows: [] });
    }

    const group = boardGroupsMap.get(bId)!;
    const rowKey = `${entry.task_id || 'none'}_${entry.entry_type}`;
    let row = group.rows.find((r) => `${r.taskId || 'none'}_${r.entryType}` === rowKey);

    if (!row) {
      row = {
        taskId: entry.task_id || undefined,
        taskTitle: entry.task_title || undefined,
        entryType: entry.entry_type,
        entries: [],
      };
      group.rows.push(row);
    }
    row.entries.push(entry);
  });

  return Array.from(boardGroupsMap.values());
}
