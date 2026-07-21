import React, { useEffect, useState } from 'react';
import {
  Video,
  Calendar,
  Plus,
  Search,
  Folder,
  Loader2,
  Play,
  Sparkles,
  ExternalLink,
  Trash2,
} from 'lucide-react';
import { useAuthStore } from '../../store/authStore';
import {
  useBoardStore,
  useActiveBoards,
  useArchivedBoards,
} from '../../store/boardStore';
import { useUiStore } from '../../store/uiStore';
import { useOrganizationStore } from '../../store/organizationStore';
import { usePageTitle } from '../../hooks/usePageTitle';
import EmptyState from '../../components/common/EmptyState';
import { ProjectCard } from '../../components/common/ProjectCard';
import JoinMeetingModal from '../meeting/components/JoinMeetingModal';
import {
  listRecentMeetingSessions,
  deleteMeetingSession,
  type MeetingSession,
} from '../../services/meetingApi';
import GlobalProposalsModal from '../proposals/components/GlobalProposalsModal';
import { listOrgProposals } from '../../services/taskProposals';

export const DashboardView: React.FC = () => {
  const { user } = useAuthStore();
  usePageTitle('Dashboard');

  const { isFetching, fetchBoards } = useBoardStore();
  const activeBoards = useActiveBoards();
  const archivedBoards = useArchivedBoards();
  const { openCreateProjectModal } = useUiStore();
  const { profile } = useOrganizationStore();

  const [search, setSearch] = useState('');
  const [isJoinModalOpen, setIsJoinModalOpen] = useState(false);
  const [recentSessions, setRecentSessions] = useState<MeetingSession[]>([]);
  const [isLoadingSessions, setIsLoadingSessions] = useState(false);
  const [isProposalsModalOpen, setIsProposalsModalOpen] = useState(false);
  const [pendingProposalsCount, setPendingProposalsCount] = useState<number>(0);

  const userRole = (user?.role || '').toUpperCase();
  const isManagerOrAdmin = ['SUPER_ADMIN', 'MANAGER'].includes(userRole);

  const fetchProposalsCount = React.useCallback(async () => {
    if (!isManagerOrAdmin) return;
    try {
      const data = await listOrgProposals('pending');
      setPendingProposalsCount(data.length);
    } catch (err) {
      console.error('Failed to fetch org proposals count:', err);
    }
  }, [isManagerOrAdmin]);

  useEffect(() => {
    fetchProposalsCount();
  }, [fetchProposalsCount]);

  useEffect(() => {
    fetchBoards();
  }, [fetchBoards]);

  useEffect(() => {
    if (!isManagerOrAdmin) return;
    let isMounted = true;
    const fetchSessions = async () => {
      setIsLoadingSessions(true);
      try {
        const data = await listRecentMeetingSessions();
        if (isMounted) {
          setRecentSessions(data);
        }
      } catch (err) {
        console.error('Failed to load recent meeting sessions:', err);
      } finally {
        if (isMounted) setIsLoadingSessions(false);
      }
    };

    fetchSessions();
    return () => {
      isMounted = false;
    };
  }, [isManagerOrAdmin]);

  const filteredActiveBoards = activeBoards.filter((board: any) =>
    board.name.toLowerCase().includes(search.toLowerCase())
  );

  const filteredArchivedBoards = archivedBoards.filter((board: any) =>
    board.name.toLowerCase().includes(search.toLowerCase())
  );

  const handleDeleteSession = async (sessionId: string) => {
    try {
      await deleteMeetingSession(sessionId);
      setRecentSessions((prev) => prev.filter((s) => s.id !== sessionId && s.session_id !== sessionId));
    } catch (err) {
      console.error('Failed to delete meeting session:', err);
    }
  };

  return (
    <div className="max-w-[1400px] mx-auto px-8 py-8 space-y-8">
      {/* Top Banner / Welcome */}
      <section className="bg-brand-surface border border-brand-border rounded-2xl p-6 flex flex-col md:flex-row md:items-center justify-between gap-6 shadow-xs">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-brand-text">
            Welcome back, {user?.first_name || user?.email?.split('@')[0] || 'User'}
          </h1>
          <p className="text-sm text-brand-text-muted mt-1">
            {profile?.name || 'Workspace'} · AI Kanban Orchestration & Meeting Task Automation
          </p>
        </div>

        {/* Manager/Admin Actions: Start Meeting */}
        {isManagerOrAdmin && (
          <div className="flex items-center gap-3 shrink-0">
            <button
              onClick={() => setIsJoinModalOpen(true)}
              className="bg-brand-primary hover:bg-brand-primary/90 text-white px-5 py-2.5 rounded-xl text-sm font-semibold flex items-center gap-2 transition-all shadow-sm cursor-pointer"
            >
              <Video className="w-4 h-4" /> Start / Join Meeting
            </button>
          </div>
        )}
      </section>

      {/* Quick Launch & Meeting Controls (Manager/Admin Only) */}
      {isManagerOrAdmin && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Section 1: Start a Meeting */}
            <div className="bg-brand-surface border border-brand-border rounded-2xl p-6 flex flex-col justify-between gap-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-brand-primary/10 border border-brand-primary/20 flex items-center justify-center text-brand-primary shrink-0">
                  <Video className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-brand-text">Start a Meeting</h3>
                  <p className="text-xs text-brand-text-muted">Launch bot to extract tasks</p>
                </div>
              </div>
              <p className="text-xs text-brand-text-muted leading-relaxed">
                Connect KAIO bot to your live Google Meet URL. Extracted action items will appear in the review queue.
              </p>
              <button
                onClick={() => setIsJoinModalOpen(true)}
                className="w-full py-2 px-3 text-xs font-semibold bg-brand-surface-low border border-brand-border hover:bg-brand-surface-hover rounded-lg text-brand-text flex items-center justify-center gap-2 transition-colors cursor-pointer"
              >
                <Play className="w-3.5 h-3.5 fill-current text-brand-primary" /> Open Join Dialog
              </button>
            </div>

            {/* Section 2: Google Calendar Integration (Placeholder) */}
            <div className="bg-brand-surface border border-brand-border rounded-2xl p-6 flex flex-col justify-between gap-4 opacity-75">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-400 shrink-0">
                    <Calendar className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-brand-text">Google Calendar</h3>
                    <p className="text-xs text-brand-text-muted">Auto-sync scheduled meetings</p>
                  </div>
                </div>
                <span className="px-2 py-0.5 text-[10px] font-bold rounded-full bg-purple-500/20 text-purple-400 border border-purple-500/30">
                  Coming Soon
                </span>
              </div>
              <p className="text-xs text-brand-text-muted leading-relaxed">
                Automatically trigger meeting recording and task extraction for events on your Google Calendar.
              </p>
              <button
                disabled
                className="w-full py-2 px-3 text-xs font-semibold bg-brand-surface-low border border-brand-border text-brand-text-muted rounded-lg cursor-not-allowed opacity-60 flex items-center justify-center gap-2"
              >
                <Calendar className="w-3.5 h-3.5" /> Connect Google Calendar
              </button>
            </div>

            {/* Section 3: Proposal Review Shortcut */}
            <div
              onClick={() => setIsProposalsModalOpen(true)}
              className="bg-brand-surface border border-brand-border rounded-2xl p-6 flex flex-col justify-between gap-4 hover:border-emerald-500/50 cursor-pointer shadow-xs hover:shadow-md transition-all"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 shrink-0">
                    <Sparkles className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-brand-text">AI Task Proposals</h3>
                    <p className="text-xs text-brand-text-muted">Review & Approve</p>
                  </div>
                </div>
                {pendingProposalsCount > 0 && (
                  <span className="px-2.5 py-1 text-[11px] font-bold rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 animate-pulse">
                    {pendingProposalsCount} Pending
                  </span>
                )}
              </div>
              <p className="text-xs text-brand-text-muted leading-relaxed">
                Pending action items extracted from completed meetings are waiting for board assignment and manager approval.
              </p>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setIsProposalsModalOpen(true);
                }}
                className="w-full py-2 px-3 text-xs font-semibold bg-emerald-500/10 border border-emerald-500/30 hover:bg-emerald-500/20 text-emerald-400 rounded-lg flex items-center justify-center gap-2 transition-colors cursor-pointer"
              >
                <Sparkles className="w-3.5 h-3.5" /> Review Proposals ({pendingProposalsCount})
              </button>
            </div>
          </div>

          {/* Recent Meetings Section */}
          <section className="bg-brand-surface border border-brand-border rounded-2xl p-6 space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-base font-bold text-brand-text flex items-center gap-2">
                <Video className="w-4 h-4 text-brand-primary" /> Recent Meeting Sessions
              </h2>
              <span className="text-xs text-brand-text-muted">
                {recentSessions.length} session{recentSessions.length !== 1 ? 's' : ''} recorded
              </span>
            </div>

            {isLoadingSessions ? (
              <div className="py-8 text-center text-xs text-brand-text-muted flex items-center justify-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin text-brand-primary" /> Loading recent sessions...
              </div>
            ) : recentSessions.length === 0 ? (
              <div className="py-8 text-center text-xs text-brand-text-muted border border-dashed border-brand-border rounded-xl">
                No meeting sessions recorded yet for this organization.
              </div>
            ) : (
              <div className="divide-y divide-brand-border/60 border border-brand-border rounded-xl overflow-hidden">
                {recentSessions.slice(0, 10).map((session) => {
                  const displayTitle = session.meeting_url?.trim() || `Google Meet Session (${(session.session_id || session.id || '').substring(0, 8)})`;
                  const targetUrl = session.meeting_url?.trim() || '#';

                  return (
                    <div
                      key={session.id}
                      className="p-3.5 flex items-center justify-between gap-4 hover:bg-brand-surface-low/50 transition-colors text-xs"
                    >
                      <div className="flex items-center gap-3 min-w-0 flex-1">
                        <span
                          className={`px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase shrink-0 ${
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
                            className="font-mono text-brand-text hover:text-brand-primary truncate flex items-center gap-1 font-medium"
                          >
                            {displayTitle} <ExternalLink className="w-3 h-3 shrink-0" />
                          </a>
                        ) : (
                          <span className="font-mono text-brand-text font-medium truncate">
                            {displayTitle}
                          </span>
                        )}
                      </div>

                      <div className="flex items-center gap-3 shrink-0 text-brand-text-muted">
                        <span className="capitalize px-2 py-0.5 rounded-md bg-brand-surface-low border border-brand-border text-brand-text">
                          {session.status}
                        </span>
                        <span>{new Date(session.created_at).toLocaleDateString()}</span>

                        <button
                          onClick={() => handleDeleteSession(session.id || session.session_id)}
                          className="p-1.5 text-brand-text-muted hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors cursor-pointer"
                          title="Delete Meeting Record"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </section>
        </>
      )}

      {/* Projects Search & Controls Header */}
      <section className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 pt-4 border-t border-brand-border">
        <h2 className="text-lg font-bold text-brand-text">Active Projects</h2>

        <div className="flex items-center gap-3 w-full sm:w-auto">
          <div className="relative flex-1 sm:w-64">
            <Search
              size={16}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-brand-outline"
            />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search projects..."
              className="w-full pl-9 pr-4 py-2 bg-brand-surface border border-brand-border rounded-full text-xs outline-none focus:border-brand-primary transition-colors"
            />
          </div>

          {user?.role !== 'MEMBER' && (
            <button
              onClick={openCreateProjectModal}
              className="bg-brand-primary hover:bg-brand-primary/90 text-white px-4 py-2 rounded-full text-xs font-semibold flex items-center gap-1.5 transition-colors shrink-0 cursor-pointer"
            >
              <Plus size={15} /> Create Project
            </button>
          )}
        </div>
      </section>

      {/* Active Projects Grid */}
      <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
        {isFetching ? (
          <div className="col-span-full h-48 flex flex-col items-center justify-center text-brand-text-muted">
            <Loader2 className="w-7 h-7 animate-spin mb-3 text-brand-primary opacity-50" />
            <p className="text-xs">Loading projects...</p>
          </div>
        ) : filteredActiveBoards.length === 0 ? (
          <div className="col-span-full">
            <EmptyState
              icon={<Folder size={48} />}
              title={
                search
                  ? 'No active projects found.'
                  : `${profile?.name || 'Your Workspace'} doesn't have any projects yet.`
              }
              description={
                search
                  ? 'Try adjusting your search query.'
                  : 'Create your first project to get started.'
              }
              action={
                !search && user?.role !== 'MEMBER' ? (
                  <button
                    onClick={openCreateProjectModal}
                    className="bg-brand-primary hover:bg-brand-primary/90 text-white px-5 py-2.5 rounded-full text-xs font-medium transition-colors cursor-pointer"
                  >
                    Create Project
                  </button>
                ) : undefined
              }
            />
          </div>
        ) : (
          filteredActiveBoards.map((board: any) => (
            <ProjectCard
              key={board.id}
              board={board}
              className="shadow-sm hover:shadow-md"
            />
          ))
        )}
      </section>

      {/* Archived Projects Section */}
      {filteredArchivedBoards.length > 0 && (
        <section className="pt-8 border-t border-brand-border space-y-6 pb-24">
          <div>
            <h2 className="text-lg font-bold text-brand-text">Archived Projects</h2>
            <p className="text-xs text-brand-text-muted mt-0.5">
              Read-only view of projects that have been archived.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {filteredArchivedBoards.map((board: any) => (
              <div
                key={board.id}
                className="opacity-70 grayscale-[30%] pointer-events-none"
              >
                <ProjectCard
                  board={board}
                  isLink={false}
                  className="shadow-sm"
                />
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Join Meeting Modal */}
      <JoinMeetingModal
        isOpen={isJoinModalOpen}
        onClose={() => setIsJoinModalOpen(false)}
      />

      {/* Global AI Task Proposals Modal */}
      <GlobalProposalsModal
        isOpen={isProposalsModalOpen}
        onClose={() => setIsProposalsModalOpen(false)}
        onProposalsUpdated={fetchProposalsCount}
      />
    </div>
  );
};

export default DashboardView;
