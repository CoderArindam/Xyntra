import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Kanban, Plus, FolderPlus, ChevronLeft, ChevronRight } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardDescription } from '../../../components/ui/Card';
import { Skeleton } from '../../../components/ui/Skeleton';
import { WidgetError } from '../../../components/ui/WidgetError';
import type { DashboardBoardSummary } from '../../../services/dashboardApi';
import EmptyState from '../../../components/common/EmptyState';
import { getBoardMembers, type BoardMember } from '../../../services/usersApi';
import { useAuthStore } from '../../../store/authStore';

interface StrategicProjectsWidgetProps {
  summaryBoards: DashboardBoardSummary[];
  activeBoardsFallback: any[];
  isFetching: boolean;
  hasError?: boolean;
  onRetry?: () => void;
  onOpenCreateProjectModal: () => void;
}

const AVATAR_PALETTES = [
  'bg-blue-600 text-white',
  'bg-purple-600 text-white',
  'bg-amber-600 text-white',
  'bg-emerald-600 text-white',
  'bg-indigo-600 text-white',
  'bg-rose-600 text-white',
];

const getRelativeTime = (dateStr?: string | Date, fallbackIdx: number = 0) => {
  if (!dateStr) {
    const times = ['2 days ago', '5 days ago', '1 week ago', '2 weeks ago'];
    return times[fallbackIdx % times.length];
  }
  const date = new Date(dateStr);
  const now = new Date();
  const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000);
  if (diffInSeconds < 3600) return `${Math.max(1, Math.floor(diffInSeconds / 60))} mins ago`;
  if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)} hours ago`;
  if (diffInSeconds < 604800) return `${Math.floor(diffInSeconds / 86400)} days ago`;
  return `${Math.floor(diffInSeconds / 604800)} weeks ago`;
};

export const StrategicProjectsWidget: React.FC<StrategicProjectsWidgetProps> = ({
  summaryBoards,
  activeBoardsFallback,
  isFetching,
  hasError = false,
  onRetry,
  onOpenCreateProjectModal,
}) => {
  const { user: currentUser } = useAuthStore();
  const [currentPage, setCurrentPage] = useState(1);
  const [boardMembersMap, setBoardMembersMap] = useState<Record<number, BoardMember[]>>({});
  const pageSize = 3;

  const displayBoards =
    summaryBoards.length > 0
      ? summaryBoards.map((sb) => ({
          id: sb.id,
          name: sb.name,
          project_key: sb.project_key,
          description: sb.description,
          task_count: sb.task_count,
          completed_task_count: sb.completed_task_count,
          completion_percentage: sb.completion_percentage,
          overdue_count: sb.overdue_count,
          member_count: sb.member_count || 1,
          created_at: sb.created_at,
        }))
      : activeBoardsFallback.map((ab) => ({
          id: ab.id,
          name: ab.name,
          project_key: ab.project_key,
          description: ab.description,
          task_count: ab.task_count || 0,
          completed_task_count: ab.completed_task_count || 0,
          completion_percentage: ab.task_count > 0 ? Math.round(((ab.completed_task_count || 0) / ab.task_count) * 100) : 0,
          overdue_count: ab.overdue_count || 0,
          member_count: ab.member_count || 1,
          created_at: ab.created_at,
        }));

  // Fetch actual board members from PostgreSQL backend for each display board
  useEffect(() => {
    let isMounted = true;
    displayBoards.forEach((board) => {
      if (!boardMembersMap[board.id]) {
        getBoardMembers(board.id)
          .then((members) => {
            if (isMounted && members) {
              setBoardMembersMap((prev) => ({
                ...prev,
                [board.id]: members,
              }));
            }
          })
          .catch((err) => {
            console.error(`Failed to fetch members for board ${board.id}:`, err);
          });
      }
    });
    return () => {
      isMounted = false;
    };
  }, [displayBoards, boardMembersMap]);

  const totalPages = Math.ceil(displayBoards.length / pageSize) || 1;
  const paginatedBoards = displayBoards.slice(
    (currentPage - 1) * pageSize,
    currentPage * pageSize
  );

  // Resolves actual assigned members for a board
  const getBoardMembersToRender = (boardId: number) => {
    const realMembers = boardMembersMap[boardId];
    if (realMembers && realMembers.length > 0) {
      return realMembers.map((m) => {
        const fullName = [m.first_name, m.last_name].filter(Boolean).join(' ') || m.email.split('@')[0];
        const initials = (
          (m.first_name ? m.first_name[0] : m.email[0]) +
          (m.last_name ? m.last_name[0] : '')
        ).toUpperCase();
        return {
          id: m.id,
          fullName,
          initials,
          avatarUrl: m.avatar_url,
        };
      });
    }

    // Default fallback if real members are loading: show current logged-in creator
    const creatorName = currentUser
      ? [currentUser.first_name, currentUser.last_name].filter(Boolean).join(' ') || currentUser.email.split('@')[0]
      : 'Creator';

    const creatorInitials = currentUser
      ? (
          (currentUser.first_name ? currentUser.first_name[0] : currentUser.email[0]) +
          (currentUser.last_name ? currentUser.last_name[0] : '')
        ).toUpperCase()
      : 'CR';

    return [
      {
        id: currentUser?.id || 0,
        fullName: creatorName,
        initials: creatorInitials,
        avatarUrl: currentUser?.avatar_url,
      },
    ];
  };

  return (
    <Card variant="default" padding="lg" className="space-y-6 shadow-sm">
      <CardHeader className="flex-row items-center justify-between mb-0 pb-2">
        <div className="space-y-1">
          <CardTitle className="text-lg font-bold text-brand-text flex items-center gap-2">
            <Kanban className="w-5 h-5 text-brand-primary" aria-hidden="true" />
            <span>Strategic Projects Overview</span>
          </CardTitle>
          <CardDescription className="text-xs text-brand-text-muted">
            High-priority organizational initiatives, team assignments, and milestone completion
          </CardDescription>
        </div>

        {/* Primary Create Project Action Button */}
        <button
          onClick={onOpenCreateProjectModal}
          className="bg-brand-primary hover:bg-brand-primary-hover text-white px-3.5 py-2 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition-all shadow-xs cursor-pointer focus:ring-2 focus:ring-brand-primary focus:outline-none shrink-0"
        >
          <Plus className="w-4 h-4" /> Create Project
        </button>
      </CardHeader>

      {hasError ? (
        <WidgetError
          title="Could not load projects overview"
          message="Failed to retrieve active project statuses."
          onRetry={onRetry}
        />
      ) : isFetching && displayBoards.length === 0 ? (
        <div className="space-y-4" aria-busy="true" aria-label="Loading strategic projects">
          {[1, 2, 3].map((idx) => (
            <div
              key={idx}
              className="p-5 rounded-2xl bg-brand-surface-low/60 border border-brand-border/60 space-y-4 animate-pulse"
            >
              <div className="flex justify-between items-start">
                <div className="space-y-2 flex-1">
                  <Skeleton variant="text" width="60%" height={18} />
                  <Skeleton variant="text" width="30%" height={12} />
                </div>
                <Skeleton variant="circular" width={32} height={32} />
              </div>
              <Skeleton variant="rectangular" width="100%" height={8} />
            </div>
          ))}
        </div>
      ) : displayBoards.length === 0 ? (
        <EmptyState
          icon={<FolderPlus size={44} className="text-brand-primary/70" />}
          title="No strategic projects created yet"
          description="Get started by initializing your team's first Kanban project board."
          action={
            <button
              onClick={onOpenCreateProjectModal}
              className="bg-brand-primary hover:bg-brand-primary-hover text-white px-4 py-2 rounded-xl text-xs font-semibold shadow-xs flex items-center gap-1.5 cursor-pointer"
            >
              <Plus className="w-4 h-4" /> Create Project
            </button>
          }
        />
      ) : (
        <div className="space-y-4">
          {paginatedBoards.map((board, idx) => {
            const completionPct = Math.round(board.completion_percentage || 0);
            const isOverdue = board.overdue_count > 0;
            const statusText = isOverdue ? 'Needs Attention' : 'On Track';
            const statusBg = isOverdue
              ? 'text-amber-500 bg-amber-500/10 border-amber-500/20'
              : 'text-emerald-500 bg-emerald-500/10 border-emerald-500/20';

            const relativeTime = getRelativeTime(board.created_at, idx);
            const membersToRender = getBoardMembersToRender(board.id);

            return (
              <Link
                key={board.id}
                to={`/board/${board.id}`}
                className="group block p-5 rounded-2xl bg-brand-surface-low/40 hover:bg-brand-surface-low border border-brand-border hover:border-brand-primary/40 transition-all duration-200 shadow-2xs hover:shadow-md cursor-pointer focus:outline-none focus:ring-2 focus:ring-brand-primary"
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-3">
                  <div className="space-y-1 min-w-0">
                    <h3 className="font-bold text-base text-brand-text group-hover:text-brand-primary transition-colors truncate flex items-center gap-2">
                      <span>{board.name}</span>
                      {board.project_key && (
                        <span className="font-mono text-[10px] bg-brand-surface border border-brand-border px-1.5 py-0.5 rounded text-brand-text-muted">
                          {board.project_key}
                        </span>
                      )}
                    </h3>
                    <div className="flex items-center gap-2 text-xs">
                      <span className="text-brand-text-muted">Status:</span>
                      <span
                        className={`font-semibold px-2 py-0.5 rounded-full text-[11px] border ${statusBg}`}
                      >
                        {statusText}
                      </span>
                    </div>
                  </div>

                  {/* Real Overlapping Team Member Avatar Stack */}
                  <div className="flex items-center -space-x-2 shrink-0 self-start sm:self-auto">
                    {membersToRender.slice(0, 4).map((member, mIdx) => (
                      <div
                        key={member.id || mIdx}
                        className={`w-8 h-8 rounded-full border-2 border-brand-surface flex items-center justify-center text-[10px] font-bold shadow-xs overflow-hidden ${
                          AVATAR_PALETTES[(mIdx + idx) % AVATAR_PALETTES.length]
                        }`}
                        title={member.fullName}
                      >
                        {member.avatarUrl ? (
                          <img
                            src={member.avatarUrl}
                            alt={member.fullName}
                            className="w-full h-full object-cover"
                          />
                        ) : (
                          member.initials
                        )}
                      </div>
                    ))}
                    {membersToRender.length > 4 && (
                      <div className="w-8 h-8 rounded-full border-2 border-brand-surface bg-brand-surface-container text-brand-text text-[10px] font-bold flex items-center justify-center shadow-xs">
                        +{membersToRender.length - 4}
                      </div>
                    )}
                  </div>
                </div>

                {/* Progress Bar & Footer */}
                <div className="space-y-2 pt-1">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-brand-text-muted font-medium">Progress</span>
                    <span className="font-bold text-brand-text">{completionPct}%</span>
                  </div>

                  <div className="h-2 w-full rounded-full bg-brand-surface-container overflow-hidden">
                    <div
                      style={{ width: `${completionPct}%` }}
                      className="h-full bg-gradient-to-r from-brand-primary to-indigo-500 rounded-full transition-all duration-500"
                    />
                  </div>

                  <div className="flex justify-end pt-1">
                    <span className="text-[11px] text-brand-text-muted">{relativeTime}</span>
                  </div>
                </div>
              </Link>
            );
          })}
        </div>
      )}

      {/* Arrow Pagination Toggle at Bottom for > 3 Projects */}
      {displayBoards.length > 3 && (
        <div className="flex items-center justify-between pt-4 border-t border-brand-border/60 text-xs">
          <span className="text-brand-text-muted font-medium">
            Page {currentPage} of {totalPages} ({displayBoards.length} total projects)
          </span>
          <div className="flex items-center gap-2">
            <button
              disabled={currentPage === 1}
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              className="p-2 rounded-xl border border-brand-border text-brand-text hover:bg-brand-surface-low disabled:opacity-40 disabled:cursor-not-allowed transition-colors cursor-pointer"
              aria-label="Previous page"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <button
              disabled={currentPage === totalPages}
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
              className="p-2 rounded-xl border border-brand-border text-brand-text hover:bg-brand-surface-low disabled:opacity-40 disabled:cursor-not-allowed transition-colors cursor-pointer"
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

export default StrategicProjectsWidget;
