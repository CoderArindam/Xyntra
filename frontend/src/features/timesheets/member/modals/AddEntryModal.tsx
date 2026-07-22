import React from 'react';
import { Loader2 } from 'lucide-react';
import { type Task } from '../../../../services/tasksApi';
import { ENTRY_TYPE_OPTIONS } from '../../shared/types';
import { Button } from '../../../../components/ui/Button';
import { Modal } from '../../../../components/common/Modal';

interface AddEntryModalProps {
  boardName: string;
  onClose: () => void;
  selectedEntryType: string;
  onEntryTypeChange: (val: string) => void;
  selectedTaskId: string;
  onTaskChange: (val: string) => void;
  boardTasks: Task[];
  loadingTasks: boolean;
  onConfirm: () => void;
}

export const AddEntryModal: React.FC<AddEntryModalProps> = ({
  boardName,
  onClose,
  selectedEntryType,
  onEntryTypeChange,
  selectedTaskId,
  onTaskChange,
  boardTasks,
  loadingTasks,
  onConfirm,
}) => (
  <Modal isOpen onClose={onClose} title={`Add Entry to ${boardName}`}>
    <div className="space-y-4">
      <div>
        <label className="block text-xs font-medium text-brand-text-muted mb-1">
          Entry Category / Type
        </label>
        <select
          value={selectedEntryType}
          onChange={(e) => onEntryTypeChange(e.target.value)}
          className="w-full bg-brand-surface border border-brand-border rounded-lg px-3 py-2 text-sm text-brand-text focus:outline-none focus:border-brand-primary"
        >
          {ENTRY_TYPE_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>
      </div>

      {selectedEntryType === 'task' && (
        <div>
          <label className="block text-xs font-medium text-brand-text-muted mb-1">
            Select Task
          </label>
          {loadingTasks ? (
            <div className="flex items-center gap-2 text-xs text-brand-text-muted py-2">
              <Loader2 size={14} className="animate-spin" /> Loading board tasks...
            </div>
          ) : (
            <select
              value={selectedTaskId}
              onChange={(e) => onTaskChange(e.target.value)}
              className="w-full bg-brand-surface border border-brand-border rounded-lg px-3 py-2 text-sm text-brand-text focus:outline-none focus:border-brand-primary"
            >
              <option value="">-- General (No Task Linked) --</option>
              {boardTasks.map((t) => (
                <option key={t.id} value={String(t.id)}>
                  {t.task_reference} - {t.title}
                </option>
              ))}
            </select>
          )}
        </div>
      )}

      <div className="flex justify-end gap-2 pt-4">
        <Button variant="ghost" size="sm" onClick={onClose}>
          Cancel
        </Button>
        <Button variant="primary" size="sm" onClick={onConfirm}>
          Add Row
        </Button>
      </div>
    </div>
  </Modal>
);
