import React, { useState } from 'react';
import type { TaskProposal } from '../../../services/taskProposals';
import type { Board } from '../../../services/boardsApi';
import UserAvatar from '../../../components/common/UserAvatar';
import {
  Check,
  X,
  Edit3,
  Quote,
  ChevronDown,
  ChevronUp,
  Sparkles,
  AlertCircle,
  Kanban,
} from 'lucide-react';

interface ProposalCardProps {
  proposal: TaskProposal;
  boards: Board[];
  onApprove: (id: string, boardId?: number | null) => Promise<void>;
  onReject: (id: string) => Promise<void>;
  onEditAndApprove: (proposal: TaskProposal) => void;
}

export const ProposalCard: React.FC<ProposalCardProps> = ({
  proposal,
  boards,
  onApprove,
  onReject,
  onEditAndApprove,
}) => {
  const [showQuote, setShowQuote] = useState(false);
  const [selectedBoardId, setSelectedBoardId] = useState<number | null>(
    proposal.board_id || null
  );
  const [isApproving, setIsApproving] = useState(false);
  const [isRejecting, setIsRejecting] = useState(false);

  const confidence =
    proposal.confidence_score !== undefined && proposal.confidence_score !== null
      ? Math.round(proposal.confidence_score * 100)
      : 80;

  const getConfidenceBadge = () => {
    if (confidence >= 80) {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
          <Sparkles className="w-3 h-3" /> {confidence}% High Confidence
        </span>
      );
    } else if (confidence >= 50) {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">
          <Sparkles className="w-3 h-3" /> {confidence}% Medium Confidence
        </span>
      );
    } else {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-red-500/10 text-red-400 border border-red-500/20">
          <AlertCircle className="w-3 h-3" /> {confidence}% Low Confidence
        </span>
      );
    }
  };

  const assigneeUser = proposal.suggested_assignee_id
    ? {
        id: proposal.suggested_assignee_id,
        email: proposal.suggested_assignee_email || '',
        first_name: proposal.suggested_assignee_first_name,
        last_name: proposal.suggested_assignee_last_name,
        avatar_url: proposal.suggested_assignee_avatar_url,
      }
    : null;

  const handleApproveClick = async () => {
    if (!selectedBoardId) return;
    setIsApproving(true);
    try {
      await onApprove(proposal.id, selectedBoardId);
    } finally {
      setIsApproving(false);
    }
  };

  const handleRejectClick = async () => {
    setIsRejecting(true);
    try {
      await onReject(proposal.id);
    } finally {
      setIsRejecting(false);
    }
  };

  return (
    <div className="bg-brand-surface border border-brand-border rounded-xl p-5 shadow-sm hover:shadow-md transition-all flex flex-col gap-4">
      {/* Top Header */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            {getConfidenceBadge()}
            {proposal.priority && (
              <span className={`px-2.5 py-0.5 text-xs font-semibold rounded-full border ${
                proposal.priority === 'High' || proposal.priority === 'Urgent'
                  ? 'bg-red-500/10 text-red-400 border-red-500/20'
                  : proposal.priority === 'Medium'
                  ? 'bg-orange-500/10 text-orange-400 border-orange-500/20'
                  : 'bg-blue-500/10 text-blue-400 border-blue-500/20'
              }`}>
                {proposal.priority} Priority
              </span>
            )}
            {proposal.due_date && (
              <span className="px-2.5 py-0.5 text-xs font-medium rounded-full bg-brand-surface-low text-brand-text-muted border border-brand-border">
                Due {new Date(proposal.due_date).toLocaleDateString()}
              </span>
            )}
            {proposal.status === 'approved' && (
              <span className="px-2 py-0.5 text-xs font-semibold rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                Approved
              </span>
            )}
            {proposal.status === 'rejected' && (
              <span className="px-2 py-0.5 text-xs font-semibold rounded-full bg-red-500/20 text-red-400 border border-red-500/30">
                Rejected
              </span>
            )}
          </div>
          <h3 className="text-base font-semibold text-brand-text leading-snug">
            {proposal.title}
          </h3>
        </div>

        {/* Assignee Preview */}
        <div className="flex items-center gap-2 shrink-0 bg-brand-surface-low px-3 py-1.5 rounded-lg border border-brand-border/50">
          <UserAvatar user={assigneeUser} size="sm" />
          <span className="text-xs text-brand-text-muted font-medium max-w-[120px] truncate">
            {proposal.suggested_assignee_display_name || 'Unassigned'}
          </span>
        </div>
      </div>

      {/* Target Board Selector */}
      <div className="flex items-center gap-3 bg-brand-surface-low/80 p-3 rounded-lg border border-brand-border/60">
        <Kanban className="w-4 h-4 text-brand-primary shrink-0" />
        <div className="flex-1 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-brand-text">Target Board:</span>
            {proposal.board_source === 'llm_matched' && (
              <span className="px-2 py-0.5 text-[10px] font-semibold rounded-full bg-brand-primary/15 text-brand-primary border border-brand-primary/30 flex items-center gap-1">
                <Sparkles className="w-2.5 h-2.5" /> AI Suggested
              </span>
            )}
          </div>

          <select
            value={selectedBoardId || ''}
            disabled={proposal.status !== 'pending'}
            onChange={(e) => setSelectedBoardId(e.target.value ? Number(e.target.value) : null)}
            className="px-3 py-1.5 text-xs bg-brand-surface border border-brand-border rounded-md text-brand-text focus:outline-none focus:border-brand-primary disabled:opacity-60"
          >
            <option value="">Select a target board…</option>
            {boards.map((b) => (
              <option key={b.id} value={b.id}>
                {b.name} ({b.project_key})
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Description */}
      {proposal.description && (
        <p className="text-sm text-brand-text-muted leading-relaxed line-clamp-3">
          {proposal.description}
        </p>
      )}

      {/* Source Transcript Quote */}
      {proposal.source_transcript_quote && (
        <div className="border border-brand-border/60 rounded-lg overflow-hidden bg-brand-surface-low/50">
          <button
            onClick={() => setShowQuote(!showQuote)}
            className="w-full px-3 py-2 text-xs text-brand-text-muted flex items-center justify-between hover:bg-brand-surface transition-colors"
          >
            <span className="flex items-center gap-1.5 font-medium">
              <Quote className="w-3.5 h-3.5 text-brand-primary" /> Grounding Transcript Quote
            </span>
            {showQuote ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          </button>
          {showQuote && (
            <div className="px-3 py-2.5 text-xs italic text-brand-text/90 border-t border-brand-border/40 bg-brand-surface/80">
              "{proposal.source_transcript_quote}"
            </div>
          )}
        </div>
      )}

      {/* Actions (Only active when status === 'pending') */}
      {proposal.status === 'pending' ? (
        <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-2 border-t border-brand-border/40">
          {!selectedBoardId ? (
            <span className="text-xs text-amber-400 font-medium flex items-center gap-1">
              <AlertCircle className="w-3.5 h-3.5" /> Select a board to approve
            </span>
          ) : (
            <span />
          )}

          <div className="flex items-center gap-2.5 w-full sm:w-auto justify-end">
            <button
              onClick={handleRejectClick}
              disabled={isRejecting || isApproving}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-red-400 hover:text-red-300 hover:bg-red-500/10 rounded-lg transition-colors border border-red-500/20 disabled:opacity-50"
            >
              <X className="w-3.5 h-3.5" /> Reject
            </button>

            <button
              onClick={() => onEditAndApprove({ ...proposal, board_id: selectedBoardId })}
              disabled={isRejecting || isApproving || !selectedBoardId}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-brand-primary hover:bg-brand-primary/10 rounded-lg transition-colors border border-brand-primary/30 disabled:opacity-50"
            >
              <Edit3 className="w-3.5 h-3.5" /> Edit & Approve
            </button>

            <button
              onClick={handleApproveClick}
              disabled={isRejecting || isApproving || !selectedBoardId}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-white bg-emerald-600 hover:bg-emerald-500 rounded-lg transition-colors shadow-sm disabled:opacity-50"
            >
              <Check className="w-3.5 h-3.5" /> Approve
            </button>
          </div>
        </div>
      ) : (
        <div className="text-xs text-brand-text-muted pt-2 border-t border-brand-border/40 flex justify-between items-center">
          <span>Reviewed by {proposal.reviewer_display_name || 'System'}</span>
          <span>{proposal.reviewed_at ? new Date(proposal.reviewed_at).toLocaleDateString() : ''}</span>
        </div>
      )}
    </div>
  );
};

export default ProposalCard;
