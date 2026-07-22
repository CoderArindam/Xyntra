import React, { useState, useEffect } from 'react';
import { Loader2, Trash2 } from 'lucide-react';
import { type Board } from '../../../../services/boardsApi';
import { type Task } from '../../../../services/tasksApi';
import { type TimesheetEntry } from '../../../../services/timesheetService';
import { ENTRY_TYPE_OPTIONS } from '../../shared/types';
import { toDateStr } from '../../shared/utils';
import { Button } from '../../../../components/ui/Button';
import { Modal } from '../../../../components/common/Modal';
import { TaskSearchSelector } from '../../shared/TaskSearchSelector';

interface EditEntryModalProps {
  isOpen: boolean;
  onClose: () => void;
  entry: TimesheetEntry | null;
  accessibleBoards: Board[];
  boardTasksMap: Record<string, Task[]>;
  loadingTasks: boolean;
  onLoadTasks: (boardId: string) => Promise<void>;
  weekDates: Date[];
  onSave: (data: {
    entryId?: string;
    boardId?: string;
    taskId?: string;
    entryDate: string;
    hours: number;
    entryType: string;
    description?: string;
  }) => void;
  onDelete: (entryId: string) => void;
}

export const EditEntryModal: React.FC<EditEntryModalProps> = ({
  isOpen,
  onClose,
  entry,
  accessibleBoards,
  boardTasksMap,
  loadingTasks,
  onLoadTasks,
  weekDates,
  onSave,
  onDelete,
}) => {
  const [boardId, setBoardId] = useState<string>('general');
  const [entryType, setEntryType] = useState<string>('task');
  const [taskId, setTaskId] = useState<string>('');
  const [entryDate, setEntryDate] = useState<string>('');
  const [hours, setHours] = useState<string>('8.0');
  const [description, setDescription] = useState<string>('');

  useEffect(() => {
    if (entry) {
      const bId = entry.board_id ? String(entry.board_id) : 'general';
      setBoardId(bId);
      setEntryType(entry.entry_type || 'task');
      setTaskId(entry.task_id ? String(entry.task_id) : '');
      setEntryDate(entry.entry_date ? entry.entry_date.split('T')[0] : '');
      setHours(entry.hours ? String(entry.hours) : '0.0');
      setDescription(entry.description || '');
      if (bId !== 'general') {
        onLoadTasks(bId);
      }
    }
  }, [entry]);

  if (!isOpen || !entry) return null;

  const handleBoardChange = async (newBoardId: string) => {
    setBoardId(newBoardId);
    setTaskId('');
    if (newBoardId !== 'general') {
      await onLoadTasks(newBoardId);
    }
  };

  const handleSave = () => {
    const numHours = parseFloat(hours) || 0;
    onSave({
      entryId: entry.id,
      boardId: boardId === 'general' ? undefined : boardId,
      taskId: entryType === 'task' && taskId ? taskId : undefined,
      entryDate,
      hours: numHours,
      entryType,
      description,
    });
    onClose();
  };

  const handleDelete = () => {
    if (entry.id) {
      onDelete(entry.id);
      onClose();
    }
  };

  const tasksForBoard = boardTasksMap[boardId] || [];

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Edit Time Entry">
      <div className="space-y-4">
        {/* Board Selection */}
        <div>
          <label className="block text-xs font-semibold text-brand-text mb-1">
            Project / Board
          </label>
          <select
            value={boardId}
            onChange={(e) => handleBoardChange(e.target.value)}
            className="w-full bg-brand-surface border border-brand-border rounded-lg px-3 py-2 text-sm text-brand-text focus:outline-none focus:border-brand-primary"
          >
            <option value="general">General / Non-Project</option>
            {accessibleBoards.map((b) => (
              <option key={b.id} value={String(b.id)}>
                {b.name}
              </option>
            ))}
          </select>
        </div>

        {/* Entry Category */}
        <div>
          <label className="block text-xs font-semibold text-brand-text mb-1">
            Entry Type / Category
          </label>
          <select
            value={entryType}
            onChange={(e) => setEntryType(e.target.value)}
            className="w-full bg-brand-surface border border-brand-border rounded-lg px-3 py-2 text-sm text-brand-text focus:outline-none focus:border-brand-primary"
          >
            {ENTRY_TYPE_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        {/* Task Selection */}
        {entryType === 'task' && boardId !== 'general' && (
          <div>
            <label className="block text-xs font-semibold text-brand-text mb-1">
              Work Item / Task (Assigned to You)
            </label>
            <TaskSearchSelector
              value={taskId}
              boardId={boardId}
              onChange={(tId) => setTaskId(tId)}
              placeholder="Search your assigned tasks on this board..."
            />
          </div>
        )}

        {/* Date & Hours Grid */}
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-semibold text-brand-text mb-1">
              Date *
            </label>
            <select
              value={entryDate}
              onChange={(e) => setEntryDate(e.target.value)}
              className="w-full bg-brand-surface border border-brand-border rounded-lg px-3 py-2 text-sm text-brand-text focus:outline-none focus:border-brand-primary"
            >
              {weekDates.map((d) => {
                const dStr = toDateStr(d);
                const label = d.toLocaleDateString('en-US', {
                  weekday: 'short',
                  month: 'short',
                  day: 'numeric',
                });
                return (
                  <option key={dStr} value={dStr}>
                    {label}
                  </option>
                );
              })}
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-brand-text mb-1">
              Hours Spent *
            </label>
            <input
              type="number"
              step="0.5"
              min="0.0"
              max="24"
              value={hours}
              onChange={(e) => setHours(e.target.value)}
              className="w-full bg-brand-surface border border-brand-border rounded-lg px-3 py-2 text-sm text-brand-text focus:outline-none focus:border-brand-primary font-mono"
            />
          </div>
        </div>

        {/* Description / Note */}
        <div>
          <label className="block text-xs font-semibold text-brand-text mb-1">
            Work Description / Notes
          </label>
          <textarea
            rows={2}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Add details about work done..."
            className="w-full bg-brand-surface border border-brand-border rounded-lg p-2 text-xs text-brand-text focus:outline-none focus:border-brand-primary resize-none"
          />
        </div>

        {/* Action Buttons */}
        <div className="flex items-center justify-between pt-4 border-t border-brand-border/60">
          <Button
            variant="danger"
            size="sm"
            onClick={handleDelete}
            className="flex items-center gap-1.5"
          >
            <Trash2 size={14} /> Delete Entry
          </Button>

          <div className="flex items-center gap-2">
            <Button variant="ghost" size="sm" onClick={onClose}>
              Cancel
            </Button>
            <Button variant="primary" size="sm" onClick={handleSave}>
              Save Changes
            </Button>
          </div>
        </div>
      </div>
    </Modal>
  );
};
