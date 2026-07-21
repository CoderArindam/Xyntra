import React from 'react';
import {
  Video,
  ExternalLink,
  Trash2,
  Sparkles,
  Plus,
} from 'lucide-react';
import { Card, CardHeader, CardTitle, CardDescription } from '../../../components/ui/Card';
import { Skeleton } from '../../../components/ui/Skeleton';
import { WidgetError } from '../../../components/ui/WidgetError';
import type { MeetingSession } from '../../../services/meetingApi';

interface RecentMeetingsWidgetProps {
  sessions: MeetingSession[];
  isLoading: boolean;
  hasError?: boolean;
  onRetry?: () => void;
  pendingPropsCount: number;
  onDeleteSession: (sessionId: string) => void;
  onOpenJoinModal: () => void;
  onOpenProposalsModal: () => void;
}

export const RecentMeetingsWidget: React.FC<RecentMeetingsWidgetProps> = ({
  sessions,
  isLoading,
  hasError = false,
  onRetry,
  pendingPropsCount,
  onDeleteSession,
  onOpenJoinModal,
  onOpenProposalsModal,
}) => {
  return (
    <Card variant="default" padding="md" className="space-y-4">
      <CardHeader className="flex-row items-center justify-between mb-0">
        <div className="space-y-0.5">
          <CardTitle className="text-sm">
            <Video className="w-4 h-4 text-brand-primary" aria-hidden="true" />
            <span>Recent Meetings</span>
          </CardTitle>
          <CardDescription>Recorded Google Meet sessions</CardDescription>
        </div>
        <span className="text-[11px] text-brand-text-muted font-medium">
          {sessions.length} total
        </span>
      </CardHeader>

      {hasError ? (
        <WidgetError
          title="Could not load meetings"
          message="Failed to retrieve recent meeting records."
          onRetry={onRetry}
        />
      ) : isLoading && sessions.length === 0 ? (
        /* Shape-accurate Meeting Skeletons */
        <div className="space-y-2.5" aria-busy="true" aria-label="Loading recent meetings">
          {[1, 2, 3].map((idx) => (
            <div key={idx} className="p-3 rounded-xl border border-brand-border/60 bg-brand-surface-low/30 space-y-2">
              <div className="flex justify-between">
                <Skeleton variant="text" width={100} height={14} />
                <Skeleton variant="rectangular" width={45} height={14} />
              </div>
              <Skeleton variant="text" width={60} height={10} />
            </div>
          ))}
        </div>
      ) : sessions.length === 0 ? (
        /* Purposeful Empty State for 0 Meetings */
        <div className="p-6 text-center border border-dashed border-brand-border rounded-xl space-y-3">
          <Video className="w-7 h-7 mx-auto text-brand-primary/60" aria-hidden="true" />
          <div className="space-y-1">
            <h4 className="text-xs font-bold text-brand-text">No recorded meeting sessions yet</h4>
            <p className="text-[11px] text-brand-text-muted">
              Connect KAIO bot to a Google Meet URL to record audio, generate transcripts, and extract action items.
            </p>
          </div>
          <button
            onClick={onOpenJoinModal}
            className="w-full py-2 px-3 text-xs font-semibold bg-brand-primary hover:bg-brand-primary-hover text-white rounded-lg transition-colors cursor-pointer flex items-center justify-center gap-1.5 shadow-xs"
          >
            <Plus size={14} /> Start / Join Meeting
          </button>
        </div>
      ) : (
        /* Meeting Sessions List */
        <div className="divide-y divide-brand-border/60 border border-brand-border/80 rounded-xl overflow-hidden bg-brand-surface-low/30">
          {sessions.slice(0, 5).map((session) => {
            const displayTitle =
              session.meeting_url?.trim() ||
              `Meeting (${(session.session_id || session.id || '').substring(0, 8)})`;
            const targetUrl = session.meeting_url?.trim() || '#';
            const isCompleted = ['completed', 'finished', 'proposals_ready'].includes(
              (session.status || '').toLowerCase()
            );

            return (
              <div
                key={session.id}
                className="p-3 flex flex-col gap-2 hover:bg-brand-surface-low transition-colors text-xs"
              >
                <div className="flex items-center justify-between gap-3">
                  <div className="min-w-0 flex-1 space-y-0.5">
                    <div className="flex items-center gap-2">
                      <span
                        className={`px-1.5 py-0.2 rounded text-[9px] font-bold uppercase shrink-0 ${
                          session.source === 'google_calendar'
                            ? 'bg-purple-500/10 text-purple-400 border border-purple-500/20'
                            : 'bg-brand-primary/10 text-brand-primary border border-brand-primary/20'
                        }`}
                      >
                        {session.source === 'google_calendar' ? 'Calendar' : 'Manual'}
                      </span>

                      {session.meeting_url ? (
                        <a
                          href={targetUrl}
                          target="_blank"
                          rel="noreferrer"
                          className="font-mono text-brand-text hover:text-brand-primary truncate flex items-center gap-1 font-semibold text-[11px] focus:outline-none focus:underline"
                        >
                          {displayTitle} <ExternalLink className="w-3 h-3 shrink-0" aria-hidden="true" />
                        </a>
                      ) : (
                        <p className="font-mono text-brand-text font-semibold truncate text-[11px]">
                          {displayTitle}
                        </p>
                      )}
                    </div>

                    <div className="flex items-center gap-2 text-[10px] text-brand-text-muted">
                      <span className="capitalize font-medium text-brand-text">{session.status}</span>
                      <span>·</span>
                      <span>{new Date(session.created_at).toLocaleDateString()}</span>
                    </div>
                  </div>

                  <button
                    onClick={() => onDeleteSession(session.id || session.session_id)}
                    className="p-1.5 text-brand-text-muted hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors shrink-0 cursor-pointer focus:ring-1 focus:ring-red-400"
                    title="Delete Meeting Record"
                    aria-label={`Delete meeting record ${displayTitle}`}
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>

                {/* Proposals Ready Direct Link */}
                {isCompleted && pendingPropsCount > 0 && (
                  <button
                    onClick={onOpenProposalsModal}
                    className="w-full mt-1 py-1 px-2 text-[11px] font-semibold bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 rounded-lg flex items-center justify-center gap-1.5 transition-colors cursor-pointer focus:ring-1 focus:ring-emerald-400"
                  >
                    <Sparkles className="w-3 h-3 text-emerald-400" /> Proposals Ready — Review Queue ({pendingPropsCount})
                  </button>
                )}
              </div>
            );
          })}
        </div>
      )}
    </Card>
  );
};
