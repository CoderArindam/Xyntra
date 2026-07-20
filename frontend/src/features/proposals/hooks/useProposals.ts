import { useState, useCallback } from 'react';
import toast from 'react-hot-toast';
import type { TaskProposal } from '../../../services/taskProposals';
import {
  listProposalsByMeeting,
  updateProposal,
  approveProposal,
  rejectProposal,
} from '../../../services/taskProposals';

export const useProposals = () => {
  const [proposals, setProposals] = useState<TaskProposal[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchProposals = useCallback(async (sessionId: string) => {
    setLoading(true);
    setError(null);
    try {
      const data = await listProposalsByMeeting(sessionId);
      setProposals(data);
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      const msg = typeof detail === 'object' && detail?.message ? detail.message : (detail || 'Failed to fetch task proposals');
      setError(msg);
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleApprove = async (id: string, boardId?: number | null) => {
    try {
      await approveProposal(id, boardId ? { board_id: boardId } : undefined);
      toast.success('Task proposal approved & task created!');
      setProposals((prev) =>
        prev.map((p) => (p.id === id ? { ...p, status: 'approved' } : p))
      );
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      const msg = typeof detail === 'object' && detail?.message ? detail.message : (detail || 'Failed to approve task proposal');
      toast.error(msg);
      throw err;
    }
  };

  const handleReject = async (id: string) => {
    try {
      await rejectProposal(id);
      toast.success('Task proposal rejected');
      setProposals((prev) =>
        prev.map((p) => (p.id === id ? { ...p, status: 'rejected' } : p))
      );
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      const msg = typeof detail === 'object' && detail?.message ? detail.message : (detail || 'Failed to reject task proposal');
      toast.error(msg);
      throw err;
    }
  };

  const handleUpdateAndApprove = async (
    id: string,
    data: { title: string; description: string; suggested_assignee_id: number | null; board_id: number | null }
  ) => {
    try {
      const updated = await updateProposal(id, data);
      setProposals((prev) => prev.map((p) => (p.id === id ? updated : p)));

      await approveProposal(id, { board_id: data.board_id });
      toast.success('Proposal updated and approved!');
      setProposals((prev) =>
        prev.map((p) => (p.id === id ? { ...p, ...updated, status: 'approved' } : p))
      );
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      const msg = typeof detail === 'object' && detail?.message ? detail.message : (detail || 'Failed during edit and approve operation');
      toast.error(msg);
      throw err;
    }
  };

  return {
    proposals,
    loading,
    error,
    fetchProposals,
    handleApprove,
    handleReject,
    handleUpdateAndApprove,
  };
};
