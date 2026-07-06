import React, { useState } from 'react';
import { Loader2 } from 'lucide-react';
import { useTaskStore } from '../../../store/taskStore';
import { useUiStore } from '../../../store/uiStore';
import StatusSelector from '../../../components/shared/StatusSelector';
import AssigneeSelector from '../../../components/shared/AssigneeSelector';
import PrioritySelector from '../../../components/shared/PrioritySelector';
import DueDatePicker from '../../../components/shared/DueDatePicker';
import Modal from '../../../components/common/Modal';

const CreateTaskModal: React.FC = () => {
  const { isCreateTaskModalOpen, closeCreateTaskModal } = useUiStore();
  const { getBoardMembersList, getColumnsList, createNewTask, isSubmitting } = useTaskStore();
  const boardMembers = getBoardMembersList();
  const columns = getColumnsList();

  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [priority, setPriority] = useState('Medium');
  const [assigneeId, setAssigneeId] = useState<number | null>(null);
  const [dueDate, setDueDate] = useState<string | null>(null);
  const [columnId, setColumnId] = useState<number | undefined>(undefined);

  // set initial columnId when modal opens if not set
  React.useEffect(() => {
    if (isCreateTaskModalOpen && columns.length > 0 && columnId === undefined) {
      setColumnId(columns[0].id);
    }
  }, [isCreateTaskModalOpen, columns, columnId]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || columnId === undefined) return;
    
    await createNewTask({
      title,
      description,
      priority,
      assigned_to: assigneeId || undefined,
      due_date: dueDate,
      column_id: columnId,
    });
    
    setTitle('');
    setDescription('');
    setPriority('Medium');
    setAssigneeId(null);
    setDueDate(null);
    setColumnId(columns[0]?.id);
    closeCreateTaskModal();
  };

  return (
    <Modal 
      isOpen={isCreateTaskModalOpen} 
      onClose={closeCreateTaskModal} 
      title="Create Task" 
      width="max-w-2xl"
    >
      <form onSubmit={handleSubmit} className="flex flex-col -mx-6 -my-6">
        <div className="p-6 space-y-6">
          <div>
            <input
              autoFocus
              type="text"
              placeholder="Task title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full text-xl font-semibold bg-brand-surface border border-brand-border rounded-lg px-4 py-2 outline-none focus:border-brand-primary placeholder:font-normal"
            />
          </div>
          
          <div>
            <textarea
              rows={4}
              placeholder="Add a detailed description..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full bg-brand-surface border border-brand-border rounded-lg px-4 py-3 text-sm outline-none resize-none focus:border-brand-primary"
            />
          </div>

          <div className="grid grid-cols-2 gap-6 bg-brand-surface-low border border-brand-border rounded-lg p-5">
            <div>
              <p className="text-xs font-semibold text-brand-text-muted mb-2 uppercase tracking-wider">Status</p>
              <StatusSelector 
                columnId={columnId} 
                columns={columns} 
                onChange={(newColumnId: any) => setColumnId(newColumnId)} 
              />
            </div>

            <div>
              <p className="text-xs font-semibold text-brand-text-muted mb-2 uppercase tracking-wider">Assignee</p>
              <AssigneeSelector 
                assigneeId={assigneeId} 
                users={boardMembers} 
                onChange={(newAssignee: any) => setAssigneeId(newAssignee)} 
              />
            </div>

            <div>
              <p className="text-xs font-semibold text-brand-text-muted mb-2 uppercase tracking-wider">Priority</p>
              <PrioritySelector 
                priority={priority} 
                onChange={(newPriority: any) => setPriority(newPriority)} 
              />
            </div>

            <div>
              <p className="text-xs font-semibold text-brand-text-muted mb-2 uppercase tracking-wider">Due Date</p>
              <DueDatePicker 
                dueDate={dueDate} 
                onChange={(newDueDate: any) => setDueDate(newDueDate)} 
              />
            </div>
          </div>
        </div>
        
        <div className="p-6 border-t border-brand-border bg-brand-surface-low flex justify-end gap-3 mt-auto rounded-b-lg">
          <button
            type="button"
            onClick={closeCreateTaskModal}
            className="px-4 py-2 rounded-lg text-sm border border-brand-border hover:bg-brand-surface transition"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={isSubmitting || !title.trim()}
            className="bg-brand-primary hover:bg-brand-primary-hover text-white px-6 py-2 rounded-lg text-sm font-medium flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed transition"
          >
            {isSubmitting && <Loader2 size={16} className="animate-spin" />}
            {isSubmitting ? "Creating..." : "Create Task"}
          </button>
        </div>
      </form>
    </Modal>
  );
};

export default CreateTaskModal;
