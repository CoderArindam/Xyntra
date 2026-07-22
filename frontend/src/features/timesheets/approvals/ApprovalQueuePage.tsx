import React, { useEffect, useState, useCallback } from 'react';
import { Navigate } from 'react-router-dom';
import {
  Filter,
  Eye,
  ShieldCheck,
  ChevronLeft,
  ChevronRight,
  Inbox,
  AlertCircle,
  RefreshCw,
  Building,
} from 'lucide-react';
import { useAuthStore } from '../../../store/authStore';
import { isManagerOrAdmin } from '../../../lib/rbac';
import {
  getApprovalQueue,
  getApprovalQueueSummary,
  type ApprovalQueueItem,
  type ApprovalQueueSummary,
} from '../../../services/timesheetApprovalService';
import { getBoards, type Board } from '../../../services/boardsApi';
import { ApprovalQueueSummaryCards } from './ApprovalQueueSummaryCards';
import { TimesheetReviewModal } from './TimesheetReviewModal';
import { UserAvatar } from '../../../components/common/UserAvatar';
import { Badge } from '../../../components/ui/Badge';
import { Button } from '../../../components/ui/Button';
import { Skeleton } from '../../../components/ui/Skeleton';

const ITEMS_PER_PAGE = 25;

export const ApprovalQueuePage: React.FC = () => {
  const { user } = useAuthStore();

  // RBAC Gate: Redirect regular members to /timesheets
  if (user && !isManagerOrAdmin(user)) {
    return <Navigate to="/timesheets" replace />;
  }

  // Summary state
  const [summary, setSummary] = useState<ApprovalQueueSummary | null>(null);
  const [summaryLoading, setSummaryLoading] = useState<boolean>(true);
  const [summaryError, setSummaryError] = useState<string | null>(null);

  // Queue data state
  const [queueItems, setQueueItems] = useState<ApprovalQueueItem[]>([]);
  const [queueLoading, setQueueLoading] = useState<boolean>(true);
  const [queueError, setQueueError] = useState<string | null>(null);

  // Filters state
  const [statusFilter, setStatusFilter] = useState<string>('submitted'); // default 'submitted' (Pending)
  const [selectedBoardId, setSelectedBoardId] = useState<string>('');
  const [boards, setBoards] = useState<Board[]>([]);

  // Pagination state
  const [currentPage, setCurrentPage] = useState<number>(1);

  // Modal review state
  const [selectedTimesheetId, setSelectedTimesheetId] = useState<string | null>(null);

  // Load available boards for filter
  useEffect(() => {
    getBoards()
      .then((data) => setBoards(data))
      .catch((err) => console.error('Failed to load boards for filter:', err));
  }, []);

  // Fetch summary
  const fetchSummary = useCallback(async () => {
    setSummaryLoading(true);
    setSummaryError(null);
    try {
      const data = await getApprovalQueueSummary();
      setSummary(data);
    } catch (err: any) {
      setSummaryError(err.response?.data?.detail || 'Failed to fetch summary metrics');
    } finally {
      setSummaryLoading(false);
    }
  }, []);

  // Fetch queue items based on current filters
  const fetchQueue = useCallback(async () => {
    setQueueLoading(true);
    setQueueError(null);
    try {
      const params: { status?: string; board_id?: string } = {};
      if (statusFilter) params.status = statusFilter;
      if (selectedBoardId) params.board_id = selectedBoardId;

      const items = await getApprovalQueue(params);
      const sorted = [...items].sort((a, b) => {
        const timeA = a.submitted_at ? new Date(a.submitted_at).getTime() : 0;
        const timeB = b.submitted_at ? new Date(b.submitted_at).getTime() : 0;
        if (timeB !== timeA) return timeB - timeA;
        const dateA = a.week_start_date ? new Date(a.week_start_date).getTime() : 0;
        const dateB = b.week_start_date ? new Date(b.week_start_date).getTime() : 0;
        return dateB - dateA;
      });
      setQueueItems(sorted);
      setCurrentPage(1); // Reset page on filter change
    } catch (err: any) {
      setQueueError(err.response?.data?.detail || 'Failed to load approval queue');
    } finally {
      setQueueLoading(false);
    }
  }, [statusFilter, selectedBoardId]);

  // Initial load
  useEffect(() => {
    fetchSummary();
    fetchQueue();
  }, [fetchSummary, fetchQueue]);

  // 60s Polling interval for real-time updates
  useEffect(() => {
    const interval = setInterval(() => {
      fetchSummary();
      fetchQueue();
    }, 60000);

    return () => clearInterval(interval);
  }, [fetchSummary, fetchQueue]);

  // Handle status tab change
  const handleStatusChange = (newStatus: string) => {
    setStatusFilter(newStatus);
  };

  // Callback when a timesheet is approved/rejected in modal
  const handleItemUpdated = () => {
    fetchSummary();
    fetchQueue();
  };

  // Pagination calculations
  const totalItems = queueItems.length;
  const totalPages = Math.ceil(totalItems / ITEMS_PER_PAGE) || 1;
  const startIndex = (currentPage - 1) * ITEMS_PER_PAGE;
  const paginatedItems = queueItems.slice(startIndex, startIndex + ITEMS_PER_PAGE);

  const getStatusBadge = (status: string) => {
    const s = status.toLowerCase();
    switch (s) {
      case 'approved':
        return <Badge variant="success">APPROVED</Badge>;
      case 'rejected':
        return <Badge variant="danger">REJECTED</Badge>;
      case 'submitted':
        return <Badge variant="warning">PENDING REVIEW</Badge>;
      default:
        return <Badge variant="secondary">{status.toUpperCase()}</Badge>;
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header section */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-brand-text">Timesheet Approvals</h1>
            <Badge variant="primary" className="gap-1 font-semibold">
              <ShieldCheck size={14} /> Managers Only
            </Badge>
          </div>
          <p className="text-xs text-brand-text-muted mt-1">
            Review, approve, or reject team timesheet submissions for your assigned boards.
          </p>
        </div>

        <Button
          variant="outline"
          size="sm"
          onClick={() => {
            fetchSummary();
            fetchQueue();
          }}
          className="gap-2 shrink-0 text-xs"
        >
          <RefreshCw size={14} className={queueLoading ? 'animate-spin' : ''} /> Refresh Queue
        </Button>
      </div>

      {/* Summary Cards Row */}
      <ApprovalQueueSummaryCards
        summary={summary}
        loading={summaryLoading}
        error={summaryError}
        onRetry={fetchSummary}
      />

      {/* Filter Bar & Content */}
      <div className="bg-brand-surface border border-brand-border rounded-2xl shadow-lg p-5 space-y-4">
        {/* Filter Controls Row */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4 border-b border-brand-border pb-4">
          {/* Status Tabs */}
          <div className="flex items-center p-1 bg-brand-surface-low rounded-xl border border-brand-border/60 text-xs">
            {[
              { id: 'submitted', label: 'Pending' },
              { id: 'approved', label: 'Approved' },
              { id: 'rejected', label: 'Rejected' },
              { id: 'all', label: 'All' },
            ].map((tab) => {
              const isActive = statusFilter === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => handleStatusChange(tab.id)}
                  className={`px-4 py-2 rounded-lg font-medium transition-all ${
                    isActive
                      ? 'bg-brand-primary text-white shadow-sm font-semibold'
                      : 'text-brand-text-muted hover:text-brand-text hover:bg-brand-surface/50'
                  }`}
                >
                  {tab.label}
                </button>
              );
            })}
          </div>

          {/* Board Filter Dropdown */}
          <div className="flex items-center gap-2">
            <Filter size={14} className="text-brand-text-muted shrink-0" />
            <select
              value={selectedBoardId}
              onChange={(e) => setSelectedBoardId(e.target.value)}
              className="bg-brand-surface-low border border-brand-border rounded-xl text-xs text-brand-text px-3 py-2 outline-none focus:border-brand-primary transition-colors cursor-pointer"
            >
              <option value="">All Boards</option>
              {boards.map((b) => (
                <option key={b.id} value={b.id}>
                  {b.name}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Timesheet List / Table */}
        {queueLoading ? (
          <div className="space-y-3 py-4">
            {Array.from({ length: 5 }).map((_, idx) => (
              <Skeleton key={idx} variant="rectangular" className="h-16 rounded-xl" />
            ))}
          </div>
        ) : queueError ? (
          <div className="p-6 text-center bg-red-500/10 border border-red-500/20 rounded-xl text-red-400 space-y-3">
            <AlertCircle size={28} className="mx-auto" />
            <p className="text-sm font-semibold">{queueError}</p>
            <Button variant="outline" size="sm" onClick={fetchQueue}>
              Retry Loading Queue
            </Button>
          </div>
        ) : paginatedItems.length === 0 ? (
          /* Empty state per filter */
          <div className="py-16 text-center space-y-3">
            <div className="w-16 h-16 rounded-2xl bg-brand-surface-low border border-brand-border flex items-center justify-center mx-auto text-brand-text-muted">
              <Inbox size={32} />
            </div>
            <h3 className="text-sm font-bold text-brand-text">
              {statusFilter === 'submitted'
                ? 'No timesheets pending review'
                : 'No timesheets match current filters'}
            </h3>
            <p className="text-xs text-brand-text-muted max-w-sm mx-auto">
              {statusFilter === 'submitted'
                ? "Great job! You've reviewed all submitted timesheets in your approval queue."
                : 'Try adjusting your status or board filters to view submitted member timesheets.'}
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-brand-border text-xs font-semibold text-brand-text-muted uppercase tracking-wider">
                  <th className="py-3 px-4">Member</th>
                  <th className="py-3 px-4">Week</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Total Hours</th>
                  <th className="py-3 px-4">Submitted</th>
                  <th className="py-3 px-4">Boards Involved</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-brand-border/40 text-xs">
                {paginatedItems.map((item) => {
                  const isOverdue = item.is_overdue || (item.status === 'submitted' && item.days_since_submitted > 2);
                  const weekFormatted = new Date(item.week_start_date + 'T00:00:00').toLocaleDateString(
                    'en-US',
                    { month: 'short', day: 'numeric', year: 'numeric' }
                  );

                  return (
                    <tr
                      key={item.id}
                      onClick={() => setSelectedTimesheetId(item.id)}
                      className={`hover:bg-brand-surface-low/60 transition-colors cursor-pointer group ${
                        isOverdue ? 'border-l-4 border-l-amber-500 bg-amber-500/5' : ''
                      }`}
                    >
                      {/* Member */}
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-3">
                          <UserAvatar
                            user={{
                              first_name: item.submitter_name,
                              email: item.submitter_email,
                            }}
                            size="sm"
                          />
                          <div>
                            <div className="font-semibold text-brand-text group-hover:text-brand-primary transition-colors">
                              {item.submitter_name}
                            </div>
                            <div className="text-[10px] text-brand-text-muted">
                              {item.submitter_email}
                            </div>
                          </div>
                        </div>
                      </td>

                      {/* Week */}
                      <td className="py-3 px-4 font-medium text-brand-text whitespace-nowrap">
                        Week of {weekFormatted}
                      </td>

                      {/* Status */}
                      <td className="py-3 px-4 whitespace-nowrap">{getStatusBadge(item.status)}</td>

                      {/* Total Hours */}
                      <td className="py-3 px-4 font-mono font-bold text-brand-text whitespace-nowrap">
                        {item.total_hours.toFixed(1)} hrs
                      </td>

                      {/* Days Since Submitted */}
                      <td className="py-3 px-4 text-brand-text-muted whitespace-nowrap">
                        {item.days_since_submitted === 0
                          ? 'Today'
                          : item.days_since_submitted === 1
                          ? '1 day ago'
                          : `${item.days_since_submitted} days ago`}
                        {isOverdue && item.status === 'submitted' && (
                          <span className="ml-2 text-[10px] font-bold text-amber-400 bg-amber-500/10 px-1.5 py-0.5 rounded">
                            OVERDUE
                          </span>
                        )}
                      </td>

                      {/* Boards Involved */}
                      <td className="py-3 px-4">
                        <div className="flex flex-wrap gap-1">
                          {item.boards_involved.length === 0 ? (
                            <span className="text-brand-text-muted italic">General / None</span>
                          ) : (
                            item.boards_involved.map((bName, bIdx) => (
                              <Badge key={bIdx} variant="outline" size="sm" className="gap-1 text-[10px]">
                                <Building size={10} /> {bName}
                              </Badge>
                            ))
                          )}
                        </div>
                      </td>

                      {/* Action Button */}
                      <td className="py-3 px-4 text-right whitespace-nowrap">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedTimesheetId(item.id);
                          }}
                          className="gap-1.5 text-xs group-hover:border-brand-primary group-hover:text-brand-primary"
                        >
                          <Eye size={14} /> Review
                        </Button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination Footer */}
        {!queueLoading && totalItems > 0 && (
          <div className="flex items-center justify-between border-t border-brand-border pt-4 text-xs text-brand-text-muted">
            <div>
              Showing <span className="font-semibold text-brand-text">{startIndex + 1}</span> to{' '}
              <span className="font-semibold text-brand-text">
                {Math.min(startIndex + ITEMS_PER_PAGE, totalItems)}
              </span>{' '}
              of <span className="font-semibold text-brand-text">{totalItems}</span> timesheets
            </div>

            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setCurrentPage((p) => Math.max(p - 1, 1))}
                disabled={currentPage === 1}
                className="gap-1 px-2.5"
              >
                <ChevronLeft size={14} /> Previous
              </Button>

              <span className="px-2 font-medium">
                Page {currentPage} of {totalPages}
              </span>

              <Button
                variant="outline"
                size="sm"
                onClick={() => setCurrentPage((p) => Math.min(p + 1, totalPages))}
                disabled={currentPage === totalPages}
                className="gap-1 px-2.5"
              >
                Next <ChevronRight size={14} />
              </Button>
            </div>
          </div>
        )}
      </div>

      {/* Review Modal */}
      {selectedTimesheetId && (
        <TimesheetReviewModal
          timesheetId={selectedTimesheetId}
          onClose={() => setSelectedTimesheetId(null)}
          onApproved={handleItemUpdated}
          onRejected={handleItemUpdated}
        />
      )}
    </div>
  );
};

export default ApprovalQueuePage;
