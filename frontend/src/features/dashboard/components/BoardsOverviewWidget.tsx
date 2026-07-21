import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Kanban,
  Search,
  Plus,
  ChevronLeft,
  ChevronRight,
  FolderPlus,
  Users,
  AlertTriangle,
} from 'lucide-react';
import { Card, CardHeader, CardTitle, CardDescription } from '../../../components/ui/Card';
import { Skeleton } from '../../../components/ui/Skeleton';
import { WidgetError } from '../../../components/ui/WidgetError';
import type { DashboardBoardSummary } from '../../../services/dashboardApi';
import EmptyState from '../../../components/common/EmptyState';

interface BoardsOverviewWidgetProps {
  summaryBoards: DashboardBoardSummary[];
  activeBoardsFallback: any[];
  isFetching: boolean;
  hasError?: boolean;
  onRetry?: () => void;
  onOpenCreateProjectModal: () => void;
}

export const BoardsOverviewWidget: React.FC<BoardsOverviewWidgetProps> = ({
  summaryBoards,
  activeBoardsFallback,
  isFetching,
  hasError = false,
  onRetry,
  onOpenCreateProjectModal,
}) => {
  const [search, setSearch] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 6;

  // Use summary boards data if available, fallback to activeBoards
  const displayBoards = summaryBoards.length > 0
    ? summaryBoards.map((sb) => ({
        id: sb.id,
        name: sb.name,
        project_key: sb.project_key,
        description: sb.description,
        icon: sb.icon,
        color: sb.color,
        cover_gradient: sb.cover_gradient,
        task_count: sb.task_count,
        completed_task_count: sb.completed_task_count,
        completion_percentage: sb.completion_percentage,
        overdue_count: sb.overdue_count,
        member_count: sb.member_count,
      }))
    : activeBoardsFallback.map((ab) => ({
        id: ab.id,
        name: ab.name,
        project_key: ab.project_key,
        description: ab.description,
        icon: ab.icon,
        color: ab.color,
        cover_gradient: ab.cover_gradient,
        task_count: ab.task_count || 0,
        completed_task_count: 0,
        completion_percentage: 0,
        overdue_count: 0,
        member_count: ab.member_count || 1,
      }));

  const filteredBoards = displayBoards.filter((b) =>
    b.name.toLowerCase().includes(search.toLowerCase()) ||
    (b.project_key && b.project_key.toLowerCase().includes(search.toLowerCase()))
  );

  const totalPages = Math.ceil(filteredBoards.length / pageSize) || 1;
  const paginatedBoards = filteredBoards.slice(
    (currentPage - 1) * pageSize,
    currentPage * pageSize
  );

  return (
    <Card variant="default" padding="lg" className="space-y-6">
      <CardHeader className="flex-row items-center justify-between mb-0">
        <div className="space-y-1">
          <CardTitle>
            <Kanban className="w-5 h-5 text-brand-primary" aria-hidden="true" />
            <span>Boards & Projects Overview</span>
          </CardTitle>
          <CardDescription>
            Completion metrics, progress bars, and task distributions across all active projects
          </CardDescription>
        </div>

        <button
          onClick={onOpenCreateProjectModal}
          className="bg-brand-primary hover:bg-brand-primary-hover text-white px-3.5 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-colors shrink-0 cursor-pointer shadow-xs focus:ring-2 focus:ring-brand-primary focus:outline-none"
          aria-label="Create new project board"
        >
          <Plus size={14} aria-hidden="true" /> New Project
        </button>
      </CardHeader>

      {/* Filter / Search Bar */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div className="relative flex-1 w-full sm:w-auto">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-brand-outline" aria-hidden="true" />
          <input
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setCurrentPage(1);
            }}
            placeholder="Search projects by name or key..."
            className="w-full pl-9 pr-4 py-2 bg-brand-surface-low border border-brand-border rounded-lg text-xs outline-none focus:border-brand-primary transition-colors text-brand-text placeholder:text-brand-text-muted"
            aria-label="Search active boards"
          />
        </div>
        <span className="text-xs text-brand-text-muted shrink-0">
          Showing {paginatedBoards.length} of {filteredBoards.length} boards
        </span>
      </div>

      {/* Error Boundary State */}
      {hasError ? (
        <WidgetError
          title="Could not load boards"
          message="Failed to retrieve organization project boards."
          onRetry={onRetry}
        />
      ) : isFetching && displayBoards.length === 0 ? (
        /* Shape-accurate Skeleton Loading State */
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4" aria-busy="true" aria-label="Loading boards">
          {[1, 2, 3, 4].map((idx) => (
            <div key={idx} className="p-4 rounded-xl bg-brand-surface-low/50 border border-brand-border/60 space-y-3">
              <div className="flex justify-between items-center">
                <Skeleton variant="text" width={120} height={16} />
                <Skeleton variant="rectangular" width={40} height={16} />
              </div>
              <Skeleton variant="text" width="80%" height={12} />
              <div className="pt-2 border-t border-brand-border/40 space-y-1.5">
                <Skeleton variant="text" width="100%" height={8} />
                <div className="flex justify-between">
                  <Skeleton variant="text" width={60} height={10} />
                  <Skeleton variant="text" width={50} height={10} />
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : filteredBoards.length === 0 ? (
        /* Purposeful Empty State for 0 Boards */
        <EmptyState
          icon={<FolderPlus size={44} className="text-brand-primary/70" />}
          title={search ? 'No matching boards found.' : 'No active projects created yet'}
          description={
            search
              ? 'Try adjusting your search filter or project key query.'
              : 'Get started by creating your first Kanban project board to assign tasks and track team progress.'
          }
          action={
            !search ? (
              <button
                onClick={onOpenCreateProjectModal}
                className="bg-brand-primary hover:bg-brand-primary-hover text-white px-4 py-2 rounded-lg text-xs font-semibold shadow-xs flex items-center gap-1.5"
              >
                <Plus size={14} /> Create Your First Project
              </button>
            ) : undefined
          }
        />
      ) : (
        /* Boards Grid */
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {paginatedBoards.map((board) => {
            const completionPct = Math.min(100, Math.max(0, board.completion_percentage || 0));

            return (
              <Link
                key={board.id}
                to={`/board/${board.id}`}
                className="group p-4 rounded-xl bg-brand-surface-low/50 hover:bg-brand-surface-low border border-brand-border hover:border-brand-primary/50 transition-all space-y-3 flex flex-col justify-between focus:outline-none focus:ring-2 focus:ring-brand-primary"
                aria-label={`Board ${board.name}, ${board.completed_task_count || 0} of ${board.task_count || 0} tasks completed`}
              >
                <div>
                  <div className="flex items-center justify-between gap-2 mb-1.5">
                    <div className="flex items-center gap-2 min-w-0">
                      {board.icon ? (
                        <span className="text-xl shrink-0 leading-none">{board.icon}</span>
                      ) : (
                        <div className="w-4 h-4 rounded bg-brand-primary/20 shrink-0" />
                      )}
                      <h3 className="font-bold text-sm text-brand-text group-hover:text-brand-primary truncate transition-colors">
                        {board.name}
                      </h3>
                    </div>

                    {board.project_key && (
                      <span className="font-mono text-[10px] bg-brand-surface border border-brand-border px-1.5 py-0.5 rounded text-brand-text-muted shrink-0">
                        {board.project_key}
                      </span>
                    )}
                  </div>

                  <p className="text-xs text-brand-text-muted line-clamp-1">
                    {board.description || 'No description provided.'}
                  </p>
                </div>

                {/* Task Completion Progress Bar */}
                <div className="space-y-1.5 pt-2 border-t border-brand-border/40">
                  <div className="flex items-center justify-between text-[11px]">
                    <span className="text-brand-text-muted">Progress</span>
                    <span className="font-semibold text-brand-text">
                      {board.completed_task_count || 0} / {board.task_count || 0} tasks ({completionPct.toFixed(0)}%)
                    </span>
                  </div>

                  <div className="h-2 w-full rounded-full bg-brand-surface-container overflow-hidden">
                    <div
                      style={{ width: `${completionPct}%` }}
                      className="h-full bg-emerald-500 rounded-full transition-all duration-300"
                    />
                  </div>

                  {/* Overdue Badge & Member Count */}
                  <div className="flex items-center justify-between pt-1 text-[10px]">
                    <span className="flex items-center gap-1 text-brand-text-muted">
                      <Users className="w-3 h-3" aria-hidden="true" /> {board.member_count || 1} members
                    </span>

                    {board.overdue_count > 0 ? (
                      <span className="px-1.5 py-0.5 rounded bg-red-500/10 text-red-400 border border-red-500/20 font-semibold flex items-center gap-1">
                        <AlertTriangle className="w-3 h-3" aria-hidden="true" /> {board.overdue_count} Overdue
                      </span>
                    ) : (
                      <span className="text-emerald-400 font-medium">On track</span>
                    )}
                  </div>
                </div>
              </Link>
            );
          })}
        </div>
      )}

      {/* Pagination Controls */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between pt-4 border-t border-brand-border/60 text-xs">
          <span className="text-brand-text-muted">
            Page {currentPage} of {totalPages}
          </span>
          <div className="flex items-center gap-2">
            <button
              disabled={currentPage === 1}
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              className="p-1.5 rounded-lg border border-brand-border text-brand-text hover:bg-brand-surface-low disabled:opacity-40 disabled:cursor-not-allowed focus:ring-1 focus:ring-brand-primary"
              aria-label="Previous page"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <button
              disabled={currentPage === totalPages}
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
              className="p-1.5 rounded-lg border border-brand-border text-brand-text hover:bg-brand-surface-low disabled:opacity-40 disabled:cursor-not-allowed focus:ring-1 focus:ring-brand-primary"
              aria-label="Next page"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </Card>
  );
};
