import React from 'react';
import {
  CheckCircle2,
  AlertTriangle,
  Clock,
  Kanban,
  Sparkles,
  ChevronRight,
} from 'lucide-react';
import { Card } from '../../../components/ui/Card';
import { Skeleton } from '../../../components/ui/Skeleton';
import { WidgetError } from '../../../components/ui/WidgetError';
import type { DashboardKPIs } from '../../../services/dashboardApi';

interface KpiCardsRowProps {
  kpis: DashboardKPIs | null;
  isLoading: boolean;
  hasError?: boolean;
  onRetry?: () => void;
  totalTasksFallback: number;
  activeBoardsFallback: number;
  pendingProposalsCount: number;
  organizationName?: string;
  onOpenProposalsModal: () => void;
}

export const KpiCardsRow: React.FC<KpiCardsRowProps> = ({
  kpis,
  isLoading,
  hasError = false,
  onRetry,
  totalTasksFallback,
  activeBoardsFallback,
  pendingProposalsCount,
  organizationName,
  onOpenProposalsModal,
}) => {
  if (hasError) {
    return (
      <section className="col-span-full">
        <WidgetError
          title="Could not load KPI metrics"
          message="Failed to connect to dashboard metrics service."
          onRetry={onRetry}
        />
      </section>
    );
  }

  if (isLoading && !kpis) {
    return (
      <section className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-6" aria-busy="true" aria-label="Loading dashboard metrics">
        {[1, 2, 3, 4].map((idx) => (
          <div key={idx} className="p-6 rounded-2xl border border-brand-border/60 bg-brand-surface space-y-4 animate-pulse">
            <div className="flex items-start justify-between">
              <div className="space-y-2 flex-1">
                <Skeleton variant="text" width={100} height={12} />
                <Skeleton variant="text" width={60} height={32} />
              </div>
              <Skeleton variant="circular" width={40} height={40} />
            </div>
            <div className="pt-3 border-t border-brand-border/40 flex justify-between">
              <Skeleton variant="text" width={80} height={12} />
              <Skeleton variant="text" width={60} height={12} />
            </div>
          </div>
        ))}
      </section>
    );
  }

  const totalTasks = kpis?.total_tasks ?? totalTasksFallback;
  const overdueTasks = kpis?.overdue_tasks ?? 0;
  const totalBoards = kpis?.total_boards ?? activeBoardsFallback;
  const teamSize = kpis?.team_size ?? 1;
  const pendingProps = kpis?.pending_proposals_count ?? pendingProposalsCount;
  const activeMeetings = kpis?.active_meetings_count ?? 0;

  const todoCount = kpis?.tasks_by_status?.todo ?? 0;
  const inProgressCount = kpis?.tasks_by_status?.in_progress ?? 0;
  const reviewCount = kpis?.tasks_by_status?.review ?? 0;
  const doneCount = kpis?.tasks_by_status?.done ?? 0;

  const safeTotal = totalTasks > 0 ? totalTasks : 1;
  const todoPct = Math.round((todoCount / safeTotal) * 100);
  const inProgressPct = Math.round((inProgressCount / safeTotal) * 100);
  const reviewPct = Math.round((reviewCount / safeTotal) * 100);
  const donePct = Math.round((doneCount / safeTotal) * 100);

  return (
    <section className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-6" aria-label="Dashboard Key Performance Indicators">
      {/* KPI 1: Total Tasks & Breakdown */}
      <Card hoverEffect padding="md" variant="default" className="flex flex-col justify-between">
        <div className="flex items-start justify-between">
          <div>
            <h3 className="text-xs font-semibold text-brand-text-muted uppercase tracking-wider">
              Total Org Tasks
            </h3>
            <div className="text-3xl lg:text-4xl font-extrabold text-brand-text tracking-tight mt-1" aria-label={`${totalTasks} total tasks`}>
              {totalTasks}
            </div>
          </div>
          <div className="w-10 h-10 rounded-xl bg-brand-primary/10 border border-brand-primary/20 flex items-center justify-center text-brand-primary shrink-0">
            <CheckCircle2 className="w-5 h-5" aria-hidden="true" />
          </div>
        </div>

        <div className="mt-4 pt-3 border-t border-brand-border/60 space-y-2">
          {totalTasks > 0 ? (
            <div className="h-2 w-full rounded-full bg-brand-surface-container overflow-hidden flex" aria-label="Status breakdown bar">
              <div style={{ width: `${todoPct}%` }} className="bg-blue-500" title={`Todo: ${todoCount}`} />
              <div style={{ width: `${inProgressPct}%` }} className="bg-amber-500" title={`In Progress: ${inProgressCount}`} />
              <div style={{ width: `${reviewPct}%` }} className="bg-purple-500" title={`Review: ${reviewCount}`} />
              <div style={{ width: `${donePct}%` }} className="bg-emerald-500" title={`Done: ${doneCount}`} />
            </div>
          ) : (
            <p className="text-[11px] text-brand-text-muted italic">No tasks created yet</p>
          )}

          <div className="flex items-center justify-between text-[11px]">
            <span className="text-blue-400 font-medium">Todo: {todoCount}</span>
            <span className="text-amber-400 font-medium">Prog: {inProgressCount}</span>
            <span className="text-purple-400 font-medium">Rev: {reviewCount}</span>
            <span className="text-emerald-400 font-medium">Done: {doneCount}</span>
          </div>
        </div>
      </Card>

      {/* KPI 2: Overdue Tasks (Urgent Warning Accent + Icon + Text Label for Accessibility) */}
      <Card
        hoverEffect
        padding="md"
        variant="default"
        className={`flex flex-col justify-between transition-all ${
          overdueTasks > 0
            ? 'border-red-500/40 bg-red-500/5 shadow-xs shadow-red-500/10'
            : ''
        }`}
      >
        <div className="flex items-start justify-between">
          <div>
            <h3 className="text-xs font-semibold text-brand-text-muted uppercase tracking-wider flex items-center gap-1.5">
              <span>Overdue Tasks</span>
              {overdueTasks > 0 && (
                <span className="px-1.5 py-0.2 rounded text-[9px] font-bold uppercase bg-red-500/20 text-red-400 border border-red-500/30">
                  Urgent
                </span>
              )}
            </h3>
            <div
              className={`text-3xl lg:text-4xl font-extrabold tracking-tight mt-1 ${
                overdueTasks > 0 ? 'text-red-500' : 'text-brand-text'
              }`}
              aria-label={`${overdueTasks} overdue tasks`}
            >
              {overdueTasks}
            </div>
          </div>
          <div
            className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 border ${
              overdueTasks > 0
                ? 'bg-red-500/20 border-red-500/30 text-red-500'
                : 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'
            }`}
          >
            {overdueTasks > 0 ? <AlertTriangle className="w-5 h-5" aria-hidden="true" /> : <Clock className="w-5 h-5" aria-hidden="true" />}
          </div>
        </div>

        <div className="mt-4 pt-3 border-t border-brand-border/60 flex items-center justify-between text-[11px]">
          <span className="text-brand-text-muted">Due date &lt; Now</span>
          <span
            className={`font-semibold px-2 py-0.5 rounded-full text-[10px] flex items-center gap-1 ${
              overdueTasks > 0
                ? 'bg-red-500/20 text-red-400 border border-red-500/30 font-bold'
                : 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
            }`}
          >
            {overdueTasks > 0 ? (
              <>
                <AlertTriangle className="w-3 h-3" aria-hidden="true" />
                <span>Action Required</span>
              </>
            ) : (
              <span>All On Schedule</span>
            )}
          </span>
        </div>
      </Card>

      {/* KPI 3: Workspace Scale (Boards & Team) */}
      <Card hoverEffect padding="md" variant="default" className="flex flex-col justify-between">
        <div className="flex items-start justify-between">
          <div>
            <h3 className="text-xs font-semibold text-brand-text-muted uppercase tracking-wider">
              Workspace Scale
            </h3>
            <div className="flex items-baseline gap-2 mt-1" aria-label={`${totalBoards} boards, ${teamSize} team members`}>
              <span className="text-3xl lg:text-4xl font-extrabold text-brand-text tracking-tight">
                {totalBoards}
              </span>
              <span className="text-xs text-brand-text-muted">boards</span>
              <span className="text-2xl font-bold text-brand-text ml-1">/ {teamSize}</span>
              <span className="text-xs text-brand-text-muted">team</span>
            </div>
          </div>
          <div className="w-10 h-10 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 shrink-0">
            <Kanban className="w-5 h-5" aria-hidden="true" />
          </div>
        </div>

        <div className="mt-4 pt-3 border-t border-brand-border/60 flex items-center justify-between text-[11px] text-brand-text-muted">
          <span>Organization</span>
          <span className="font-semibold text-brand-text truncate max-w-[120px]">
            {organizationName || 'Workspace'}
          </span>
        </div>
      </Card>

      {/* KPI 4: Pending AI Proposals & Active Meetings */}
      <Card hoverEffect padding="md" variant="default" className="flex flex-col justify-between">
        <div className="flex items-start justify-between">
          <div>
            <h3 className="text-xs font-semibold text-brand-text-muted uppercase tracking-wider">
              Pending AI Proposals
            </h3>
            <div className="flex items-center gap-2 mt-1">
              <span className="text-3xl lg:text-4xl font-extrabold text-emerald-400 tracking-tight" aria-label={`${pendingProps} pending task proposals`}>
                {pendingProps}
              </span>
              {pendingProps > 0 && (
                <span className="px-2 py-0.5 text-[10px] font-bold rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 animate-pulse">
                  Pending Review
                </span>
              )}
            </div>
          </div>
          <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 shrink-0">
            <Sparkles className="w-5 h-5" aria-hidden="true" />
          </div>
        </div>

        <div className="mt-4 pt-3 border-t border-brand-border/60 flex items-center justify-between text-[11px] text-brand-text-muted">
          <span>Active Meetings: {activeMeetings}</span>
          <button
            onClick={onOpenProposalsModal}
            className="font-semibold text-emerald-400 hover:underline flex items-center gap-0.5 cursor-pointer text-xs focus:outline-none focus:ring-1 focus:ring-emerald-400 rounded"
            aria-label="Review pending proposals queue"
          >
            Review Queue <ChevronRight className="w-3 h-3" aria-hidden="true" />
          </button>
        </div>
      </Card>
    </section>
  );
};
