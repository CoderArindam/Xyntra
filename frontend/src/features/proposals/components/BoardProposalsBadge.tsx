import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Sparkles } from 'lucide-react';
import { useAuthStore } from '../../../store/authStore';
import { listPendingProposalsByBoard, type TaskProposal } from '../../../services/taskProposals';

interface BoardProposalsBadgeProps {
  boardId: number;
}

export const BoardProposalsBadge: React.FC<BoardProposalsBadgeProps> = ({ boardId }) => {
  const { user } = useAuthStore();
  const [proposals, setProposals] = useState<TaskProposal[]>([]);

  const userRole = (user?.role || '').toUpperCase();
  const isManagerOrAdmin = ['SUPER_ADMIN', 'MANAGER'].includes(userRole);

  useEffect(() => {
    if (!isManagerOrAdmin || !boardId) return;

    let isMounted = true;
    const fetchBoardProposals = async () => {
      try {
        const data = await listPendingProposalsByBoard(boardId);
        if (isMounted) {
          setProposals(data);
        }
      } catch (err) {
        // Silently catch if board has no proposals or permissions check fails
      }
    };

    fetchBoardProposals();
  }, [boardId, isManagerOrAdmin]);

  if (!isManagerOrAdmin || proposals.length === 0) {
    return null;
  }

  const latestSessionId = proposals[0]?.meeting_session_id;

  return (
    <Link
      to={`/meetings/${latestSessionId}/proposals`}
      className="px-3 py-1.5 bg-brand-primary/10 border border-brand-primary/30 hover:bg-brand-primary/20 rounded-md text-xs font-semibold text-brand-primary flex items-center gap-2 transition-colors shadow-xs shrink-0"
      title={`${proposals.length} pending task proposal(s) ready for review`}
    >
      <Sparkles className="w-3.5 h-3.5 text-brand-primary animate-pulse" />
      <span>{proposals.length} Proposal{proposals.length > 1 ? 's' : ''}</span>
    </Link>
  );
};

export default BoardProposalsBadge;
