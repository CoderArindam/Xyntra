import React, { useEffect, useState } from 'react';
import {
  Video,
  Sparkles,
  Loader2,
  Search,
  Folder,
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
import {
  getDashboardSummary,
  type DashboardKPIs,
  type DashboardBoardSummary,
  type DashboardActivityItem,
} from '../../services/dashboardApi';
import { Card } from '../../components/ui/Card';

// Widgets
import { KpiCardsRow } from './components/KpiCardsRow';
import { BoardsOverviewWidget } from './components/BoardsOverviewWidget';
import { RecentActivityWidget } from './components/RecentActivityWidget';
import { QuickActionsWidget } from './components/QuickActionsWidget';
import { RecentMeetingsWidget } from './components/RecentMeetingsWidget';
import { PendingProposalsWidget } from './components/PendingProposalsWidget';

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
  const [hasSessionsError, setHasSessionsError] = useState(false);

  const [isProposalsModalOpen, setIsProposalsModalOpen] = useState(false);
  const [pendingProposalsCount, setPendingProposalsCount] = useState<number>(0);

  // Dashboard summary API state powered by GET /api/v1/dashboard/summary
  const [kpis, setKpis] = useState<DashboardKPIs | null>(null);
  const [summaryBoards, setSummaryBoards] = useState<DashboardBoardSummary[]>([]);
  const [recentActivities, setRecentActivities] = useState<DashboardActivityItem[]>([]);
  const [isLoadingSummary, setIsLoadingSummary] = useState<boolean>(false);
  const [hasSummaryError, setHasSummaryError] = useState<boolean>(false);

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

  // Single primary API call to GET /api/v1/dashboard/summary with per-widget error boundary support
  const fetchSummaryData = React.useCallback(async () => {
    if (!isManagerOrAdmin) return;
    setIsLoadingSummary(true);
    setHasSummaryError(false);
    try {
      const summary = await getDashboardSummary();
      if (summary) {
        setKpis(summary.kpis);
        setSummaryBoards(summary.boards);
        setRecentActivities(summary.recent_activity);
        if (summary.kpis.pending_proposals_count !== undefined) {
          setPendingProposalsCount(summary.kpis.pending_proposals_count);
        }
      }
    } catch (err) {
      console.error('Failed to load dashboard summary:', err);
      setHasSummaryError(true);
    } finally {
      setIsLoadingSummary(false);
    }
  }, [isManagerOrAdmin]);

  useEffect(() => {
    fetchBoards();
  }, [fetchBoards]);

  useEffect(() => {
    fetchProposalsCount();
    fetchSummaryData();
  }, [fetchProposalsCount, fetchSummaryData]);

  // Meeting sessions query call with error handling
  const fetchSessions = React.useCallback(async () => {
    if (!isManagerOrAdmin) return;
    setIsLoadingSessions(true);
    setHasSessionsError(false);
    try {
      const data = await listRecentMeetingSessions(5);
      setRecentSessions(data);
    } catch (err) {
      console.error('Failed to load recent meeting sessions:', err);
      setHasSessionsError(true);
    } finally {
      setIsLoadingSessions(false);
    }
  }, [isManagerOrAdmin]);

  useEffect(() => {
    fetchSessions();
  }, [fetchSessions]);

  const filteredActiveBoards = activeBoards.filter((board: any) =>
    board.name.toLowerCase().includes(search.toLowerCase())
  );

  const filteredArchivedBoards = archivedBoards.filter((board: any) =>
    board.name.toLowerCase().includes(search.toLowerCase())
  );

  const handleDeleteSession = async (sessionId: string) => {
    try {
      await deleteMeetingSession(sessionId);
      setRecentSessions((prev) =>
        prev.filter((s) => s.id !== sessionId && s.session_id !== sessionId)
      );
    } catch (err) {
      console.error('Failed to delete meeting session:', err);
    }
  };

  return (
    <div className="max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8 animate-fade-in">
      {/* 1. Top Welcome Banner Card */}
      <Card variant="glass" padding="lg" className="border-brand-border/80 relative overflow-hidden">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 relative z-10">
          <div className="space-y-1.5">
            <div className="flex items-center gap-2">
              <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold uppercase tracking-wider bg-brand-primary/10 text-brand-primary border border-brand-primary/20">
                {isManagerOrAdmin ? (userRole === 'SUPER_ADMIN' ? 'Superadmin View' : 'Manager Dashboard') : 'Member Workspace'}
              </span>
              <span className="text-xs text-brand-text-muted">· {profile?.name || 'Workspace'}</span>
            </div>
            <h1 className="text-2xl lg:text-3xl font-extrabold tracking-tight text-brand-text">
              Welcome back, {user?.first_name || user?.email?.split('@')[0] || 'User'}
            </h1>
            <p className="text-xs sm:text-sm text-brand-text-muted max-w-2xl">
              AI Kanban Orchestration, Real-time Task Monitoring & Meeting Automation
            </p>
          </div>

          {isManagerOrAdmin && (
            <div className="flex items-center flex-wrap gap-3 shrink-0">
              <button
                onClick={() => setIsJoinModalOpen(true)}
                className="bg-brand-primary hover:bg-brand-primary-hover text-white px-5 py-2.5 rounded-xl text-xs sm:text-sm font-semibold flex items-center gap-2 transition-all shadow-xs hover:shadow-md cursor-pointer focus:ring-2 focus:ring-brand-primary focus:outline-none"
                aria-label="Start or join a Google Meet session"
              >
                <Video className="w-4 h-4" aria-hidden="true" /> Start / Join Meeting
              </button>
              {pendingProposalsCount > 0 && (
                <button
                  onClick={() => setIsProposalsModalOpen(true)}
                  className="bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 px-4 py-2.5 rounded-xl text-xs sm:text-sm font-semibold flex items-center gap-2 transition-all cursor-pointer focus:ring-2 focus:ring-emerald-400 focus:outline-none"
                  aria-label="Open AI task proposals review queue"
                >
                  <Sparkles className="w-4 h-4 text-emerald-400" aria-hidden="true" /> Proposals ({pendingProposalsCount})
                </button>
              )}
            </div>
          )}
        </div>
      </Card>

      {/* MEMBER ROLE VIEW: Reduced Streamlined Layout */}
      {!isManagerOrAdmin ? (
        <div className="space-y-8">
          <section className="space-y-6" aria-label="Member Active Projects">
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
              <div>
                <h2 className="text-lg font-bold text-brand-text">Active Projects</h2>
                <p className="text-xs text-brand-text-muted">Your assigned Kanban boards</p>
              </div>

              <div className="relative w-full sm:w-64">
                <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-brand-outline" aria-hidden="true" />
                <input
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Search projects..."
                  className="w-full pl-9 pr-4 py-2 bg-brand-surface border border-brand-border rounded-full text-xs outline-none focus:border-brand-primary transition-colors text-brand-text placeholder:text-brand-text-muted"
                  aria-label="Search assigned projects"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
              {isFetching ? (
                <div className="col-span-full h-48 flex flex-col items-center justify-center text-brand-text-muted">
                  <Loader2 className="w-7 h-7 animate-spin mb-3 text-brand-primary opacity-50" />
                  <p className="text-xs">Loading projects...</p>
                </div>
              ) : filteredActiveBoards.length === 0 ? (
                <div className="col-span-full">
                  <EmptyState
                    icon={<Folder size={48} />}
                    title={search ? 'No matching projects.' : 'No active projects yet.'}
                    description="You will see your assigned projects here."
                  />
                </div>
              ) : (
                filteredActiveBoards.map((board: any) => (
                  <ProjectCard key={board.id} board={board} className="shadow-xs hover:shadow-md" />
                ))
              )}
            </div>
          </section>
        </div>
      ) : (
        /* MANAGER / SUPERADMIN FULL WIDGET LAYOUT */
        <div className="space-y-8">
          {/* 1. KPI Cards Row */}
          <KpiCardsRow
            kpis={kpis}
            isLoading={isLoadingSummary}
            hasError={hasSummaryError}
            onRetry={fetchSummaryData}
            totalTasksFallback={activeBoards.reduce((acc: number, b: any) => acc + (b.task_count || 0), 0)}
            activeBoardsFallback={activeBoards.length}
            pendingProposalsCount={pendingProposalsCount}
            organizationName={profile?.name}
            onOpenProposalsModal={() => setIsProposalsModalOpen(true)}
          />

          {/* 2. Two-Column Main Layout Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
            {/* LEFT / PRIMARY COLUMN (8 cols out of 12) */}
            <div className="lg:col-span-8 space-y-8">
              {/* Widget 2: Boards Overview Widget */}
              <BoardsOverviewWidget
                summaryBoards={summaryBoards}
                activeBoardsFallback={activeBoards}
                isFetching={isFetching || isLoadingSummary}
                hasError={hasSummaryError}
                onRetry={fetchSummaryData}
                onOpenCreateProjectModal={openCreateProjectModal}
              />

              {/* Widget 3: Recent Activity Widget */}
              <RecentActivityWidget
                activities={recentActivities}
                isLoading={isLoadingSummary}
                hasError={hasSummaryError}
                onRetry={fetchSummaryData}
              />
            </div>

            {/* RIGHT / SIDEBAR COLUMN (4 cols out of 12) */}
            <div className="lg:col-span-4 space-y-8">
              {/* Widget 6: Quick Actions Widget */}
              <QuickActionsWidget
                userRole={userRole}
                pendingPropsCount={pendingProposalsCount}
                onOpenJoinModal={() => setIsJoinModalOpen(true)}
                onOpenProposalsModal={() => setIsProposalsModalOpen(true)}
                onOpenCreateProjectModal={openCreateProjectModal}
              />

              {/* Widget 4: Recent Meetings Widget */}
              <RecentMeetingsWidget
                sessions={recentSessions}
                isLoading={isLoadingSessions}
                hasError={hasSessionsError}
                onRetry={fetchSessions}
                pendingPropsCount={pendingProposalsCount}
                onDeleteSession={handleDeleteSession}
                onOpenJoinModal={() => setIsJoinModalOpen(true)}
                onOpenProposalsModal={() => setIsProposalsModalOpen(true)}
              />

              {/* Widget 5: Pending Task Proposals Widget */}
              <PendingProposalsWidget
                pendingPropsCount={pendingProposalsCount}
                onOpenProposalsModal={() => setIsProposalsModalOpen(true)}
              />
            </div>
          </div>
        </div>
      )}

      {/* Archived Projects Section */}
      {filteredArchivedBoards.length > 0 && (
        <section className="pt-8 border-t border-brand-border space-y-6 pb-24" aria-label="Archived Projects">
          <div>
            <h2 className="text-lg font-bold text-brand-text">Archived Projects</h2>
            <p className="text-xs text-brand-text-muted mt-0.5">
              Read-only view of projects that have been archived.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {filteredArchivedBoards.map((board: any) => (
              <div key={board.id} className="opacity-70 grayscale-[30%] pointer-events-none">
                <ProjectCard board={board} isLink={false} className="shadow-xs" />
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Modals */}
      <JoinMeetingModal isOpen={isJoinModalOpen} onClose={() => setIsJoinModalOpen(false)} />

      <GlobalProposalsModal
        isOpen={isProposalsModalOpen}
        onClose={() => setIsProposalsModalOpen(false)}
        onProposalsUpdated={() => {
          fetchProposalsCount();
          fetchSummaryData();
          fetchSessions();
        }}
      />
    </div>
  );
};

export default DashboardView;
