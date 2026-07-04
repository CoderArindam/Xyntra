import React, { useState, useEffect } from 'react';
import { X, Loader2, Folder, ChevronRight } from 'lucide-react';
import { type Task } from '../../../api/tasksApi';
import { useTaskStore } from '../../../store/taskStore';

interface TaskHeaderProps {
  task: Task;
  onClose: () => void;
  canEdit: boolean;
}

const TaskHeader: React.FC<TaskHeaderProps> = ({ task, onClose, canEdit }) => {
  const [isEditing, setIsEditing] = useState(false);
  const [editTitle, setEditTitle] = useState(task.title);
  const [isSaving, setIsSaving] = useState(false);
  const { updateTaskData } = useTaskStore();

  useEffect(() => {
    if (!isEditing) setEditTitle(task.title);
  }, [task.title, isEditing]);

  const handleSave = async () => {
    if (!editTitle.trim() || editTitle === task.title) {
      setIsEditing(false);
      return;
    }
    setIsSaving(true);
    await updateTaskData(task.id, { title: editTitle });
    setIsSaving(false);
    setIsEditing(false);
  };

  const handleCancel = () => {
    setEditTitle(task.title);
    setIsEditing(false);
  };

  return (
    <header className="flex justify-between items-start p-8 border-b border-brand-border bg-brand-surface-low shrink-0">
      <div className="space-y-3 flex-1 mr-4">
        <div className="flex items-center gap-2 text-brand-text-muted text-xs">
          <Folder size={15} />
          <span>Board #{task.board_id}</span>
          <ChevronRight size={15} />
          <span className="text-brand-primary">{task.task_reference}</span>
        </div>

        {isEditing ? (
          <input
            autoFocus
            value={editTitle}
            onChange={(e) => setEditTitle(e.target.value)}
            className="text-3xl font-bold text-brand-text bg-brand-surface border border-brand-border rounded-lg px-3 py-1 outline-none w-full focus:border-brand-primary"
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleSave();
              if (e.key === 'Escape') handleCancel();
            }}
          />
        ) : (
          <h1 
            className={`text-3xl font-bold text-brand-text ${canEdit ? 'cursor-pointer hover:bg-brand-surface-container rounded-lg -ml-2 px-2 py-1' : ''}`}
            onClick={() => canEdit && setIsEditing(true)}
          >
            {task.title}
          </h1>
        )}
      </div>

      <div className="flex items-center gap-2 shrink-0">
        {isEditing && (
          <>
            <button
              onClick={handleSave}
              disabled={isSaving}
              className="bg-brand-primary hover:bg-brand-primary-hover text-white px-4 py-1.5 rounded-lg text-sm flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed transition"
            >
              {isSaving && <Loader2 size={14} className="animate-spin" />}
              {isSaving ? "Saving..." : "Save"}
            </button>
            <button
              onClick={handleCancel}
              className="px-4 py-1.5 rounded-lg text-sm border border-brand-border"
            >
              Cancel
            </button>
          </>
        )}
        {!isEditing && canEdit && (
          <button
            onClick={() => setIsEditing(true)}
            className="px-4 py-1.5 rounded-lg text-sm border border-brand-border hover:bg-brand-surface-container transition"
          >
            Edit
          </button>
        )}
        <button
          onClick={onClose}
          className="p-1 rounded bg-brand-surface-low hover:bg-brand-bg transition"
        >
          <X size={20} />
        </button>
      </div>
    </header>
  );
};

export default TaskHeader;
