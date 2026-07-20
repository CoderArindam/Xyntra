import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useProposals } from '../hooks/useProposals';
import ProposalCard from './ProposalCard';
import ProposalEditModal from './ProposalEditModal';
import type { TaskProposal } from '../../../services/taskProposals';
import { getBoards, type Board } from '../../../services/boardsApi';
import { ArrowLeft, Sparkles, CheckCircle, RefreshCw, AlertCircle } from 'lucide-react';

export const ProposalQueueView: React.FC = () => {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();
  const {
    proposals,
    loading,
    error,
    fetchProposals,
    handleApprove,
    handleReject,
    handleUpdateAndApprove,
  } = useProposals();

  const [boards, setBoards] = useState<Board[]>([]);
  const [editingProposal, setEditingProposal] = useState<TaskProposal | null>(null);

  useEffect(() => {
    if (sessionId) {
      fetchProposals(sessionId);
    }
  }, [sessionId, fetchProposals]);

  useEffect(() => {
    let isMounted = true;
    const fetchOrgBoards = async () => {
      try {
        const boardList = await getBoards();
        if (isMounted) {
          setBoards(boardList.filter((b) => !b.archived_at));
        }
      } catch (err) {
        console.error('Failed to fetch org boards for proposal queue:', err);
      }
    };

    fetchOrgBoards();
    return () => {
      isMounted = false;
    };
  }, []);

  const pendingProposals = proposals.filter((p) => p.status === 'pending');
  const reviewedProposals = proposals.filter((p) => p.status !== 'pending');

  return (
    <div className="min-h-screen bg-brand-bg text-brand-text p-6 max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-brand-border">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate(-1)}
            className="p-2 rounded-lg bg-brand-surface border border-brand-border text-brand-text-muted hover:text-brand-text hover:bg-brand-surface-low transition-colors"
            title="Go Back"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold text-brand-text flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-brand-primary" /> Task Proposal Review Queue
              </h1>
              {pendingProposals.length > 0 && (
                <span className="px-2.5 py-0.5 text-xs font-semibold rounded-full bg-brand-primary/20 text-brand-primary border border-brand-primary/30">
                  {pendingProposals.length} Pending
                </span>
              )}
            </div>
            <p className="text-xs text-brand-text-muted mt-0.5">
              Review AI-extracted action items from meeting session <span className="font-mono text-brand-text">{sessionId}</span>
            </p>
          </div>
        </div>

        <button
          onClick={() => sessionId && fetchProposals(sessionId)}
          disabled={loading}
          className="flex items-center gap-2 px-3.5 py-2 text-xs font-medium bg-brand-surface border border-brand-border rounded-lg text-brand-text hover:bg-brand-surface-low transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} /> Refresh Proposals
        </button>
      </div>

      {/* Loading & Error States */}
      {loading && proposals.length === 0 && (
        <div className="flex flex-col items-center justify-center py-16 gap-3">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-primary"></div>
          <p className="text-sm text-brand-text-muted">Loading AI task proposals...</p>
        </div>
      )}

      {error && (
        <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm flex items-center gap-3">
          <AlertCircle className="w-5 h-5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Empty State */}
      {!loading && proposals.length === 0 && !error && (
        <div className="flex flex-col items-center justify-center py-16 px-4 bg-brand-surface border border-brand-border rounded-2xl text-center">
          <CheckCircle className="w-12 h-12 text-emerald-400 mb-3" />
          <h3 className="text-base font-semibold text-brand-text">No Task Proposals Found</h3>
          <p className="text-xs text-brand-text-muted max-w-md mt-1">
            Either all extracted task proposals for this meeting have already been reviewed, or no clear action items were identified.
          </p>
        </div>
      )}

      {/* Pending Proposals Section */}
      {pendingProposals.length > 0 && (
        <div className="space-y-4">
          <h2 className="text-sm font-semibold text-brand-text uppercase tracking-wider text-brand-text-muted">
            Pending Proposals ({pendingProposals.length})
          </h2>
          <div className="grid grid-cols-1 gap-4">
            {pendingProposals.map((proposal) => (
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
        </div>
      )}

      {/* Previously Reviewed Section */}
      {reviewedProposals.length > 0 && (
        <div className="space-y-4 pt-6 border-t border-brand-border/60">
          <h2 className="text-sm font-semibold text-brand-text uppercase tracking-wider text-brand-text-muted">
            Reviewed Proposals ({reviewedProposals.length})
          </h2>
          <div className="grid grid-cols-1 gap-4 opacity-80">
            {reviewedProposals.map((proposal) => (
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
        </div>
      )}

      {/* Edit Modal */}
      <ProposalEditModal
        isOpen={Boolean(editingProposal)}
        onClose={() => setEditingProposal(null)}
        proposal={editingProposal}
        boards={boards}
        onSubmit={handleUpdateAndApprove}
      />
    </div>
  );
};

export default ProposalQueueView;
