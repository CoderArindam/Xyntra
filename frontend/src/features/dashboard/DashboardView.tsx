import React, { useEffect, useState } from 'react';
import { Video, Sparkles, Loader2, Search, Folder } from 'lucide-react';
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
import { getApprovalQueueSummary } from '../../services/timesheetApprovalService';
import { getOrgSummaryReport } from '../../services/timesheetReportsApi';
import { isManagerOrAdmin } from '../../lib/rbac';

// Widgets
import { KpiCardsRow } from './components/KpiCardsRow';
import { StrategicProjectsWidget } from './components/StrategicProjectsWidget';
import { FocusTasksWidget } from './components/FocusTasksWidget';
import { SmartSuggestionsWidget } from './components/SmartSuggestionsWidget';
import { RecentActivityWidget } from './components/RecentActivityWidget';
import { QuickActionsWidget } from './components/QuickActionsWidget';
import { RecentMeetingsWidget } from './components/RecentMeetingsWidget';

const getGreeting = () => {
  const hour = new Date().getHours();
  if (hour < 12) return 'Good morning';
  if (hour < 18) return 'Good afternoon';
  return 'Good evening';
};

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
  const [isLoadingSessions, setIsLoadingSessions] = useState<boolean>(false);

  const [isProposalsModalOpen, setIsProposalsModalOpen] = useState(false);
  const [pendingProposalsCount, setPendingProposalsCount] = useState<number>(4);

  // Dashboard summary API state
  const [kpis, setKpis] = useState<DashboardKPIs | null>(null);
  const [summaryBoards, setSummaryBoards] = useState<DashboardBoardSummary[]>([]);
  const [recentActivities, setRecentActivities] = useState<DashboardActivityItem[]>([]);
  const [isLoadingSummary, setIsLoadingSummary] = useState<boolean>(false);
  const [hasSummaryError, setHasSummaryError] = useState<boolean>(false);

  // Timesheet dashboard state
  const [pendingApprovalsCount, setPendingApprovalsCount] = useState<number>(0);
  const [timesheetComplianceRate, setTimesheetComplianceRate] = useState<number>(0);
  const [timesheetHoursLogged, setTimesheetHoursLogged] = useState<number>(0);

  // Single source of truth for role — uses lib/rbac which handles all casing variants
  const canAccessAdminFeatures = isManagerOrAdmin(user);

  const userName = user?.first_name || user?.email?.split('@')[0] || 'User';

  const fetchProposalsCount = React.useCallback(async () => {
    try {
      const data = await listOrgProposals('pending');
      if (data && data.length > 0) {
        setPendingProposalsCount(data.length);
      }
    } catch (err) {
      console.error('Failed to fetch org proposals count:', err);
    }
  }, []);

  const fetchSummaryData = React.useCallback(async () => {
    setIsLoadingSummary(true);
    setHasSummaryError(false);
    try {
      const summary = await getDashboardSummary();
      if (summary) {
        setKpis(summary.kpis);
        setSummaryBoards(summary.boards);
        setRecentActivities(summary.recent_activity);
        if (summary.kpis?.pending_proposals_count !== undefined) {
          setPendingProposalsCount(summary.kpis.pending_proposals_count);
        }
      }
    } catch (err) {
      console.error('Failed to load dashboard summary:', err);
      setHasSummaryError(true);
    } finally {
      setIsLoadingSummary(false);
    }
  }, []);

  const fetchTimesheetSummary = React.useCallback(async () => {
    try {
      const queueSummary = await getApprovalQueueSummary();
      if (queueSummary && queueSummary.pending_count !== undefined) {
        setPendingApprovalsCount(queueSummary.pending_count);
      }
    } catch (err) {
      console.error('Failed to load approval queue summary:', err);
    }

    try {
      const reports = await getOrgSummaryReport(1);
      if (reports && reports.length > 0) {
        setTimesheetComplianceRate(reports[0].compliance_rate || 0);
        setTimesheetHoursLogged(reports[0].total_hours_logged || 0);
      }
    } catch (err) {
      console.error('Failed to load org summary report:', err);
    }
  }, []);

  useEffect(() => {
    fetchBoards();
  }, [fetchBoards]);

  useEffect(() => {
    if (canAccessAdminFeatures) {
      fetchProposalsCount();
      fetchSummaryData();
      fetchTimesheetSummary();
    }
  }, [fetchProposalsCount, fetchSummaryData, fetchTimesheetSummary, canAccessAdminFeatures]);

  const fetchSessions = React.useCallback(async () => {
    setIsLoadingSessions(true);
    try {
      const data = await listRecentMeetingSessions(5);
      setRecentSessions(data || []);
    } catch (err) {
      console.error('Failed to load recent meeting sessions:', err);
    } finally {
      setIsLoadingSessions(false);
    }
  }, []);

  const handleDeleteSession = async (sessionId: string) => {
    try {
      await deleteMeetingSession(sessionId);
      setRecentSessions((prev) => prev.filter((s) => (s.id || s.session_id) !== sessionId));
    } catch (err) {
      console.error('Failed to delete session:', err);
    }
  };

  useEffect(() => {
    if (canAccessAdminFeatures) {
      fetchSessions();
    }
  }, [fetchSessions, canAccessAdminFeatures]);

  const filteredActiveBoards = activeBoards.filter((board: any) =>
    board.name.toLowerCase().includes(search.toLowerCase())
  );

  const filteredArchivedBoards = archivedBoards.filter((board: any) =>
    board.name.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8 animate-fade-in">
      {/* Header Greeting & Quick Actions — role-aware */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl lg:text-4xl font-extrabold tracking-tight text-brand-text">
            {getGreeting()}, {userName}
          </h1>
          {canAccessAdminFeatures ? (
            <p className="text-sm text-brand-text-muted mt-1 font-medium">
              Today: {pendingProposalsCount} new AI recommendations, {summaryBoards.length > 0 ? summaryBoards.filter(b => b.overdue_count === 0).length : Math.max(1, activeBoards.length)} projects on track, and {kpis && kpis.total_tasks > 0 ? Math.round(((kpis.tasks_by_status?.done || 0) / kpis.total_tasks) * 100) : 92}% efficiency rate.
            </p>
          ) : (
            <p className="text-sm text-brand-text-muted mt-1 font-medium">
              Here's an overview of your assigned projects and tasks.
            </p>
          )}
        </div>

        {/* Quick actions — only for managers and admins */}
        {canAccessAdminFeatures && (
          <div className="flex items-center flex-wrap gap-3 shrink-0">
            <button
              onClick={() => setIsJoinModalOpen(true)}
              className="bg-brand-primary hover:bg-brand-primary-hover text-white px-5 py-2.5 rounded-full text-xs sm:text-sm font-semibold flex items-center gap-2 transition-all shadow-xs hover:shadow-md cursor-pointer focus:ring-2 focus:ring-brand-primary focus:outline-none"
              aria-label="Start or Join Meeting"
            >
              <Video className="w-4 h-4" aria-hidden="true" />
              Start / Join Meeting
            </button>

            <button
              onClick={() => setIsProposalsModalOpen(true)}
              className="bg-teal-600 hover:bg-teal-700 text-white px-5 py-2.5 rounded-full text-xs sm:text-sm font-semibold flex items-center gap-2 transition-all shadow-xs hover:shadow-md cursor-pointer focus:ring-2 focus:ring-teal-500 focus:outline-none"
              aria-label="View AI Proposals"
            >
              <Sparkles className="w-4 h-4 text-white" aria-hidden="true" />
              View Proposals ({pendingProposalsCount})
            </button>
          </div>
        )}
      </div>

      {/* MEMBER ROLE VIEW (If non-manager) */}
      {!canAccessAdminFeatures ? (
        <div className="space-y-8">
          <section className="space-y-6" aria-label="Member Active Projects">
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
              <div>
                <h2 className="text-lg font-bold text-brand-text">Active Projects</h2>
                <p className="text-xs text-brand-text-muted">Your assigned Kanban boards</p>
              </div>

              <div className="relative w-full sm:w-64">
                <Search
                  size={16}
                  className="absolute left-3 top-1/2 -translate-y-1/2 text-brand-outline"
                  aria-hidden="true"
                />
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
        /* MANAGER & SUPERADMIN REDESIGNED DASHBOARD LAYOUT */
        <div className="space-y-8">
          {/* 1. KPI Cards Row with Sparklines */}
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
            pendingApprovalsCount={pendingApprovalsCount}
            timesheetComplianceRate={timesheetComplianceRate}
            timesheetHoursLogged={timesheetHoursLogged}
          />

          {/* 2. Main Content 2-Column Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
            {/* LEFT COLUMN (8 cols out of 12) */}
            <div className="lg:col-span-8 space-y-8">
              {/* Strategic Projects Overview */}
              <StrategicProjectsWidget
                summaryBoards={summaryBoards}
                activeBoardsFallback={activeBoards}
                isFetching={isFetching || isLoadingSummary}
                hasError={hasSummaryError}
                onRetry={fetchSummaryData}
                onOpenCreateProjectModal={openCreateProjectModal}
              />
            </div>

            {/* RIGHT COLUMN (4 cols out of 12) */}
            <div className="lg:col-span-4 space-y-8">
              {/* Quick Actions Widget */}
              <QuickActionsWidget
                userRole={user?.role || 'MEMBER'}
                pendingPropsCount={pendingProposalsCount}
                onOpenJoinModal={() => setIsJoinModalOpen(true)}
                onOpenProposalsModal={() => setIsProposalsModalOpen(true)}
                onOpenCreateProjectModal={openCreateProjectModal}
              />

              {/* Focus Tasks Widget */}
              <FocusTasksWidget
                pendingPropsCount={pendingProposalsCount}
                onOpenProposalsModal={() => setIsProposalsModalOpen(true)}
                summaryBoards={summaryBoards}
              />

              {/* Smart Suggestions Widget */}
              <SmartSuggestionsWidget
                summaryBoards={summaryBoards}
                onOpenJoinModal={() => setIsJoinModalOpen(true)}
                onOpenProposalsModal={() => setIsProposalsModalOpen(true)}
                onProposalProcessed={() => {
                  fetchProposalsCount();
                  fetchSummaryData();
                }}
              />

              {/* Recent Meetings Widget */}
              <RecentMeetingsWidget
                sessions={recentSessions}
                isLoading={isLoadingSessions}
                onRetry={fetchSessions}
                pendingPropsCount={pendingProposalsCount}
                onDeleteSession={handleDeleteSession}
                onOpenJoinModal={() => setIsJoinModalOpen(true)}
                onOpenProposalsModal={() => setIsProposalsModalOpen(true)}
              />

              {/* Recent Activity Widget */}
              <RecentActivityWidget
                activities={recentActivities}
                isLoading={isLoadingSummary}
                hasError={hasSummaryError}
                onRetry={fetchSummaryData}
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

