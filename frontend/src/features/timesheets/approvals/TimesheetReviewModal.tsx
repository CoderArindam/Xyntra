import React, { useEffect, useState } from 'react';
import toast from 'react-hot-toast';
import {
  X,
  CheckCircle2,
  XCircle,
  MessageSquare,
  AlertTriangle,
  Loader2,
  Calendar,
  History,
  FileText,
} from 'lucide-react';
import {
  getTimesheetDetail,
  type Timesheet,
  type TimesheetDetail,
} from '../../../services/timesheetService';
import {
  getTimesheetPolicy,
  type TimesheetPolicy,
} from '../../../services/timesheetAdminService';
import {
  approveTimesheet,
  rejectTimesheet,
} from '../../../services/timesheetApprovalService';
import TimeEntryRow from '../member/TimeEntryRow';
import { Badge } from '../../../components/ui/Badge';
import { Button } from '../../../components/ui/Button';
import { TimesheetErrorBanner, parseTimesheetError, type TimesheetApiError } from '../shared/TimesheetErrorBanner';
import { groupEntriesByBoard, buildWeekDates } from '../shared/utils';

export interface TimesheetReviewModalProps {
  timesheetId: string;
  onClose: () => void;
  onApproved: (ts: Timesheet) => void;
  onRejected: (ts: Timesheet) => void;
}



