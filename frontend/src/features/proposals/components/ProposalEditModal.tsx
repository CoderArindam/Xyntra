import React, { useState, useEffect } from 'react';
import Modal from '../../../components/common/Modal';
import type { TaskProposal } from '../../../services/taskProposals';
import type { Board } from '../../../services/boardsApi';
import { getUsers, type User } from '../../../services/usersApi';
import { Check, Calendar, Flag, User as UserIcon, Layout } from 'lucide-react';

interface ProposalEditModalProps {
  isOpen: boolean;
  onClose: () => void;
  proposal: TaskProposal | null;
  boards: Board[];
  onSubmit: (
    id: string,
    data: {
      title: string;
      description: string;
      suggested_assignee_id: number | null;
      board_id: number | null;
      priority: string | null;
      due_date: string | null;
    }
  ) => Promise<void>;
}

export const ProposalEditModal: React.FC<ProposalEditModalProps> = ({
  isOpen,
  onClose,
  proposal,
  boards,
  onSubmit,
}) => {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [assigneeId, setAssigneeId] = useState<number | null>(null);
  const [boardId, setBoardId] = useState<number | null>(null);
  const [priority, setPriority] = useState<string>('Medium');
  const [dueDate, setDueDate] = useState<string>('');
  const [users, setUsers] = useState<User[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    getUsers().then(setUsers).catch(console.error);
  }, []);

  useEffect(() => {
    if (proposal) {
      setTitle(proposal.title || '');
      setDescription(proposal.description || '');
      setAssigneeId(proposal.suggested_assignee_id || null);
      setBoardId(proposal.board_id || null);

      // 1. Normalize priority to match select option values ('Low', 'Medium', 'High', 'Urgent')
      let p = (proposal.priority || 'Medium').trim();
      if (p) {
        p = p.charAt(0).toUpperCase() + p.slice(1).toLowerCase();
      }
      if (!['Low', 'Medium', 'High', 'Urgent'].includes(p)) {
        p = 'Medium';
      }
      setPriority(p);

      // 2. Format due_date safely as YYYY-MM-DD for HTML5 date input
      let formattedDate = '';
      if (proposal.due_date) {
        try {
          const d = new Date(proposal.due_date);
          if (!isNaN(d.getTime())) {
            formattedDate = d.toISOString().split('T')[0];
          } else {
            formattedDate = proposal.due_date.split('T')[0].split(' ')[0];
          }
        } catch {
          formattedDate = (proposal.due_date || '').split('T')[0].split(' ')[0];
        }
      }
      setDueDate(formattedDate);
      setErrorMessage(null);
    }
  }, [proposal]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!proposal) return;

    if (!title.trim()) {
      setErrorMessage('Task title is required');
      return;
    }

    if (!boardId) {
      setErrorMessage('Target board selection is required');
      return;
    }

    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      await onSubmit(proposal.id, {
        title: title.trim(),
        description: description.trim(),
        suggested_assignee_id: assigneeId,
        board_id: boardId,
        priority: priority,
        due_date: dueDate || null,
      });
      onClose();
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      const msg = typeof detail === 'object' && detail?.message ? detail.message : (detail || 'Failed to edit and approve proposal');
      setErrorMessage(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!proposal) return null;

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Edit & Approve Proposal" width="max-w-xl">
      <form onSubmit={handleSubmit} className="space-y-4">
        {errorMessage && (
          <div className="p-3 text-xs bg-red-500/10 border border-red-500/20 rounded-lg text-red-400">
            {errorMessage}
          </div>
        )}

        {/* Board Selection */}
        <div>
          <label className="block text-xs font-semibold text-brand-text mb-1 flex items-center gap-1.5">
            <Layout size={13} className="text-brand-text-muted" />
            Target Board <span className="text-red-400">*</span>
          </label>
          <select
            value={boardId || ''}
            onChange={(e) => setBoardId(e.target.value ? Number(e.target.value) : null)}
            className="w-full px-3 py-2 text-sm bg-brand-surface-low border border-brand-border rounded-lg text-brand-text focus:outline-none focus:border-brand-primary"
            required
          >
            <option value="">Select a target board…</option>
            {boards.map((b) => (
              <option key={b.id} value={b.id}>
                {b.name} ({b.project_key})
              </option>
            ))}
          </select>
        </div>

        {/* Title */}
        <div>
          <label className="block text-xs font-semibold text-brand-text mb-1">
            Task Title <span className="text-red-400">*</span>
          </label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="w-full px-3 py-2 text-sm bg-brand-surface-low border border-brand-border rounded-lg text-brand-text focus:outline-none focus:border-brand-primary"
            placeholder="Enter actionable task title"
            required
          />
        </div>

        {/* Description */}
        <div>
          <label className="block text-xs font-semibold text-brand-text mb-1">
            Description
          </label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={3}
            className="w-full px-3 py-2 text-sm bg-brand-surface-low border border-brand-border rounded-lg text-brand-text focus:outline-none focus:border-brand-primary resize-y"
            placeholder="Contextual task description from meeting transcript"
          />
        </div>

        {/* Priority, Due Date & Assignee Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {/* Priority */}
          <div>
            <label className="block text-xs font-semibold text-brand-text mb-1 flex items-center gap-1.5">
              <Flag size={13} className="text-brand-text-muted" />
              Priority
            </label>
            <select
              value={priority}
              onChange={(e) => setPriority(e.target.value)}
              className="w-full px-3 py-2 text-sm bg-brand-surface-low border border-brand-border rounded-lg text-brand-text focus:outline-none focus:border-brand-primary"
            >
              <option value="Low">Low</option>
              <option value="Medium">Medium</option>
              <option value="High">High</option>
              <option value="Urgent">Urgent</option>
            </select>
          </div>

          {/* Due Date */}
          <div>
            <label className="block text-xs font-semibold text-brand-text mb-1 flex items-center gap-1.5">
              <Calendar size={13} className="text-brand-text-muted" />
              Due Date
            </label>
            <input
              type="date"
              value={dueDate}
              onChange={(e) => setDueDate(e.target.value)}
              className="w-full px-3 py-2 text-sm bg-brand-surface-low border border-brand-border rounded-lg text-brand-text focus:outline-none focus:border-brand-primary"
            />
          </div>

          {/* Assignee */}
          <div>
            <label className="block text-xs font-semibold text-brand-text mb-1 flex items-center gap-1.5">
              <UserIcon size={13} className="text-brand-text-muted" />
              Assignee
            </label>
            <select
              value={assigneeId || ''}
              onChange={(e) => setAssigneeId(e.target.value ? Number(e.target.value) : null)}
              className="w-full px-3 py-2 text-sm bg-brand-surface-low border border-brand-border rounded-lg text-brand-text focus:outline-none focus:border-brand-primary"
            >
              <option value="">Unassigned</option>
              {users.map((u) => {
                const name = [u.first_name, u.last_name].filter(Boolean).join(' ') || u.email;
                return (
                  <option key={u.id} value={u.id}>
                    {name}
                  </option>
                );
              })}
            </select>
          </div>
        </div>

        {proposal.source_transcript_quote && (
          <div className="p-3 rounded-lg bg-brand-surface-low/60 border border-brand-border/40 text-xs italic text-brand-text-muted">
            <span className="font-semibold non-italic text-brand-text block mb-1">
              Grounding Quote:
            </span>
            "{proposal.source_transcript_quote}"
          </div>
        )}

        <div className="flex items-center justify-end gap-3 pt-3 border-t border-brand-border">
          <button
            type="button"
            onClick={onClose}
            disabled={isSubmitting}
            className="px-4 py-2 text-xs font-medium text-brand-text-muted hover:text-brand-text hover:bg-brand-surface-low rounded-lg transition-colors"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={isSubmitting || !boardId}
            className="flex items-center gap-1.5 px-4 py-2 text-xs font-semibold text-white bg-brand-primary hover:bg-brand-primary/90 rounded-lg shadow-sm transition-colors disabled:opacity-50"
          >
            {isSubmitting ? (
              <span className="animate-spin rounded-full h-3.5 w-3.5 border-b-2 border-white"></span>
            ) : (
              <Check className="w-3.5 h-3.5" />
            )}
            Save & Approve Task
          </button>
        </div>
      </form>
    </Modal>
  );
};

export default ProposalEditModal;
