import React, { useEffect, useState, useCallback } from "react";
import { createPortal } from "react-dom";
import {
  listOrgProposals,
  approveProposal,
  rejectProposal,
  updateProposal,
  type TaskProposal,
} from "../../../services/taskProposals";
import { getBoards, type Board } from "../../../services/boardsApi";
import ProposalCard from "./ProposalCard";
import ProposalEditModal from "./ProposalEditModal";
import {
  Sparkles,
  X,
  RefreshCw,
  CheckCircle2,
} from "lucide-react";

interface GlobalProposalsModalProps {
  isOpen: boolean;
  onClose: () => void;
  onProposalsUpdated?: () => void;
}

export const GlobalProposalsModal: React.FC<GlobalProposalsModalProps> = ({
  isOpen,
  onClose,
  onProposalsUpdated,
}) => {
  const [proposals, setProposals] = useState<TaskProposal[]>([]);
  const [boards, setBoards] = useState<Board[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editingProposal, setEditingProposal] = useState<TaskProposal | null>(
    null,
  );

  const fetchProposals = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listOrgProposals("pending");
      setProposals(data);
    } catch (err: any) {
      console.error("Failed to load organization proposals:", err);
      setError(err?.response?.data?.detail || "Failed to load task proposals");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!isOpen) return;

    fetchProposals();

    let isMounted = true;
    getBoards()
      .then((data) => {
        if (isMounted) setBoards(data.filter((b) => !b.archived_at));
      })
      .catch((err) =>
        console.error("Failed to load boards for proposal modal:", err),
      );

    return () => {
      isMounted = false;
    };
  }, [isOpen, fetchProposals]);

  if (!isOpen) return null;

  const handleApprove = async (id: string, boardId?: number | null) => {
    try {
      await approveProposal(id, { board_id: boardId });
      setProposals((prev) => prev.filter((p) => p.id !== id));
      if (onProposalsUpdated) onProposalsUpdated();
    } catch (err: any) {
      console.error("Failed to approve proposal:", err);
      alert(err?.response?.data?.detail || "Failed to approve proposal");
    }
  };

  const handleReject = async (id: string) => {
    try {
      await rejectProposal(id);
      setProposals((prev) => prev.filter((p) => p.id !== id));
      if (onProposalsUpdated) onProposalsUpdated();
    } catch (err: any) {
      console.error("Failed to reject proposal:", err);
      alert(err?.response?.data?.detail || "Failed to reject proposal");
    }
  };

  const handleUpdateAndApprove = async (updatedProposal: TaskProposal) => {
    try {
      await updateProposal(updatedProposal.id, {
        title: updatedProposal.title,
        description: updatedProposal.description,
        suggested_assignee_id: updatedProposal.suggested_assignee_id,
        board_id: updatedProposal.board_id,
        priority: updatedProposal.priority,
        due_date: updatedProposal.due_date,
      });

      await approveProposal(updatedProposal.id, {
        board_id: updatedProposal.board_id,
      });
      setProposals((prev) => prev.filter((p) => p.id !== updatedProposal.id));
      setEditingProposal(null);
      if (onProposalsUpdated) onProposalsUpdated();
    } catch (err: any) {
      console.error("Failed to edit and approve proposal:", err);
      alert(err?.response?.data?.detail || "Failed to update proposal");
    }
  };

  return createPortal(
    <div className="fixed inset-0 z-[var(--z-overlay)] flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs overflow-y-auto">
      <div className="bg-brand-bg border border-brand-border rounded-2xl w-full max-w-4xl max-h-[90vh] flex flex-col shadow-2xl overflow-hidden relative z-[var(--z-modal)]">
        {/* Header */}
        <div className="p-6 border-b border-brand-border flex items-center justify-between bg-brand-surface shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 shrink-0">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-lg font-bold text-brand-text">
                  AI Task Proposals Queue
                </h2>
                <span className="px-2.5 py-0.5 text-xs font-semibold rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                  {proposals.length} Pending
                </span>
              </div>
              <p className="text-xs text-brand-text-muted mt-0.5">
                Review, modify target board, title, description, priority,
                deadline, or assignee before approving into active Kanban
                boards.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={fetchProposals}
              disabled={loading}
              className="p-2 rounded-lg bg-brand-surface-low border border-brand-border text-brand-text-muted hover:text-brand-text transition-colors disabled:opacity-50"
              title="Refresh Queue"
            >
              <RefreshCw
                className={`w-4 h-4 ${loading ? "animate-spin" : ""}`}
              />
            </button>
            <button
              onClick={onClose}
              className="p-2 rounded-lg bg-brand-surface-low border border-brand-border text-brand-text-muted hover:text-brand-text transition-colors"
              title="Close Modal"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Content Body */}
        <div className="p-6 overflow-y-auto flex-1 space-y-4">
          {loading && proposals.length === 0 && (
            <div className="flex flex-col items-center justify-center py-16 gap-3">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-primary"></div>
              <p className="text-sm text-brand-text-muted">
                Loading pending proposals...
              </p>
            </div>
          )}

          {error && (
            <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-xs flex items-center justify-between">
              <span>{error}</span>
              <button
                onClick={fetchProposals}
                className="font-semibold underline cursor-pointer"
              >
                Retry
              </button>
            </div>
          )}

          {!loading && proposals.length === 0 && !error && (
            <div className="flex flex-col items-center justify-center py-16 text-center border border-dashed border-brand-border rounded-xl p-8 bg-brand-surface/50 space-y-3">
              <CheckCircle2 className="w-12 h-12 text-emerald-400/60" />
              <h3 className="text-base font-semibold text-brand-text">
                All Task Proposals Reviewed!
              </h3>
              <p className="text-xs text-brand-text-muted max-w-md">
                There are currently no pending AI task proposals awaiting
                approval. Extracted items will appear here after new meetings
                conclude.
              </p>
            </div>
          )}

          {proposals.map((proposal) => (
            <ProposalCard
              key={proposal.id}
              proposal={proposal}
              boards={boards}
              onApprove={handleApprove}
              onReject={handleReject}
              onEditAndApprove={(p) => setEditingProposal(p)}
            />
          ))}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-brand-border bg-brand-surface flex justify-end shrink-0">
          <button
            onClick={onClose}
            className="px-4 py-2 text-xs font-semibold bg-brand-surface-low border border-brand-border hover:bg-brand-surface-hover rounded-xl text-brand-text transition-colors cursor-pointer"
          >
            Done
          </button>
        </div>
      </div>

      {/* Edit Modal */}
      {editingProposal && (
        <ProposalEditModal
          isOpen={!!editingProposal}
          proposal={editingProposal}
          boards={boards}
          onClose={() => setEditingProposal(null)}
          onSubmit={async (_id, data) => {
            await handleUpdateAndApprove({
              ...editingProposal,
              title: data.title,
              description: data.description,
              suggested_assignee_id: data.suggested_assignee_id,
              board_id: data.board_id,
              priority: data.priority,
              due_date: data.due_date,
            });
          }}
        />
      )}
    </div>,
    document.body
  );
};

export default GlobalProposalsModal;