export const TimesheetReviewModal: React.FC<TimesheetReviewModalProps> = ({
  timesheetId,
  onClose,
  onApproved,
  onRejected,
}) => {
  const [detail, setDetail] = useState<TimesheetDetail | null>(null);
  const [policy, setPolicy] = useState<TimesheetPolicy | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [apiError, setApiError] = useState<TimesheetApiError | null>(null);

  // Action inline forms state
  const [actionType, setActionType] = useState<'none' | 'approve' | 'reject'>('none');
  const [approveComment, setApproveComment] = useState('');
  const [rejectComment, setRejectComment] = useState('');
  const [rejectError, setRejectError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    let isMounted = true;
    const fetchData = async () => {
      setLoading(true);
      setError(null);
      try {
        const [detailRes, policyRes] = await Promise.all([
          getTimesheetDetail(timesheetId),
          getTimesheetPolicy().catch(() => null),
        ]);
        if (isMounted) {
          setDetail(detailRes);
          setPolicy(policyRes);
        }
      } catch (err: any) {
        if (isMounted) {
          setError(err.response?.data?.detail || 'Failed to load timesheet details');
        }
      } finally {
        if (isMounted) setLoading(false);
      }
    };

    fetchData();
    return () => {
      isMounted = false;
    };
  }, [timesheetId]);

  const handleApproveSubmit = async () => {
    setIsSubmitting(true);
    setApiError(null);
    try {
      const res = await approveTimesheet(timesheetId, {
        comment: approveComment.trim() || undefined,
      });
      toast.success(`Timesheet approved for ${detail?.submitter_name || 'member'}`);
      onApproved(res);
      onClose();
    } catch (err: any) {
      const parsed = parseTimesheetError(err);
      setApiError(parsed);
      toast.error(parsed?.detail || 'Failed to approve timesheet');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRejectSubmit = async () => {
    if (!rejectComment.trim()) {
      setRejectError('Comment is mandatory when rejecting a timesheet.');
      return;
    }
    setRejectError(null);
    setApiError(null);
    setIsSubmitting(true);
    try {
      const res = await rejectTimesheet(timesheetId, {
        comment: rejectComment.trim(),
      });
      toast.success(`Timesheet returned to draft for ${detail?.submitter_name || 'member'}`);
      onRejected(res);
      onClose();
    } catch (err: any) {
      const parsed = parseTimesheetError(err);
      setApiError(parsed);
      toast.error(parsed?.detail || 'Failed to reject timesheet');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Build 7 days and grouped rows using shared utilities
  const weekDates = detail?.week_start_date ? buildWeekDates(detail.week_start_date) : [];
  const boardGroups = detail ? groupEntriesByBoard(detail) : [];

  const getStatusBadge = (status?: string) => {
    const s = (status || '').toLowerCase();
    switch (s) {
      case 'approved':
        return <Badge variant="success">APPROVED</Badge>;
      case 'rejected':
        return <Badge variant="danger">REJECTED</Badge>;
      case 'submitted':
        return <Badge variant="warning">PENDING REVIEW</Badge>;
      default:
        return <Badge variant="secondary">{status || 'DRAFT'}</Badge>;
    }
  };

  const effectivePolicy: import('../../../services/timesheetAdminService').TimesheetPolicy = policy ?? {
    org_id: detail?.org_id ?? '',
    week_start_day: 'monday',
    standard_hours_per_day: 8.0,
    standard_hours_per_week: detail?.standard_hours_per_week ?? 40.0,
    max_hours_per_day: 12.0,
    overtime_policy: 'flag_only',
    submission_deadline_days: 2,
    allow_future_entry: false,
    allow_past_entry_days: 30,
    require_task_link: false,
    allow_member_recall: true,
    org_name: '',
    org_slug: '',
  };

  const totalHours = detail?.total_hours || 0;
  const stdHours = effectivePolicy.standard_hours_per_week;
  const deltaHours = totalHours - stdHours;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm overflow-y-auto animate-in fade-in duration-200">
      <div className="bg-brand-surface border border-brand-border rounded-2xl w-full max-w-5xl max-h-[90vh] flex flex-col shadow-2xl overflow-hidden my-auto">
        
        {/* Section 1: Header */}
        <div className="p-5 border-b border-brand-border flex items-center justify-between bg-brand-surface-low/80 shrink-0">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-brand-primary/10 rounded-xl text-brand-primary border border-brand-primary/20">
              <FileText size={22} />
            </div>
            <div>
              <div className="flex items-center gap-3">
                <h2 className="text-lg font-bold text-brand-text">
                  {detail ? `${detail.submitter_name}'s Timesheet` : 'Review Timesheet'}
                </h2>
                {detail && getStatusBadge(detail.status)}
              </div>
              <p className="text-xs text-brand-text-muted mt-0.5">
                Week of {detail?.week_start_date ? new Date(detail.week_start_date + 'T00:00:00').toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : '...'}
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-2 rounded-lg text-brand-text-muted hover:text-brand-text hover:bg-brand-surface-low transition-colors"
          >
            <X size={20} />
          </button>
        </div>

        {/* Modal Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          <TimesheetErrorBanner error={apiError} onDismiss={() => setApiError(null)} />
          {loading ? (
            <div className="flex flex-col items-center justify-center py-20 gap-3 text-brand-text-muted">
              <Loader2 size={32} className="animate-spin text-brand-primary" />
              <span className="text-sm font-medium">Loading details for review...</span>
            </div>
          ) : error || !detail ? (
            <div className="p-6 bg-red-500/10 border border-red-500/20 rounded-xl text-center text-red-400 space-y-2">
              <AlertTriangle size={28} className="mx-auto" />
              <p className="font-semibold">{error || 'Timesheet not found'}</p>
            </div>
          ) : (
            <>
              {/* Section 2: Summary Row */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div className="bg-brand-surface-low/50 border border-brand-border/60 rounded-xl p-4 flex flex-col">
                  <span className="text-[11px] font-semibold text-brand-text-muted uppercase tracking-wider">
                    Total Submitted Hours
                  </span>
                  <span className="text-xl font-bold font-mono text-brand-text mt-1">
                    {totalHours.toFixed(1)} hrs
                  </span>
                </div>

                <div className="bg-brand-surface-low/50 border border-brand-border/60 rounded-xl p-4 flex flex-col">
                  <span className="text-[11px] font-semibold text-brand-text-muted uppercase tracking-wider">
                    Standard Weekly Target
                  </span>
                  <span className="text-xl font-bold font-mono text-brand-text mt-1">
                    {stdHours.toFixed(1)} hrs
                  </span>
                </div>

                <div className="bg-brand-surface-low/50 border border-brand-border/60 rounded-xl p-4 flex flex-col">
                  <span className="text-[11px] font-semibold text-brand-text-muted uppercase tracking-wider">
                    Target Variance (Delta)
                  </span>
                  <span
                    className={`text-xl font-bold font-mono mt-1 ${
                      deltaHours >= 0 ? 'text-emerald-400' : 'text-red-400'
                    }`}
                  >
                    {deltaHours >= 0 ? `+${deltaHours.toFixed(1)}` : deltaHours.toFixed(1)} hrs
                  </span>
                </div>
              </div>

              {/* Section 5: Member Note (if present) */}
              {detail.member_note && (
                <div className="p-4 bg-brand-primary/5 border-l-4 border-l-brand-primary border border-brand-border rounded-r-xl space-y-1">
                  <div className="text-xs font-semibold text-brand-primary uppercase tracking-wider flex items-center gap-1.5">
                    <MessageSquare size={14} /> Member Submission Note
                  </div>
                  <p className="text-xs text-brand-text italic">
                    "{detail.member_note}"
                  </p>
                </div>
              )}

              {/* Section 3: Read-only Weekly Grid */}
              <div className="space-y-2">
                <h3 className="text-xs font-bold text-brand-text-muted uppercase tracking-wider flex items-center gap-2">
                  <Calendar size={14} className="text-brand-primary" /> Weekly Work Breakdown
                </h3>

                <div className="w-full overflow-x-auto bg-brand-surface border border-brand-border rounded-xl">
                  <table className="w-full text-left border-collapse">
                    <thead>
                      <tr className="border-b border-brand-border bg-brand-surface-low/60 text-xs font-semibold text-brand-text-muted">
                        <th className="py-3 px-4 min-w-[220px]">Work Item / Board</th>
                        {weekDates.map((date) => {
                          const dateKey = date.toISOString().split('T')[0];
                          const dayName = date.toLocaleDateString('en-US', { weekday: 'short' });
                          const dayNum = date.getDate();
                          return (
                            <th key={dateKey} className="py-3 px-2 text-center min-w-[60px]">
                              <div className="text-[10px] uppercase tracking-wider">{dayName}</div>
                              <div className="text-xs font-semibold text-brand-text mt-0.5">{dayNum}</div>
                            </th>
                          );
                        })}
                        <th className="py-3 px-4 text-right min-w-[70px]">Total</th>
                      </tr>
                    </thead>
                    <tbody>
                      {boardGroups.length === 0 ? (
                        <tr>
                          <td colSpan={9} className="py-8 text-center text-xs text-brand-text-muted">
                            No time entries recorded for this week.
                          </td>
                        </tr>
                      ) : (
                        boardGroups.map((group) => (
                          <React.Fragment key={group.boardId}>
                            {group.rows.map((row, idx) => (
                              <TimeEntryRow
                                key={`${group.boardId}_${row.taskId || 'none'}_${row.entryType}_${idx}`}
                                boardName={group.boardName}
                                taskTitle={row.taskTitle}
                                entryType={row.entryType}
                                entries={row.entries}
                                weekDates={weekDates}
                                policy={effectivePolicy}
                                readOnly={true}
                                onHoursChange={() => {}}
                                onDescriptionChange={() => {}}
                                onDelete={() => {}}
                              />
                            ))}
                          </React.Fragment>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Section 4: Audit Log Timeline */}
              <div className="space-y-3 pt-2">
                <h3 className="text-xs font-bold text-brand-text-muted uppercase tracking-wider flex items-center gap-2">
                  <History size={14} className="text-brand-primary" /> Approval Audit Log
                </h3>

                {detail.audit_log.length === 0 ? (
                  <div className="p-4 bg-brand-surface-low/30 border border-brand-border/40 rounded-xl text-xs text-brand-text-muted">
                    No status transitions logged yet.
                  </div>
                ) : (
                  <div className="relative pl-6 space-y-4 before:absolute before:top-2 before:bottom-2 before:left-2.5 before:w-0.5 before:bg-brand-border">
                    {detail.audit_log.map((audit) => (
                      <div key={audit.id} className="relative flex flex-col gap-1">
                        <div className="absolute -left-6 top-1.5 w-3 h-3 rounded-full bg-brand-primary border-2 border-brand-surface" />
                        <div className="bg-brand-surface-low/40 border border-brand-border/50 p-3 rounded-xl text-xs space-y-1.5">
                          <div className="flex items-center justify-between">
                            <span className="font-semibold text-brand-text">
                              {audit.actor_name} <span className="text-brand-text-muted font-normal">({audit.actor_email})</span>
                            </span>
                            <span className="text-[10px] text-brand-text-muted">
                              {new Date(audit.created_at).toLocaleString()}
                            </span>
                          </div>

                          <div className="flex items-center gap-2 text-brand-text-muted">
                            <span>Status changed:</span>
                            <Badge variant="outline" size="sm">{audit.from_status || 'DRAFT'}</Badge>
                            <span>→</span>
                            <Badge variant="primary" size="sm">{audit.to_status}</Badge>
                          </div>

                          {audit.comment && (
                            <p className="mt-1.5 text-xs italic text-brand-text bg-brand-surface/60 p-2.5 rounded-lg border border-brand-border/40">
                              "{audit.comment}"
                            </p>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </>
          )}
        </div>

        {/* Section 6: Action Section at bottom */}
        {detail && (
          <div className="p-4 border-t border-brand-border bg-brand-surface-low/90 shrink-0">
            {actionType === 'none' && (
              <div className="flex items-center justify-between">
                <Button variant="outline" size="sm" onClick={onClose}>
                  Close
                </Button>

                {detail.status.toUpperCase() === 'SUBMITTED' ? (
                  <div className="flex items-center gap-3">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setActionType('reject')}
                      className="border-red-500/40 text-red-400 hover:bg-red-500/10 hover:border-red-500/60 gap-1.5"
                    >
                      <XCircle size={16} /> Reject
                    </Button>

                    <Button
                      size="sm"
                      onClick={() => setActionType('approve')}
                      className="bg-emerald-600 hover:bg-emerald-500 text-white gap-1.5"
                    >
                      <CheckCircle2 size={16} /> Approve
                    </Button>
                  </div>
                ) : (
                  <span className="text-xs text-brand-text-muted italic">
                    This timesheet is currently in <strong className="uppercase">{detail.status}</strong> state.
                  </span>
                )}
              </div>
            )}

            {/* Approve inline form */}
            {actionType === 'approve' && (
              <div className="space-y-3 animate-in fade-in">
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-bold text-emerald-400 flex items-center gap-1.5">
                    <CheckCircle2 size={16} /> Confirm Timesheet Approval
                  </h4>
                  <button
                    onClick={() => setActionType('none')}
                    className="text-xs text-brand-text-muted hover:text-brand-text"
                  >
                    Cancel
                  </button>
                </div>

                <input
                  type="text"
                  value={approveComment}
                  onChange={(e) => setApproveComment(e.target.value)}
                  placeholder="Optional approval comment for submitter..."
                  className="w-full text-xs p-2.5 rounded-lg bg-brand-surface border border-brand-border text-brand-text outline-none focus:border-emerald-500"
                />

                <div className="flex justify-end gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setActionType('none')}
                    disabled={isSubmitting}
                  >
                    Cancel
                  </Button>
                  <Button
                    size="sm"
                    onClick={handleApproveSubmit}
                    disabled={isSubmitting}
                    className="bg-emerald-600 hover:bg-emerald-500 text-white gap-1.5"
                  >
                    {isSubmitting ? (
                      <>
                        <Loader2 size={14} className="animate-spin" /> Approving...
                      </>
                    ) : (
                      <>Confirm Approval</>
                    )}
                  </Button>
                </div>
              </div>
            )}

            {/* Reject inline form */}
            {actionType === 'reject' && (
              <div className="space-y-3 animate-in fade-in">
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-bold text-red-400 flex items-center gap-1.5">
                    <XCircle size={16} /> Reject Timesheet (Reverts to Draft)
                  </h4>
                  <button
                    onClick={() => {
                      setActionType('none');
                      setRejectError(null);
                    }}
                    className="text-xs text-brand-text-muted hover:text-brand-text"
                  >
                    Cancel
                  </button>
                </div>

                <textarea
                  rows={2}
                  value={rejectComment}
                  onChange={(e) => {
                    setRejectComment(e.target.value);
                    if (e.target.value.trim()) setRejectError(null);
                  }}
                  placeholder="Required: Provide reason for rejecting this timesheet..."
                  className={`w-full text-xs p-2.5 rounded-lg bg-brand-surface border text-brand-text outline-none resize-none ${
                    rejectError ? 'border-red-500 focus:border-red-500' : 'border-brand-border focus:border-red-500'
                  }`}
                />
                {rejectError && (
                  <p className="text-[11px] text-red-400 font-medium">{rejectError}</p>
                )}

                <div className="flex justify-end gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      setActionType('none');
                      setRejectError(null);
                    }}
                    disabled={isSubmitting}
                  >
                    Cancel
                  </Button>
                  <Button
                    size="sm"
                    onClick={handleRejectSubmit}
                    disabled={isSubmitting}
                    className="bg-red-600 hover:bg-red-500 text-white gap-1.5"
                  >
                    {isSubmitting ? (
                      <>
                        <Loader2 size={14} className="animate-spin" /> Rejecting...
                      </>
                    ) : (
                      <>Confirm Rejection</>
                    )}
                  </Button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default TimesheetReviewModal;
