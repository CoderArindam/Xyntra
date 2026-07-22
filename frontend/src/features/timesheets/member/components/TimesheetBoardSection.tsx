import React from 'react';
import { Building, Plus } from 'lucide-react';
import { type TimesheetPolicy } from '../../../../services/timesheetAdminService';
import { type TimesheetEntry } from '../../../../services/timesheetService';
import { TimeEntryRow } from '../TimeEntryRow';
import type { BoardRowGroup } from '../../shared/types';

interface TimesheetBoardSectionProps {
  group: BoardRowGroup;
  weekDates: Date[];
  policy: TimesheetPolicy;
  readOnly: boolean;
  onHoursChange: (boardId: string, taskId: string | undefined, entryType: string, date: Date, hours: number) => void;
  onDescriptionChange: (boardId: string, taskId: string | undefined, entryType: string, date: Date, description: string) => void;
  onDelete: (entryId: string) => void;
  onDeleteRow?: (entries: TimesheetEntry[]) => void;
  onEditEntry?: (entry: TimesheetEntry) => void;
  onAddEntry: (boardId: string, boardName: string) => void;
}

export const TimesheetBoardSection: React.FC<TimesheetBoardSectionProps> = ({
  group,
  weekDates,
  policy,
  readOnly,
  onHoursChange,
  onDescriptionChange,
  onDelete,
  onDeleteRow,
  onEditEntry,
  onAddEntry,
}) => {
  const groupTotalHours = group.rows.reduce(
    (sum, row) => sum + row.entries.reduce((rSum, e) => rSum + (Number(e.hours) || 0), 0),
    0
  );

  return (
    <React.Fragment>
      {/* Board Section Header */}
      <tr className="bg-brand-surface-low/80 border-y border-brand-border/60">
        <td colSpan={9} className="py-2 px-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-xs font-bold text-brand-text">
              <Building size={14} className="text-brand-primary" />
              <span>{group.boardName}</span>
              <span className="text-brand-text-muted font-normal text-[11px]">
                ({groupTotalHours.toFixed(1)} hrs)
              </span>
            </div>

            {!readOnly && (
              <button
                type="button"
                onClick={() => onAddEntry(group.boardId, group.boardName)}
                className="flex items-center gap-1 text-[11px] font-medium text-brand-primary hover:text-brand-primary-hover transition-colors px-2 py-1 rounded hover:bg-brand-primary/10"
              >
                <Plus size={12} /> Add Entry
              </button>
            )}
          </div>
        </td>
      </tr>

      {/* Rows for this Board */}
      {group.rows.map((row, idx) => (
        <TimeEntryRow
          key={`${group.boardId}_${row.taskId || 'none'}_${row.entryType}_${idx}`}
          boardName={group.boardName}
          taskTitle={row.taskTitle}
          entryType={row.entryType}
          entries={row.entries}
          weekDates={weekDates}
          policy={policy}
          readOnly={readOnly}
          onHoursChange={(date, hrs) =>
            onHoursChange(group.boardId, row.taskId, row.entryType, date, hrs)
          }
          onDescriptionChange={(date, desc) =>
            onDescriptionChange(group.boardId, row.taskId, row.entryType, date, desc)
          }
          onDelete={onDelete}
          onDeleteRow={onDeleteRow ? () => onDeleteRow(row.entries) : undefined}
          onEditEntry={onEditEntry}
        />
      ))}
    </React.Fragment>
  );
};
