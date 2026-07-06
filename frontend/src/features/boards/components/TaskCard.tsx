import React from 'react';
import { Trash2, UserRound, CalendarClock } from 'lucide-react';
import { type Task, type Column } from '../../../services/tasksApi';
import { type User } from '../../../services/usersApi';
import { UserAvatar } from '../../../components/common/UserAvatar';
import { formatUserName } from '../../../utils/userHelpers';

interface TaskCardProps {
  task: Task & { board_name?: string; column_name?: string };
  columns: Column[];
  users: User[];
  onStatusChange: (newColumnId: number) => void;
  onDelete: () => void;
  onAssigneeChange: (assignedTo: number | null) => void;
  onOpen: () => void;
  canEdit: boolean;
  canReassign: boolean;
  variant?: 'board' | 'list';
}

export const TaskCard: React.FC<TaskCardProps> = React.memo(({
  task,
  columns,
  users,
  onStatusChange,
  onDelete,
  onAssigneeChange,
  onOpen,
  canEdit,
  canReassign,
  variant = 'board',
}) => {
  const assignee = users.find((u) => u.id === task.assigned_to);

  const handleAssigneeSelect = (e: React.ChangeEvent<HTMLSelectElement>) => {
    e.stopPropagation();

    const val = e.target.value;

    onAssigneeChange(val === "" ? null : parseInt(val, 10));
  };

  const currentColumn = columns.find(c => c.id === task.column_id);
  const isCompleted = currentColumn?.is_completed || false;

  let dueDateBadge = null;
  if (task.due_date) {
    const due = new Date(task.due_date);
    due.setHours(0,0,0,0);
    const now = new Date();
    now.setHours(0,0,0,0);
    const diffDays = Math.round((due.getTime() - now.getTime()) / (1000 * 3600 * 24));
    
    let colorClass = "bg-brand-surface-low text-brand-text-muted";
    let text = "Due on " + due.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });

    if (!isCompleted) {
      if (diffDays < 0) {
        colorClass = "bg-red-50 text-red-600 font-semibold";
        text = `Overdue by ${Math.abs(diffDays)} day${Math.abs(diffDays) !== 1 ? 's' : ''}`;
      } else if (diffDays === 0) {
        colorClass = "bg-orange-50 text-orange-600 font-semibold";
        text = "Due today";
      } else if (diffDays === 1) {
        colorClass = "bg-yellow-50 text-yellow-600 font-semibold";
        text = "Due tomorrow";
      } else if (diffDays <= 7) {
        text = `Due in ${diffDays} days`;
      }
    } else {
      colorClass = "bg-brand-surface-low text-brand-text-muted opacity-70";
    }

    dueDateBadge = (
      <span className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs ${colorClass}`}>
        <CalendarClock size={14} />
        {text}
      </span>
    );
  }

  if (variant === 'list') {
    return (
      <div
        className="group bg-brand-surface rounded-xl border border-brand-border p-4 flex items-center justify-between shadow-sm hover:shadow-md transition cursor-pointer gap-4"
        onClick={onOpen}
      >
        <div className="flex flex-col flex-1 gap-1">
          <div className="flex items-center gap-2">
            <h4 className="text-base font-semibold text-brand-text leading-tight">
              {task.title}
            </h4>
            {task.priority && (
              <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase ${
                task.priority === "High" ? "bg-red-50 text-red-600"
                  : task.priority === "Medium" ? "bg-orange-50 text-orange-600"
                  : "bg-green-50 text-green-600"
              }`}>
                {task.priority}
              </span>
            )}
          </div>
          <div className="text-xs text-brand-text-muted flex items-center gap-2">
            {task.board_name && <span className="font-medium">{task.board_name}</span>}
            {task.board_name && <span>•</span>}
            {task.column_name && <span>{task.column_name}</span>}
            {!task.column_name && currentColumn && <span>{currentColumn.name}</span>}
          </div>
        </div>

        <div className="flex items-center gap-4 shrink-0">
          {dueDateBadge}
          <div className="shrink-0">
            {assignee ? (
              <UserAvatar user={assignee} size="md" />
            ) : (
              <div className="w-8 h-8 rounded-full bg-brand-surface-low border border-brand-border flex items-center justify-center overflow-hidden">
                <UserRound size={15} className="text-brand-outline" />
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div
      className="group bg-brand-surface rounded-3xl border border-brand-border p-5 flex flex-col gap-4 shadow-sm hover:-translate-y-0.5 hover:shadow-md transition cursor-pointer"
      onClick={onOpen}
    >
      <div className="flex justify-between items-start gap-3">
        <h4 className="text-base font-semibold text-brand-text leading-tight">
          {task.title}
        </h4>

        {canEdit && (
          <button
            onClick={(e) => { e.stopPropagation(); onDelete(); }}
            className="opacity-0 group-hover:opacity-100 bg-brand-surface-low text-brand-outline hover:text-brand-error w-8 h-8 rounded-full flex items-center justify-center transition"
          >
            <Trash2 size={16} />
          </button>
        )}
      </div>

      {task.description && (
        <p className="text-sm text-brand-text-muted leading-relaxed">
          {task.description}
        </p>
      )}

      {dueDateBadge && (
        <div className="flex">
          {dueDateBadge}
        </div>
      )}

      <div className="flex justify-between items-center pt-4 border-t border-brand-border">
        {task.priority && (
          <span
            className={`px-3 py-1 rounded-full text-xs font-semibold ${
              task.priority === "High"
                ? "bg-red-50 text-red-600"
                : task.priority === "Medium"
                  ? "bg-orange-50 text-orange-600"
                  : "bg-green-50 text-green-600"
            }`}
          >
            {task.priority} Priority
          </span>
        )}

        {/* Assignee Avatar Dropdown */}

        <div className="relative">
          {canReassign && (
            <select
              value={task.assigned_to ?? ""}
              onChange={handleAssigneeSelect}
              onClick={(e) => e.stopPropagation()}
              className="absolute inset-0 opacity-0 cursor-pointer w-full h-full"
            >
              <option value="">Unassigned</option>

              {users.map((u) => (
                <option key={u.id} value={u.id}>
                  {formatUserName(u)}
                </option>
              ))}
            </select>
          )}

          <div className="relative">
            {assignee ? (
              <UserAvatar user={assignee} size="md" />
            ) : (
              <div className="w-8 h-8 rounded-full bg-brand-surface-low border border-brand-border flex items-center justify-center overflow-hidden cursor-pointer">
                <UserRound size={15} className="text-brand-outline" />
              </div>
            )}
          </div>
        </div>
      </div>

      {assignee && (
        <p className="text-xs text-brand-text-muted">
          Assigned to:{" "}
          <span className="font-medium text-brand-text">{formatUserName(assignee)}</span>
        </p>
      )}

      <div className="flex flex-wrap gap-2">
        {canEdit && columns.map(
          (col) =>
            col.id !== task.column_id && (
              <button
                key={col.id}
                onClick={(e) => { e.stopPropagation(); onStatusChange(col.id); }}
                className="text-xs px-2 py-1 rounded-lg bg-brand-surface-low hover:bg-brand-surface-container"
              >
                Move {col.name}
              </button>
            ),
        )}
      </div>
    </div>
  );
});

TaskCard.displayName = 'TaskCard';

export default TaskCard;
