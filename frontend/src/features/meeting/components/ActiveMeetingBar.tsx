import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Sparkles, X } from 'lucide-react';
import { useAuthStore } from '../../../store/authStore';
import api from '../../../lib/axios';

interface SessionStatusResponse {
  session_id: string;
  status: string;
  proposals_ready?: boolean;
  proposals_count?: number;
}

export const ActiveMeetingBar: React.FC = () => {
  const { user } = useAuthStore();
  const [sessionData, setSessionData] = useState<SessionStatusResponse | null>(null);
  const [dismissed, setDismissed] = useState(false);

  const userRole = (user?.role || '').toUpperCase();
  const isManagerOrAdmin = ['SUPER_ADMIN', 'MANAGER'].includes(userRole);

  useEffect(() => {
    if (!isManagerOrAdmin) return;

    // Read active or recent session ID from localStorage if available
    const activeSessionId = localStorage.getItem('kaio_active_session_id');
    if (!activeSessionId) return;

    let isMounted = true;

    const checkStatus = async () => {
      try {
        const response = await api.get(`/meeting/status/${activeSessionId}`);
        const data: SessionStatusResponse = response.data;

        if (isMounted) {
          setSessionData(data);
          if (['finished', 'completed', 'failed', 'meeting_ended'].includes(data.status)) {
            localStorage.removeItem('kaio_active_session_id');
          }
        }
      } catch (err: any) {
        localStorage.removeItem('kaio_active_session_id');
      }
    };

    checkStatus();
    const interval = setInterval(checkStatus, 10000); // 10s polling

    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [isManagerOrAdmin]);

  if (!isManagerOrAdmin || dismissed || !sessionData) {
    return null;
  }

  if (!sessionData.proposals_ready || !sessionData.proposals_count) {
    return null;
  }

  return (
    <div className="bg-brand-primary/10 border-b border-brand-primary/30 px-6 py-2.5 flex items-center justify-between z-20 animate-in slide-in-from-top duration-300 shrink-0">
      <div className="flex items-center gap-2.5 text-xs text-brand-text">
        <Sparkles className="w-4 h-4 text-brand-primary animate-pulse" />
        <span className="font-semibold text-brand-text">
          {sessionData.proposals_count} task proposal{sessionData.proposals_count > 1 ? 's' : ''} ready for review
        </span>
        <span className="text-brand-text-muted hidden md:inline">
          — AI extraction completed for session <code className="font-mono text-brand-text">{sessionData.session_id.slice(0, 8)}</code>
        </span>
      </div>

      <div className="flex items-center gap-3">
        <Link
          to={`/meetings/${sessionData.session_id}/proposals`}
          className="px-3 py-1.5 text-xs font-semibold bg-brand-primary text-white hover:bg-brand-primary/90 rounded-md transition-colors shadow-sm"
        >
          Review Proposals
        </Link>
        <button
          onClick={() => setDismissed(true)}
          className="text-brand-text-muted hover:text-brand-text p-1 rounded transition-colors"
          title="Dismiss Banner"
        >
          <X className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};

export default ActiveMeetingBar;
