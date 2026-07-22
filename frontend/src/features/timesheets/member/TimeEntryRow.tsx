import React, { useState } from "react";
import { MessageSquare, Trash2, Pencil, X } from "lucide-react";
import type { TimesheetEntry } from "../../../services/timesheetService";
import type { TimesheetPolicy } from "../../../services/timesheetAdminService";
import { Badge } from "../../../components/ui/Badge";

export interface TimeEntryRowProps {
  boardName: string;
  taskTitle?: string;
  entryType?: string;
  entries: TimesheetEntry[];
  weekDates: Date[];
  policy: TimesheetPolicy;
  readOnly: boolean;
  onHoursChange: (date: Date, hours: number) => void;
  onDescriptionChange: (date: Date, description: string) => void;
  onDelete: (entryId: string) => void;
  onDeleteRow?: () => void;
  onEditEntry?: (entry: TimesheetEntry) => void;
}

const formatDateKey = (date: Date): string => {
  const yyyy = date.getFullYear();
  const mm = String(date.getMonth() + 1).padStart(2, "0");
  const dd = String(date.getDate()).padStart(2, "0");
  return `${yyyy}-${mm}-${dd}`;
};

export const TimeEntryRow: React.FC<TimeEntryRowProps> = ({
  boardName,
  taskTitle,
  entryType = "task",
  entries,
  weekDates,
  policy,
  readOnly,
  onHoursChange,
  onDescriptionChange,
  onDelete,
  onDeleteRow,
  onEditEntry,
}) => {
  const [activeNoteDateKey, setActiveNoteDateKey] = useState<string | null>(
    null,
  );

  // Map entries by date key for quick lookup
  const entryMap = new Map<string, TimesheetEntry>();
  entries.forEach((e) => {
    entryMap.set(e.entry_date.split("T")[0], e);
  });

  const rowTotal = weekDates.reduce((sum, date) => {
    const key = formatDateKey(date);
    const entry = entryMap.get(key);
    return sum + (entry ? Number(entry.hours) || 0 : 0);
  }, 0);

  const getEntryTypeColor = (type?: string) => {
    switch (type) {
      case "leave":
        return "bg-purple-500";
      case "holiday":
        return "bg-emerald-500";
      case "meeting":
        return "bg-sky-500";
      case "general":
        return "bg-amber-500";
      default:
        return "bg-brand-primary";
    }
  };

  return (
    <tr className="border-b border-brand-border/40 hover:bg-brand-surface-low/30 transition-colors group">
      {/* Left column: Board badge + task name + row actions */}
      <td className="py-3 px-4 min-w-[220px] max-w-[280px]">
        <div className="flex items-center justify-between gap-2">
          <div className="flex flex-col gap-0.5 min-w-0">
            <div className="flex items-center gap-1.5 min-w-0">
              <span
                className={`w-2 h-2 rounded-full shrink-0 ${getEntryTypeColor(entryType)}`}
              />
              <span className="text-xs font-bold text-brand-text truncate">
                {boardName}
              </span>
              {entryType !== "task" && (
                <Badge
                  variant="outline"
                  size="sm"
                  className="capitalize text-[10px] py-0 px-1.5"
                >
                  {entryType}
                </Badge>
              )}
            </div>
            <div className="text-[11px] text-brand-text-muted truncate pl-3.5">
              - {taskTitle || (entryType !== "task" ? entryType : `General / ${boardName}`)}
            </div>
          </div>

          {/* Row actions on hover */}
          {!readOnly && (
            <div className="opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-1 shrink-0">
              {onDeleteRow && (
                <button
                  type="button"
                  onClick={onDeleteRow}
                  className="p-1 text-brand-text-muted hover:text-red-400 hover:bg-red-500/10 rounded transition-colors"
                  title="Delete row"
                >
                  <Trash2 size={13} />
                </button>
              )}
            </div>
          )}
        </div>
      </td>

      {/* 7 day cells */}
      {weekDates.map((date) => {
        const dateKey = formatDateKey(date);
        const entry = entryMap.get(dateKey);
        const hours = entry ? Number(entry.hours) || 0 : 0;

        const isOverMax = hours > (policy.max_hours_per_day || 24);
        const isOvertime =
          entry?.is_overtime || hours > (policy.standard_hours_per_day || 8);
        const hasDescription = Boolean(entry?.description);

        return (
          <td
            key={dateKey}
            className="p-1.5 text-center relative align-middle min-w-[64px]"
          >
            {readOnly ? (
              <div
                className={`py-1.5 px-2 rounded text-xs font-mono font-medium ${
                  hours === 0
                    ? "text-brand-text-muted/40"
                    : isOverMax
                      ? "bg-red-500/20 text-red-400 border border-red-500/40"
                      : isOvertime
                        ? "bg-amber-500/20 text-amber-300 border border-amber-500/30"
                        : "text-brand-text bg-brand-surface-low/40"
                }`}
              >
                {hours > 0 ? hours.toFixed(1) : "—"}
              </div>
            ) : (
              <div className="relative group/cell flex items-center justify-center">
                <input
                  type="number"
                  min={0}
                  max={24}
                  step={0.5}
                  value={hours > 0 ? hours : ""}
                  placeholder="—"
                  onChange={(e) => {
                    const val = parseFloat(e.target.value);
                    onHoursChange(date, isNaN(val) ? 0 : val);
                  }}
                  className={`w-14 h-8 text-center text-xs font-mono rounded bg-brand-surface border transition-colors outline-none focus:ring-1 focus:ring-brand-primary ${
                    isOverMax
                      ? "border-red-500 bg-red-500/10 text-red-400 font-bold"
                      : isOvertime
                        ? "border-amber-500/60 bg-amber-500/10 text-amber-300"
                        : hours > 0
                          ? "border-brand-primary/40 text-brand-text bg-brand-surface"
                          : "border-brand-border/60 text-brand-text-muted placeholder-brand-text-muted/40 hover:border-brand-border"
                  }`}
                />

                {/* Clear cell button when hours > 0 */}
                {hours > 0 && (
                  <button
                    type="button"
                    onClick={() => {
                      if (entry?.id && !entry.id.startsWith("temp_")) {
                        onDelete(entry.id);
                      } else {
                        onHoursChange(date, 0);
                      }
                    }}
                    className="absolute -top-1 -right-1 opacity-0 group-hover/cell:opacity-100 bg-red-500 text-white rounded-full p-0.5 shadow transition-opacity hover:bg-red-600"
                    title="Delete cell entry"
                  >
                    <X size={10} />
                  </button>
                )}

                {/* Edit modal or note trigger */}
                <button
                  type="button"
                  onClick={() => {
                    if (entry && onEditEntry) {
                      onEditEntry(entry);
                    } else {
                      setActiveNoteDateKey(
                        activeNoteDateKey === dateKey ? null : dateKey,
                      );
                    }
                  }}
                  className={`absolute top-0.5 left-0.5 p-0.5 rounded transition-opacity ${
                    hasDescription
                      ? "text-brand-primary opacity-100"
                      : "text-brand-text-muted opacity-0 group-hover/cell:opacity-100 hover:text-brand-text"
                  }`}
                  title={entry?.description || "Edit / Add note"}
                >
                  {entry && onEditEntry ? (
                    <Pencil size={9} />
                  ) : (
                    <MessageSquare size={9} />
                  )}
                </button>

                {/* Inline Description Popover */}
                {activeNoteDateKey === dateKey && (
                  <div className="absolute z-30 top-10 left-1/2 -translate-x-1/2 w-56 p-2 bg-brand-surface border border-brand-border rounded-lg shadow-xl animate-in fade-in zoom-in-95 text-left">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-[10px] font-semibold text-brand-text-muted uppercase tracking-wider">
                        Note ({dateKey})
                      </span>
                      {entry?.id && (
                        <button
                          type="button"
                          onClick={() => {
                            onDelete(entry.id);
                            setActiveNoteDateKey(null);
                          }}
                          className="text-red-400 hover:text-red-300 p-0.5 flex items-center gap-1 text-[10px]"
                          title="Delete entry"
                        >
                          <Trash2 size={12} /> Delete
                        </button>
                      )}
                    </div>
                    <textarea
                      rows={2}
                      value={entry?.description || ""}
                      placeholder="Add entry description..."
                      onChange={(e) =>
                        onDescriptionChange(date, e.target.value)
                      }
                      className="w-full text-xs p-1.5 bg-brand-surface-low border border-brand-border rounded text-brand-text outline-none focus:border-brand-primary resize-none"
                    />
                    <div className="mt-1 flex justify-end">
                      <button
                        type="button"
                        onClick={() => setActiveNoteDateKey(null)}
                        className="text-[10px] font-medium text-brand-primary hover:underline"
                      >
                        Done
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}
          </td>
        );
      })}

      {/* Right column: Row total */}
      <td className="py-3 px-4 text-right font-mono text-xs font-semibold text-brand-text shrink-0">
        {rowTotal.toFixed(1)} hrs
      </td>
    </tr>
  );
};

export default TimeEntryRow;
