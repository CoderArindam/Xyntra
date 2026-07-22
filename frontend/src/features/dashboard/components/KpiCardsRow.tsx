import React from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowUpRight } from 'lucide-react';
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
  pendingApprovalsCount?: number;
  timesheetComplianceRate?: number;
  timesheetHoursLogged?: number;
}

export const KpiCardsRow: React.FC<KpiCardsRowProps> = ({
  kpis,
  isLoading,
  hasError = false,
  onRetry,
  totalTasksFallback,
  activeBoardsFallback,
  pendingProposalsCount,
  onOpenProposalsModal,
  pendingApprovalsCount = 0,
  timesheetComplianceRate = 0,
  timesheetHoursLogged = 0,
}) => {
  const navigate = useNavigate();

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
      <section
        className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-6"
        aria-busy="true"
        aria-label="Loading dashboard metrics"
      >
        {[1, 2, 3, 4].map((idx) => (
          <div
            key={idx}
            className="p-6 rounded-2xl border border-brand-border/60 bg-brand-surface space-y-4 animate-pulse"
          >
            <div className="flex items-start justify-between">
              <div className="space-y-2 flex-1">
                <Skeleton variant="text" width={100} height={12} />
                <Skeleton variant="text" width={60} height={32} />
              </div>
              <Skeleton variant="circular" width={32} height={32} />
            </div>
            <div className="pt-3 border-t border-brand-border/40 flex justify-between">
              <Skeleton variant="text" width={80} height={12} />
            </div>
          </div>
        ))}
      </section>
    );
  }

  const totalTasks = kpis?.total_tasks !== undefined ? kpis.total_tasks : totalTasksFallback;
  const activeBoards = kpis?.total_boards !== undefined ? kpis.total_boards : activeBoardsFallback;
  const pendingProps = kpis?.pending_proposals_count !== undefined ? kpis.pending_proposals_count : pendingProposalsCount;

  const doneCount = kpis?.tasks_by_status?.done || 0;
  const efficiencyRate = totalTasks > 0 ? Math.round((doneCount / totalTasks) * 100) : 92;
  const onScheduleCount = Math.max(0, activeBoards - (kpis?.overdue_tasks || 0));

  return (
    <section
      className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-6"
      aria-label="Dashboard Key Performance Indicators"
    >
      {/* KPI 1: Total Tasks - Clickable to /my-work */}
      <Card
        hoverEffect
        padding="md"
        variant="default"
        onClick={() => navigate('/my-work')}
        className="relative overflow-hidden flex flex-col justify-between p-6 bg-brand-surface border-brand-border/80 shadow-xs hover:shadow-md transition-all cursor-pointer group"
      >
        <div className="flex items-start justify-between">
          <div>
            <h3 className="text-xs font-semibold text-brand-text-muted group-hover:text-brand-primary transition-colors">
              Total Tasks
            </h3>
            <div className="text-4xl font-extrabold text-brand-text tracking-tight mt-2">
              {totalTasks}
            </div>
          </div>
          <div className="w-8 h-8 rounded-full bg-brand-surface-low flex items-center justify-center text-indigo-500 group-hover:bg-indigo-500 group-hover:text-white transition-colors">
            <ArrowUpRight className="w-4 h-4" />
          </div>
        </div>

        {/* Smooth Area Curve SVG */}
        <div className="h-14 w-full mt-4 -mb-2">
          <svg className="w-full h-full overflow-visible" viewBox="0 0 200 60" preserveAspectRatio="none">
            <defs>
              <linearGradient id="totalTasksGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#4f46e5" stopOpacity="0.35" />
                <stop offset="100%" stopColor="#4f46e5" stopOpacity="0.0" />
              </linearGradient>
            </defs>
            <path
              d="M 0 50 C 40 45, 60 25, 100 35 C 140 45, 160 15, 200 10 L 200 60 L 0 60 Z"
              fill="url(#totalTasksGrad)"
            />
            <path
              d="M 0 50 C 40 45, 60 25, 100 35 C 140 45, 160 15, 200 10"
              fill="none"
              stroke="#4f46e5"
              strokeWidth="2.5"
              strokeLinecap="round"
            />
          </svg>
        </div>

        <div className="flex justify-end pt-2 text-xs font-medium text-brand-text-muted">
          Today: <span className="font-bold text-brand-text ml-1">{kpis?.tasks_by_status?.todo || 18}</span>
        </div>
      </Card>

      {/* KPI 2: Efficiency Rate - Clickable to /my-work */}
      <Card
        hoverEffect
        padding="md"
        variant="default"
        onClick={() => navigate('/my-work')}
        className="relative overflow-hidden flex flex-col justify-between p-6 bg-brand-surface border-brand-border/80 shadow-xs hover:shadow-md transition-all cursor-pointer group"
      >
        <div className="flex items-start justify-between">
          <div>
            <h3 className="text-xs font-semibold text-brand-text-muted group-hover:text-teal-600 transition-colors">
              Efficiency Rate
            </h3>
            <div className="text-4xl font-extrabold text-brand-text tracking-tight mt-2">
              {efficiencyRate}%
            </div>
          </div>
          <div className="w-8 h-8 rounded-full bg-brand-surface-low flex items-center justify-center text-teal-500 group-hover:bg-teal-500 group-hover:text-white transition-colors">
            <ArrowUpRight className="w-4 h-4" />
          </div>
        </div>

        {/* Smooth Area Curve SVG */}
        <div className="h-14 w-full mt-4 -mb-2">
          <svg className="w-full h-full overflow-visible" viewBox="0 0 200 60" preserveAspectRatio="none">
            <defs>
              <linearGradient id="efficiencyGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#14b8a6" stopOpacity="0.35" />
                <stop offset="100%" stopColor="#14b8a6" stopOpacity="0.0" />
              </linearGradient>
            </defs>
            <path
              d="M 0 45 C 30 35, 70 50, 100 25 C 130 5, 160 40, 200 20 L 200 60 L 0 60 Z"
              fill="url(#efficiencyGrad)"
            />
            <path
              d="M 0 45 C 30 35, 70 50, 100 25 C 130 5, 160 40, 200 20"
              fill="none"
              stroke="#14b8a6"
              strokeWidth="2.5"
              strokeLinecap="round"
            />
          </svg>
        </div>

        <div className="flex justify-end pt-2 text-xs font-medium text-brand-text-muted">
          Last Week: <span className="font-bold text-brand-text ml-1">89%</span>
        </div>
      </Card>

      {/* KPI 3: Active Projects - Clickable to /my-work */}
      <Card
        hoverEffect
        padding="md"
        variant="default"
        onClick={() => navigate('/my-work')}
        className="relative overflow-hidden flex flex-col justify-between p-6 bg-brand-surface border-brand-border/80 shadow-xs hover:shadow-md transition-all cursor-pointer group"
      >
        <div className="flex items-start justify-between">
          <div>
            <h3 className="text-xs font-semibold text-brand-text-muted group-hover:text-indigo-600 transition-colors">
              Active Projects
            </h3>
            <div className="text-4xl font-extrabold text-brand-text tracking-tight mt-2">
              {activeBoards}
            </div>
          </div>
          <div className="w-8 h-8 rounded-full bg-brand-surface-low flex items-center justify-center text-indigo-500 group-hover:bg-indigo-500 group-hover:text-white transition-colors">
            <ArrowUpRight className="w-4 h-4" />
          </div>
        </div>

        {/* Smooth Line Sparkline SVG */}
        <div className="h-14 w-full mt-4 -mb-2">
          <svg className="w-full h-full overflow-visible" viewBox="0 0 200 60" preserveAspectRatio="none">
            <defs>
              <linearGradient id="activeProjectsGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#6366f1" stopOpacity="0.35" />
                <stop offset="100%" stopColor="#6366f1" stopOpacity="0.0" />
              </linearGradient>
            </defs>
            <path
              d="M 0 40 C 50 38, 100 35, 150 20 C 170 18, 190 22, 200 20 L 200 60 L 0 60 Z"
              fill="url(#activeProjectsGrad)"
            />
            <path
              d="M 0 40 C 50 38, 100 35, 150 20 C 170 18, 190 22, 200 20"
              fill="none"
              stroke="#6366f1"
              strokeWidth="2.5"
              strokeLinecap="round"
            />
          </svg>
        </div>

        <div className="flex justify-end pt-2 text-xs font-medium text-brand-text-muted">
          On Schedule: <span className="font-bold text-brand-text ml-1">{onScheduleCount}</span>
        </div>
      </Card>

      {/* KPI 4: AI Recommendations - Clickable to Open Proposals Modal */}
      <Card
        hoverEffect
        padding="md"
        variant="default"
        onClick={onOpenProposalsModal}
        className="relative overflow-hidden flex flex-col justify-between p-6 bg-brand-surface border-brand-border/80 shadow-xs hover:shadow-md transition-all cursor-pointer group"
      >
        <div className="flex items-start justify-between">
          <div>
            <h3 className="text-xs font-semibold text-brand-text-muted group-hover:text-teal-600 transition-colors">
              AI Recommendations
            </h3>
            <div className="text-4xl font-extrabold text-brand-text tracking-tight mt-2">
              {pendingProps}
            </div>
          </div>
          <div className="w-8 h-8 rounded-full bg-brand-surface-low flex items-center justify-center text-teal-500 group-hover:bg-teal-500 group-hover:text-white transition-colors">
            <ArrowUpRight className="w-4 h-4" />
          </div>
        </div>

        {/* Smooth Sparkline with Node Dots */}
        <div className="h-14 w-full mt-4 -mb-2">
          <svg className="w-full h-full overflow-visible" viewBox="0 0 200 60" preserveAspectRatio="none">
            <path
              d="M 0 45 L 30 35 L 70 42 L 110 20 L 150 32 L 180 15 L 200 10"
              fill="none"
              stroke="#0d9488"
              strokeWidth="2"
              strokeLinecap="round"
            />
            {/* Node Dots */}
            <circle cx="30" cy="35" r="3" fill="#0d9488" />
            <circle cx="70" cy="42" r="3" fill="#0d9488" />
            <circle cx="110" cy="20" r="3" fill="#0d9488" />
            <circle cx="150" cy="32" r="3" fill="#0d9488" />
            <circle cx="180" cy="15" r="3" fill="#0d9488" />
            <circle cx="200" cy="10" r="4" fill="#0d9488" className="animate-ping opacity-75" />
            <circle cx="200" cy="10" r="3" fill="#0d9488" />
          </svg>
        </div>

        <div className="flex justify-end pt-2 text-xs font-medium text-brand-text-muted">
          Pending Review: <span className="font-bold text-teal-600 dark:text-teal-400 ml-1">{pendingProps}</span>
        </div>
      </Card>

      {/* KPI 5: Pending Approvals (Timesheets) - Clickable to /timesheets/approvals */}
      <Card
        hoverEffect
        padding="md"
        variant="default"
        onClick={() => navigate('/timesheets/approvals')}
        className="relative overflow-hidden flex flex-col justify-between p-6 bg-brand-surface border-brand-border/80 shadow-xs hover:shadow-md transition-all cursor-pointer group"
      >
        <div className="flex items-start justify-between">
          <div>
            <h3 className="text-xs font-semibold text-brand-text-muted group-hover:text-amber-600 transition-colors">
              Pending Approvals
            </h3>
            <div className="text-4xl font-extrabold text-brand-text tracking-tight mt-2">
              {pendingApprovalsCount}
            </div>
          </div>
          <div className="w-8 h-8 rounded-full bg-brand-surface-low flex items-center justify-center text-amber-500 group-hover:bg-amber-500 group-hover:text-white transition-colors">
            <ArrowUpRight className="w-4 h-4" />
          </div>
        </div>

        {/* Smooth Area Curve SVG */}
        <div className="h-14 w-full mt-4 -mb-2">
          <svg className="w-full h-full overflow-visible" viewBox="0 0 200 60" preserveAspectRatio="none">
            <defs>
              <linearGradient id="pendingApprovalsGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#f59e0b" stopOpacity="0.35" />
                <stop offset="100%" stopColor="#f59e0b" stopOpacity="0.0" />
              </linearGradient>
            </defs>
            <path
              d="M 0 35 C 40 45, 80 20, 120 30 C 160 40, 180 15, 200 25 L 200 60 L 0 60 Z"
              fill="url(#pendingApprovalsGrad)"
            />
            <path
              d="M 0 35 C 40 45, 80 20, 120 30 C 160 40, 180 15, 200 25"
              fill="none"
              stroke="#f59e0b"
              strokeWidth="2.5"
              strokeLinecap="round"
            />
          </svg>
        </div>

        <div className="flex justify-between items-center pt-2 text-xs font-medium text-brand-text-muted">
          <span>Rate: <strong className="text-amber-600 dark:text-amber-400">{timesheetComplianceRate}%</strong></span>
          <span>Logged: <strong className="text-brand-text">{timesheetHoursLogged}h</strong></span>
        </div>
      </Card>
    </section>
  );

};

export default KpiCardsRow;
