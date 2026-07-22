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
