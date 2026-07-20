import React, { useState, useEffect } from 'react';
import toast from 'react-hot-toast';
import Modal from '../../../components/common/Modal';
import { getBoards, type Board } from '../../../services/boardsApi';
import { joinMeeting } from '../../../services/meetingApi';
import { Video, Play, AlertCircle } from 'lucide-react';

interface JoinMeetingModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: (sessionId: string) => void;
}

export const JoinMeetingModal: React.FC<JoinMeetingModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
}) => {
  const [meetingUrl, setMeetingUrl] = useState('');
  const [selectedBoardId, setSelectedBoardId] = useState<number | null>(null);
  const [boards, setBoards] = useState<Board[]>([]);
  const [isLoadingBoards, setIsLoadingBoards] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen) return;

    let isMounted = true;
    const fetchOrgBoards = async () => {
      setIsLoadingBoards(true);
      try {
        const boardList = await getBoards();
        if (isMounted) {
          setBoards(boardList.filter((b) => !b.archived_at));
        }
      } catch (err) {
        console.error('Failed to load org boards:', err);
      } finally {
        if (isMounted) setIsLoadingBoards(false);
      }
    };

    fetchOrgBoards();
    setErrorMessage(null);
    setMeetingUrl('');
    setSelectedBoardId(null);

    return () => {
      isMounted = false;
    };
  }, [isOpen]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!meetingUrl.trim()) {
      setErrorMessage('Google Meet URL is required');
      return;
    }

    if (!meetingUrl.includes('meet.google.com') && !meetingUrl.startsWith('http')) {
      setErrorMessage('Please enter a valid meeting URL (e.g. https://meet.google.com/abc-defg-hij)');
      return;
    }

    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      const res = await joinMeeting(meetingUrl.trim(), selectedBoardId);
      toast.success('Meeting bot launch initiated!');

      if (res.session_id) {
        localStorage.setItem('kaio_active_session_id', res.session_id);
        if (onSuccess) onSuccess(res.session_id);
      }

      onClose();
    } catch (err: any) {
      const msg = err?.response?.data?.detail || 'Failed to initiate meeting join';
      setErrorMessage(msg);
      toast.error(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Start / Join Video Meeting" width="max-w-lg">
      <form onSubmit={handleSubmit} className="space-y-4">
        {errorMessage && (
          <div className="p-3 text-xs bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{errorMessage}</span>
          </div>
        )}

        <div>
          <label className="block text-xs font-semibold text-brand-text mb-1">
            Google Meet URL <span className="text-red-400">*</span>
          </label>
          <div className="relative">
            <Video className="w-4 h-4 text-brand-text-muted absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="url"
              value={meetingUrl}
              onChange={(e) => setMeetingUrl(e.target.value)}
              placeholder="https://meet.google.com/abc-defg-hij"
              className="w-full pl-9 pr-3 py-2 text-sm bg-brand-surface-low border border-brand-border rounded-lg text-brand-text focus:outline-none focus:border-brand-primary"
              required
            />
          </div>
        </div>

        <div>
          <label className="block text-xs font-semibold text-brand-text mb-1">
            Target Project Board (Optional Default)
          </label>
          <select
            value={selectedBoardId || ''}
            disabled={isLoadingBoards}
            onChange={(e) => setSelectedBoardId(e.target.value ? Number(e.target.value) : null)}
            className="w-full px-3 py-2 text-sm bg-brand-surface-low border border-brand-border rounded-lg text-brand-text focus:outline-none focus:border-brand-primary disabled:opacity-50"
          >
            <option value="">Select a default board (or leave unassigned)…</option>
            {boards.map((b) => (
              <option key={b.id} value={b.id}>
                {b.name} ({b.project_key})
              </option>
            ))}
          </select>
          <p className="text-[11px] text-brand-text-muted mt-1">
            Task proposals will automatically resolve specific target boards via AI matching during extraction.
          </p>
        </div>

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
            disabled={isSubmitting}
            className="flex items-center gap-1.5 px-4 py-2 text-xs font-semibold text-white bg-brand-primary hover:bg-brand-primary/90 rounded-lg shadow-sm transition-colors disabled:opacity-50"
          >
            {isSubmitting ? (
              <span className="animate-spin rounded-full h-3.5 w-3.5 border-b-2 border-white"></span>
            ) : (
              <Play className="w-3.5 h-3.5 fill-current" />
            )}
            Launch Meeting Bot
          </button>
        </div>
      </form>
    </Modal>
  );
};

export default JoinMeetingModal;
