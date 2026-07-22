import React, { useEffect, useState, useRef, useCallback } from 'react';
import {
  Plus,
  Save,
  Check,
  AlertTriangle,
  FolderPlus,
  Loader2,
  Calendar,
  Building,
  ShieldCheck,
} from 'lucide-react';
import {
  type TimesheetDetail,
  type TimesheetEntry,
  type UpsertEntryRequest,
  getTimesheetDetail,
  upsertEntry,
  deleteEntry,
  submitTimesheet,
  recallTimesheet,
} from '../../../services/timesheetService';
import {
  type TimesheetPolicy,
  getTimesheetPolicy,
  getEligibleApprovers,
  type EligibleApprover,
} from '../../../services/timesheetAdminService';
import { getBoards, type Board } from '../../../services/boardsApi';
import { getBoardTasks, type Task } from '../../../services/tasksApi';
import { TimeEntryRow } from './TimeEntryRow';
import { TimesheetSummaryBar } from './TimesheetSummaryBar';
import { Button } from '../../../components/ui/Button';
import { Modal } from '../../../components/ui/Modal';
import { Input } from '../../../components/ui/Input';

import { TimesheetErrorBanner, parseTimesheetError, type TimesheetApiError } from '../shared/TimesheetErrorBanner';

export interface TimesheetWeekViewProps {
  timesheetId: string;
  onStatusChange?: (newStatus: string) => void;
}

interface BoardRowGroup {
  boardId: string;
  boardName: string;
  rows: {
    taskId?: string;
    taskTitle?: string;
    entryType: string;
    entries: TimesheetEntry[];
  }[];
}

export const TimesheetWeekView: React.FC<TimesheetWeekViewProps> = ({
  timesheetId,
  onStatusChange,
}) => {
  const [detail, setDetail] = useState<TimesheetDetail | null>(null);
  const [policy, setPolicy] = useState<TimesheetPolicy | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [apiError, setApiError] = useState<TimesheetApiError | null>(null);

  // Auto-save state
  const [pendingQueue, setPendingQueue] = useState<Map<string, UpsertEntryRequest>>(new Map());
  const [isSaving, setIsSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const debounceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Modals state
  const [showSubmitModal, setShowSubmitModal] = useState(false);
  const [showRecallModal, setShowRecallModal] = useState(false);
  const [showAddBoardModal, setShowAddBoardModal] = useState(false);
  const [showAddEntryModal, setShowAddEntryModal] = useState<{
    boardId: string;
    boardName: string;
  } | null>(null);

  // Form inputs
  const [memberNote, setMemberNote] = useState('');
  const [recallReason, setRecallReason] = useState('');
  const [isActionLoading, setIsActionLoading] = useState(false);

  // Approver selection state
  const [eligibleApprovers, setEligibleApprovers] = useState<EligibleApprover[]>([]);
  const [selectedApproverId, setSelectedApproverId] = useState<string>('auto');
  const [loadingApprovers, setLoadingApprovers] = useState(false);

  useEffect(() => {
    if (showSubmitModal) {
      setLoadingApprovers(true);
      getEligibleApprovers()
        .then((approvers) => {
          setEligibleApprovers(approvers);
          if (approvers.length > 0) {
            setSelectedApproverId(approvers[0].user_id);
          }
        })
        .catch(() => [])
        .finally(() => {
          setLoadingApprovers(false);
        });
    }
  }, [showSubmitModal]);

  // Accessible boards & tasks cache
  const [accessibleBoards, setAccessibleBoards] = useState<Board[]>([]);
  const [boardTasksMap, setBoardTasksMap] = useState<Record<string, Task[]>>({});
  const [loadingTasks, setLoadingTasks] = useState(false);

  // Entry picker state inside modal
  const [selectedEntryType, setSelectedEntryType] = useState<string>('task');
  const [selectedTaskId, setSelectedTaskId] = useState<string>('');

  // Dedicated Log Effort Modal state
  const [showLogEffortModal, setShowLogEffortModal] = useState(false);
  const [logEffortBoardId, setLogEffortBoardId] = useState<string>('');
  const [logEffortEntryType, setLogEffortEntryType] = useState<string>('task');
  const [logEffortTaskId, setLogEffortTaskId] = useState<string>('');
  const [logEffortDate, setLogEffortDate] = useState<string>('');
  const [logEffortHours, setLogEffortHours] = useState<string>('8.0');
  const [logEffortDescription, setLogEffortDescription] = useState<string>('');


  // 1. Fetch Detail & Policy on mount or timesheetId change
  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [detailRes, policyRes, boardsRes] = await Promise.all([
        getTimesheetDetail(timesheetId),
        getTimesheetPolicy().catch(() => null),
        getBoards().catch(() => []),
      ]);
      setDetail(detailRes);
      setPolicy(policyRes);
      setAccessibleBoards(boardsRes);
    } catch (err: any) {
      console.error(err);
      setError(err.response?.data?.detail || 'Failed to load timesheet details');
    } finally {
      setLoading(false);
    }
  }, [timesheetId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const statusUpper = (detail?.status || '').toUpperCase();
  const readOnly = Boolean(detail && statusUpper !== 'DRAFT' && statusUpper !== 'REJECTED');

  // Flush pending changes to API
  const flushPendingQueue = useCallback(
    async (queueToFlush: Map<string, UpsertEntryRequest>) => {
      if (readOnly || queueToFlush.size === 0 || !timesheetId) return;

      setIsSaving(true);
      setSaveSuccess(false);

      try {
        const requests = Array.from(queueToFlush.values());
        for (const req of requests) {
          await upsertEntry(timesheetId, req);
        }
        // Refresh detail to ensure canonical sync
        const updated = await getTimesheetDetail(timesheetId);
        setDetail(updated);
        if (onStatusChange) onStatusChange(updated.status);

        setSaveSuccess(true);
        setTimeout(() => setSaveSuccess(false), 2000);
      } catch (err: any) {
        console.error('Auto-save error:', err);
      } finally {
        setIsSaving(false);
      }
    },
    [timesheetId, onStatusChange, readOnly]
  );

  // Handle debounced auto-save when pendingQueue changes
  const enqueueChange = (req: UpsertEntryRequest) => {
    if (readOnly) return;
    const key = `${req.board_id || 'nobd'}_${req.task_id || 'notk'}_${req.entry_date}_${req.entry_type}`;
    const nextQueue = new Map(pendingQueue);
    nextQueue.set(key, req);
    setPendingQueue(nextQueue);

    // Optimistically update local entries state
    if (detail) {
      const updatedEntries = [...detail.entries];
      const idx = updatedEntries.findIndex(
        (e) =>
          (e.board_id || null) === (req.board_id || null) &&
          (e.task_id || null) === (req.task_id || null) &&
          e.entry_date.split('T')[0] === req.entry_date &&
          e.entry_type === req.entry_type
      );

      if (idx >= 0) {
        if (req.hours === 0) {
          updatedEntries.splice(idx, 1);
        } else {
          updatedEntries[idx] = {
            ...updatedEntries[idx],
            hours: req.hours,
            description: req.description !== undefined ? req.description : updatedEntries[idx].description,
          };
        }
      } else if (req.hours > 0) {
        updatedEntries.push({
          id: `temp_${Date.now()}`,
          timesheet_id: timesheetId,
          board_id: req.board_id || null,
          task_id: req.task_id || null,
          entry_date: req.entry_date,
          hours: req.hours,
          entry_type: req.entry_type,
          description: req.description,
          is_overtime: req.hours > (policy?.standard_hours_per_day || 8),
        });
      }

      const newTotal = updatedEntries.reduce((sum, e) => sum + (Number(e.hours) || 0), 0);
      setDetail({
        ...detail,
        entries: updatedEntries,
        total_hours: newTotal,
      });
    }

    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }
    debounceTimerRef.current = setTimeout(() => {
      flushPendingQueue(nextQueue);
      setPendingQueue(new Map());
    }, 800);
  };

  // Generate 7 days of the week Date objects
  const weekDates: Date[] = [];
  if (detail?.week_start_date) {
    const start = new Date(detail.week_start_date + 'T00:00:00');
    for (let i = 0; i < 7; i++) {
      const d = new Date(start);
      d.setDate(start.getDate() + i);
      weekDates.push(d);
    }
  }

  // Calculate today & date flags
  const todayStr = new Date().toISOString().split('T')[0];

  // Group entries by board and work item
  const boardGroupsMap = new Map<string, BoardRowGroup>();

  if (detail) {
    detail.entries.forEach((entry) => {
      const bId = entry.board_id || 'general';
      const bName = entry.board_name || (bId === 'general' ? 'General & Time-off' : 'Unknown Board');

      if (!boardGroupsMap.has(bId)) {
        boardGroupsMap.set(bId, {
          boardId: bId,
          boardName: bName,
          rows: [],
        });
      }

      const group = boardGroupsMap.get(bId)!;
      const rowKey = `${entry.task_id || 'none'}_${entry.entry_type}`;
      let row = group.rows.find((r) => `${r.taskId || 'none'}_${r.entryType}` === rowKey);

      if (!row) {
        row = {
          taskId: entry.task_id || undefined,
          taskTitle: entry.task_title || undefined,
          entryType: entry.entry_type,
          entries: [],
        };
        group.rows.push(row);
      }
      row.entries.push(entry);
    });
  }

  const boardGroups = Array.from(boardGroupsMap.values());

  // Hours change handler
  const handleHoursChange = (
    boardId: string | undefined,
    taskId: string | undefined,
    entryType: string,
    date: Date,
    hours: number
  ) => {
    const yyyy = date.getFullYear();
    const mm = String(date.getMonth() + 1).padStart(2, '0');
    const dd = String(date.getDate()).padStart(2, '0');
    const dateStr = `${yyyy}-${mm}-${dd}`;

    // Find existing description
    const existing = detail?.entries.find(
      (e) =>
        (e.board_id || undefined) === boardId &&
        (e.task_id || undefined) === taskId &&
        e.entry_date.split('T')[0] === dateStr &&
        e.entry_type === entryType
    );

    enqueueChange({
      board_id: boardId === 'general' ? undefined : boardId,
      task_id: taskId,
      entry_date: dateStr,
      hours,
      entry_type: entryType,
      description: existing?.description || undefined,
    });
  };

  // Description change handler
  const handleDescriptionChange = (
    boardId: string | undefined,
    taskId: string | undefined,
    entryType: string,
    date: Date,
    description: string
  ) => {
    const yyyy = date.getFullYear();
    const mm = String(date.getMonth() + 1).padStart(2, '0');
    const dd = String(date.getDate()).padStart(2, '0');
    const dateStr = `${yyyy}-${mm}-${dd}`;

    const existing = detail?.entries.find(
      (e) =>
        (e.board_id || undefined) === boardId &&
        (e.task_id || undefined) === taskId &&
        e.entry_date.split('T')[0] === dateStr &&
        e.entry_type === entryType
    );

    enqueueChange({
      board_id: boardId === 'general' ? undefined : boardId,
      task_id: taskId,
      entry_date: dateStr,
      hours: existing ? Number(existing.hours) : 0,
      entry_type: entryType,
      description,
    });
  };

  // Delete entry handler
  const handleDeleteEntry = async (entryId: string) => {
    if (!detail || entryId.startsWith('temp_')) return;
    try {
      await deleteEntry(timesheetId, entryId);
      const updated = await getTimesheetDetail(timesheetId);
      setDetail(updated);
    } catch (err) {
      console.error('Delete entry failed:', err);
    }
  };

  // Handlers for Submitting & Recalling
  const handleConfirmSubmit = async () => {
    setIsActionLoading(true);
    setApiError(null);
    try {
      const res = await submitTimesheet(timesheetId, {
        member_note: memberNote.trim() || undefined,
        approver_id: selectedApproverId === 'auto' ? undefined : selectedApproverId,
      });
      setDetail((prev) => (prev ? { ...prev, status: res.status } : null));
      if (onStatusChange) onStatusChange(res.status);
      setShowSubmitModal(false);
      setMemberNote('');
      setSelectedApproverId('auto');
    } catch (err: any) {
      setApiError(parseTimesheetError(err));
      setShowSubmitModal(false);
    } finally {
      setIsActionLoading(false);
    }
  };

  const handleConfirmRecall = async () => {
    if (!recallReason.trim()) return;
    setIsActionLoading(true);
    setApiError(null);
    try {
      const res = await recallTimesheet(timesheetId, { reason: recallReason });
      setDetail((prev) => (prev ? { ...prev, status: res.status } : null));
      if (onStatusChange) onStatusChange(res.status);
      setShowRecallModal(false);
      setRecallReason('');
    } catch (err: any) {
      setApiError(parseTimesheetError(err));
      setShowRecallModal(false);
    } finally {
      setIsActionLoading(false);
    }
  };

  // Open add entry modal for a specific board
  const handleOpenAddEntry = async (boardId: string, boardName: string) => {
    setShowAddEntryModal({ boardId, boardName });
    setSelectedEntryType('task');
    setSelectedTaskId('');

    if (boardId !== 'general' && !boardTasksMap[boardId]) {
      setLoadingTasks(true);
      try {
        const boardData = await getBoardTasks(boardId);
        setBoardTasksMap((prev) => ({ ...prev, [boardId]: boardData.tasks || [] }));
      } catch (err) {
        console.error('Failed to load board tasks:', err);
      } finally {
        setLoadingTasks(false);
      }
    }
  };

  const handleCreateNewRow = () => {
    if (!showAddEntryModal || !detail) return;
    const { boardId } = showAddEntryModal;

    const bId = boardId === 'general' ? undefined : boardId;
    const tId = selectedEntryType === 'task' && selectedTaskId ? selectedTaskId : undefined;

    // Add row with initial 8.0 hours
    const firstDateStr = detail.week_start_date;
    enqueueChange({
      board_id: bId,
      task_id: tId,
      entry_date: firstDateStr,
      hours: 8.0,
      entry_type: selectedEntryType,
      description: '',
    });

    setShowAddEntryModal(null);
  };

  // Dedicated Log Effort handlers
  const handleOpenLogEffortModal = async (initialBoardId?: string) => {
    const todayISO = new Date().toISOString().split('T')[0];
    const defaultDate = detail?.week_start_date || todayISO;
    const bId = initialBoardId || (accessibleBoards.length > 0 ? String(accessibleBoards[0].id) : 'general');

    setLogEffortBoardId(bId);
    setLogEffortEntryType('task');
    setLogEffortTaskId('');
    setLogEffortHours('8.0');
    setLogEffortDescription('');
    setLogEffortDate(defaultDate);
    setShowLogEffortModal(true);

    if (bId !== 'general' && !boardTasksMap[bId]) {
      setLoadingTasks(true);
      try {
        const boardData = await getBoardTasks(bId);
        setBoardTasksMap((prev) => ({ ...prev, [bId]: boardData.tasks || [] }));
      } catch (err) {
        console.error('Failed to load board tasks:', err);
      } finally {
        setLoadingTasks(false);
      }
    }
  };

  const handleBoardSelectInLogEffortModal = async (newBoardId: string) => {
    setLogEffortBoardId(newBoardId);
    setLogEffortTaskId('');
    if (newBoardId !== 'general' && !boardTasksMap[newBoardId]) {
      setLoadingTasks(true);
      try {
        const boardData = await getBoardTasks(newBoardId);
        setBoardTasksMap((prev) => ({ ...prev, [newBoardId]: boardData.tasks || [] }));
      } catch (err) {
        console.error('Failed to load board tasks:', err);
      } finally {
        setLoadingTasks(false);
      }
    }
  };


  const handleSaveLogEffort = () => {
    if (!detail) return;
    const numHours = parseFloat(logEffortHours) || 0;
    if (numHours <= 0) return;

    const bId = logEffortBoardId === 'general' ? undefined : logEffortBoardId;
    const tId = logEffortEntryType === 'task' && logEffortTaskId ? logEffortTaskId : undefined;
    const dateStr = logEffortDate || detail.week_start_date;

    enqueueChange({
      board_id: bId,
      task_id: tId,
      entry_date: dateStr,
      hours: numHours,
      entry_type: logEffortEntryType,
      description: logEffortDescription,
    });

    setShowLogEffortModal(false);
  };


  // Calculate day totals for summary bar
  const dayTotals = weekDates.map((date) => {
    const yyyy = date.getFullYear();
    const mm = String(date.getMonth() + 1).padStart(2, '0');
    const dd = String(date.getDate()).padStart(2, '0');
    const dateStr = `${yyyy}-${mm}-${dd}`;

    return (
      detail?.entries.reduce((sum, e) => {
        if (e.entry_date.split('T')[0] === dateStr) {
          return sum + (Number(e.hours) || 0);
        }
        return sum;
      }, 0) || 0
    );
  });

  // Calculate missing task links policy warning
  const missingTaskLinksCount =
    policy?.require_task_link && detail
      ? detail.entries.filter((e) => e.entry_type === 'task' && !e.task_id).length
      : 0;



  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] gap-3 text-brand-text-muted">
        <Loader2 size={32} className="animate-spin text-brand-primary" />
        <span className="text-sm font-medium">Loading timesheet...</span>
      </div>
    );
  }

  if (error || !detail || !policy) {
    return (
      <div className="p-8 text-center text-red-400 bg-red-500/10 border border-red-500/20 rounded-xl my-6">
        <AlertTriangle size={28} className="mx-auto mb-2" />
        <p className="font-semibold">{error || 'Timesheet not found'}</p>
        <Button variant="outline" size="sm" onClick={loadData} className="mt-4">
          Retry
        </Button>
      </div>
    );
  }

  return (
    <div className="flex flex-col min-h-full pb-20 relative">
      {/* Top Banner Warnings */}
      <div className="space-y-2 mb-4">
        <TimesheetErrorBanner error={apiError} onDismiss={() => setApiError(null)} />
        {missingTaskLinksCount > 0 && (
          <div className="p-3 bg-amber-500/15 border border-amber-500/30 rounded-lg flex items-center gap-3 text-xs text-amber-300">
            <AlertTriangle size={16} className="text-amber-400 shrink-0" />
            <span>
              <strong>Policy Warning:</strong> You have {missingTaskLinksCount} entries missing task
              links. Organization policy requires all work entries to be linked to a task before
              submission.
            </span>
          </div>
        )}
      </div>

      {/* Auto-Save & Sync Status Indicator (Top Right floating / header) */}
      <div className="flex items-center justify-between mb-3 px-1">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <Calendar size={16} className="text-brand-primary" />
            <span className="text-sm font-medium text-brand-text">
              Grid View ({detail.entry_count} entries)
            </span>
          </div>
          {!readOnly && (
            <Button
              variant="primary"
              size="sm"
              onClick={() => handleOpenLogEffortModal()}
              className="flex items-center gap-1.5 shadow-md shadow-brand-primary/20 bg-brand-primary hover:bg-brand-primary-hover text-white font-semibold cursor-pointer"
            >
              <Plus size={16} /> Log Effort
            </Button>
          )}
        </div>


        <div className="flex items-center gap-2 text-xs font-medium">
          {isSaving ? (
            <span className="flex items-center gap-1.5 text-amber-400 animate-pulse">
              <Loader2 size={12} className="animate-spin" />
              Saving changes...
            </span>
          ) : saveSuccess ? (
            <span className="flex items-center gap-1 text-emerald-400">
              <Check size={14} /> Saved
            </span>
          ) : (
            <span className="text-brand-text-muted/60 flex items-center gap-1">
              <Save size={12} /> Ready
            </span>
          )}
        </div>
      </div>

      {/* Grid Table Container */}
      <div className="w-full overflow-x-auto bg-brand-surface border border-brand-border rounded-xl shadow-lg">
        <table className="w-full text-left border-collapse">
          {/* Table Header: Days of the Week */}
          <thead>
            <tr className="border-b border-brand-border bg-brand-surface-low/60 text-xs font-semibold text-brand-text-muted">
              <th className="py-3 px-4 min-w-[220px]">Work Item / Board</th>
              {weekDates.map((date) => {
                const dateKey = date.toISOString().split('T')[0];
                const isToday = dateKey === todayStr;
                const dayName = date.toLocaleDateString('en-US', { weekday: 'short' });
                const dayNum = date.getDate();

                return (
                  <th
                    key={dateKey}
                    className={`py-3 px-2 text-center min-w-[64px] ${
                      isToday ? 'bg-brand-primary/10 text-brand-primary font-bold' : ''
                    }`}
                  >
                    <div className="text-[11px] uppercase tracking-wider">{dayName}</div>
                    <div className={`text-xs mt-0.5 ${isToday ? 'text-brand-primary' : 'text-brand-text'}`}>
                      {dayNum}
                    </div>
                  </th>
                );
              })}
              <th className="py-3 px-4 text-right min-w-[80px]">Total</th>
            </tr>
          </thead>

          {/* Table Body: Board Sections & Rows */}
          <tbody>
            {boardGroups.map((group) => {
              const groupTotalHours = group.rows.reduce(
                (sum, row) =>
                  sum +
                  row.entries.reduce((rSum, e) => rSum + (Number(e.hours) || 0), 0),
                0
              );

              return (
                <React.Fragment key={group.boardId}>
                  {/* Board Section Header */}
                  <tr className="bg-brand-surface-low/80 border-y border-brand-border/60">
                    <td colSpan={9} className="py-2 px-4">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2 text-xs font-bold text-brand-text">
                          <Building size={14} className="text-brand-primary" />
                          <span>{group.boardName}</span>
                          <span className="text-brand-text-muted font-normal text-[11px]">
                            ({groupTotalHours.toFixed(1)} hrs)
                          </span>
                        </div>

                        {!readOnly && (
                          <button
                            type="button"
                            onClick={() => handleOpenAddEntry(group.boardId, group.boardName)}
                            className="flex items-center gap-1 text-[11px] font-medium text-brand-primary hover:text-brand-primary-hover transition-colors px-2 py-1 rounded hover:bg-brand-primary/10"
                          >
                            <Plus size={12} /> Add Entry
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>

                  {/* Rows for this Board */}
                  {group.rows.map((row, idx) => (
                    <TimeEntryRow
                      key={`${group.boardId}_${row.taskId || 'none'}_${row.entryType}_${idx}`}
                      boardName={group.boardName}
                      taskTitle={row.taskTitle}
                      entryType={row.entryType}
                      entries={row.entries}
                      weekDates={weekDates}
                      policy={policy}
                      readOnly={readOnly}
                      onHoursChange={(date, hrs) =>
                        handleHoursChange(group.boardId, row.taskId, row.entryType, date, hrs)
                      }
                      onDescriptionChange={(date, desc) =>
                        handleDescriptionChange(group.boardId, row.taskId, row.entryType, date, desc)
                      }
                      onDelete={handleDeleteEntry}
                    />
                  ))}
                </React.Fragment>
              );
            })}

            {/* Empty state if no rows */}
            {boardGroups.length === 0 && (
              <tr>
                <td colSpan={9} className="py-12 text-center text-brand-text-muted">
                  <p className="text-sm mb-3">No time entries recorded for this week yet.</p>
                  {!readOnly && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setShowAddBoardModal(true)}
                      className="inline-flex items-center gap-2"
                    >
                      <FolderPlus size={14} /> Select a Board to start logging
                    </Button>
                  )}
                </td>
              </tr>
            )}
          </tbody>
        </table>

        {/* Add Board Footer Button */}
        {!readOnly && boardGroups.length > 0 && (
          <div className="p-3 border-t border-brand-border bg-brand-surface-low/30">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowAddBoardModal(true)}
              className="w-full flex items-center justify-center gap-2 text-brand-text-muted hover:text-brand-text border border-dashed border-brand-border/60 hover:border-brand-primary/50"
            >
              <FolderPlus size={15} /> Add Board to Timesheet
            </Button>
          </div>
        )}
      </div>

      {/* Sticky Bottom Summary Bar */}
      <TimesheetSummaryBar
        timesheet={detail}
        policy={policy}
        onSubmit={() => setShowSubmitModal(true)}
        onRecall={() => setShowRecallModal(true)}
        isSubmitting={isActionLoading}
        dayTotals={dayTotals}
        weekDates={weekDates}
      />

      {/* MODAL 1: Add Board Selector Modal */}
      <Modal
        isOpen={showAddBoardModal}
        onClose={() => setShowAddBoardModal(false)}
        title="Add Board to Timesheet"
      >
        <div className="space-y-4">
          <p className="text-xs text-brand-text-muted">
            Select an accessible project board to log time against.
          </p>

          <div className="max-h-60 overflow-y-auto space-y-1.5 border border-brand-border rounded-lg p-2">
            {accessibleBoards.map((b) => (
              <div
                key={b.id}
                onClick={() => {
                  handleOpenAddEntry(String(b.id), b.name);
                  setShowAddBoardModal(false);
                }}
                className="flex items-center justify-between p-2.5 rounded-lg hover:bg-brand-surface-low cursor-pointer transition-colors"
              >
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full bg-brand-primary" />
                  <span className="text-sm font-medium text-brand-text">{b.name}</span>
                </div>
                <span className="text-xs text-brand-text-muted">{b.project_key}</span>
              </div>
            ))}
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button variant="ghost" size="sm" onClick={() => setShowAddBoardModal(false)}>
              Cancel
            </Button>
          </div>
        </div>
      </Modal>

      {/* MODAL 2: Inline Add Entry Modal */}
      {showAddEntryModal && (
        <Modal
          isOpen={Boolean(showAddEntryModal)}
          onClose={() => setShowAddEntryModal(null)}
          title={`Add Entry to ${showAddEntryModal.boardName}`}
        >
          <div className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-brand-text-muted mb-1">
                Entry Category / Type
              </label>
              <select
                value={selectedEntryType}
                onChange={(e) => setSelectedEntryType(e.target.value)}
                className="w-full bg-brand-surface border border-brand-border rounded-lg px-3 py-2 text-sm text-brand-text focus:outline-none focus:border-brand-primary"
              >
                <option value="task">Task Work Item</option>
                <option value="general">General Project Work</option>
                <option value="meeting">Meeting</option>
                <option value="leave">Leave / Time-off</option>
                <option value="holiday">Holiday</option>
              </select>
            </div>

            {selectedEntryType === 'task' && (
              <div>
                <label className="block text-xs font-medium text-brand-text-muted mb-1">
                  Select Task
                </label>
                {loadingTasks ? (
                  <div className="flex items-center gap-2 text-xs text-brand-text-muted py-2">
                    <Loader2 size={14} className="animate-spin" /> Loading board tasks...
                  </div>
                ) : (
                  <select
                    value={selectedTaskId}
                    onChange={(e) => setSelectedTaskId(e.target.value)}
                    className="w-full bg-brand-surface border border-brand-border rounded-lg px-3 py-2 text-sm text-brand-text focus:outline-none focus:border-brand-primary"
                  >
                    <option value="">-- General (No Task Linked) --</option>
                    {(boardTasksMap[showAddEntryModal.boardId] || []).map((t) => (
                      <option key={t.id} value={String(t.id)}>
                        {t.task_reference} - {t.title}
                      </option>
                    ))}
                  </select>
                )}
              </div>
            )}

            <div className="flex justify-end gap-2 pt-4">
              <Button variant="ghost" size="sm" onClick={() => setShowAddEntryModal(null)}>
                Cancel
              </Button>
              <Button variant="primary" size="sm" onClick={handleCreateNewRow}>
                Add Row
              </Button>
            </div>
          </div>
        </Modal>
      )}

      {/* MODAL: Log Effort Modal */}
      {showLogEffortModal && (
        <Modal
          isOpen={showLogEffortModal}
          onClose={() => setShowLogEffortModal(false)}
          title="Log Effort Under Task / Board"
        >
          <div className="space-y-4">
            {/* Board Selector */}
            <div>
              <label className="block text-xs font-semibold text-brand-text mb-1">
                Project Board * (Your Assigned Boards)
              </label>
              <select
                value={logEffortBoardId}
                onChange={(e) => handleBoardSelectInLogEffortModal(e.target.value)}
                className="w-full bg-brand-surface border border-brand-border rounded-lg px-3 py-2 text-sm text-brand-text focus:outline-none focus:border-brand-primary"
              >
                <option value="general">-- General & Time-off --</option>
                {accessibleBoards.map((b) => (
                  <option key={b.id} value={String(b.id)}>
                    {b.name} ({b.project_key})
                  </option>
                ))}
              </select>
            </div>

            {/* Category / Type */}
            <div>
              <label className="block text-xs font-semibold text-brand-text mb-1">
                Work Category / Type *
              </label>
              <select
                value={logEffortEntryType}
                onChange={(e) => setLogEffortEntryType(e.target.value)}
                className="w-full bg-brand-surface border border-brand-border rounded-lg px-3 py-2 text-sm text-brand-text focus:outline-none focus:border-brand-primary"
              >
                <option value="task">Task Work Item</option>
                <option value="general">General Project Work</option>
                <option value="meeting">Meeting</option>
                <option value="leave">Leave / Time-off</option>
                <option value="holiday">Holiday</option>
              </select>
            </div>

            {/* Task Selector */}
            {logEffortEntryType === 'task' && logEffortBoardId !== 'general' && (
              <div>
                <label className="block text-xs font-semibold text-brand-text mb-1">
                  Select Task * (Belonging to Selected Board)
                </label>
                {loadingTasks ? (
                  <div className="flex items-center gap-2 text-xs text-brand-text-muted py-2">
                    <Loader2 size={14} className="animate-spin text-brand-primary" /> Loading board tasks...
                  </div>
                ) : (
                  <select
                    value={logEffortTaskId}
                    onChange={(e) => setLogEffortTaskId(e.target.value)}
                    className="w-full bg-brand-surface border border-brand-border rounded-lg px-3 py-2 text-sm text-brand-text focus:outline-none focus:border-brand-primary"
                  >
                    <option value="">-- General Board Work (No Task Linked) --</option>
                    {(boardTasksMap[logEffortBoardId] || []).map((t) => (
                      <option key={t.id} value={String(t.id)}>
                        {t.task_reference} - {t.title}
                      </option>
                    ))}
                  </select>
                )}
              </div>
            )}

            {/* Date & Hours */}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-semibold text-brand-text mb-1">
                  Log Date *
                </label>
                <select
                  value={logEffortDate}
                  onChange={(e) => setLogEffortDate(e.target.value)}
                  className="w-full bg-brand-surface border border-brand-border rounded-lg px-3 py-2 text-sm text-brand-text focus:outline-none focus:border-brand-primary"
                >
                  {weekDates.map((d) => {
                    const dStr = d.toISOString().split('T')[0];
                    const label = d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
                    return (
                      <option key={dStr} value={dStr}>
                        {label}
                      </option>
                    );
                  })}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-brand-text mb-1">
                  Hours Spent *
                </label>
                <input
                  type="number"
                  step="0.5"
                  min="0.5"
                  max="24"
                  value={logEffortHours}
                  onChange={(e) => setLogEffortHours(e.target.value)}
                  className="w-full bg-brand-surface border border-brand-border rounded-lg px-3 py-2 text-sm text-brand-text focus:outline-none focus:border-brand-primary font-mono"
                />
              </div>
            </div>

            {/* Description */}
            <div>
              <label className="block text-xs font-semibold text-brand-text mb-1">
                Effort Description / Details (Optional)
              </label>
              <textarea
                rows={2}
                value={logEffortDescription}
                onChange={(e) => setLogEffortDescription(e.target.value)}
                placeholder="What work was accomplished during these hours?"
                className="w-full bg-brand-surface border border-brand-border rounded-lg p-2 text-xs text-brand-text focus:outline-none focus:border-brand-primary resize-none"
              />
            </div>

            <div className="flex justify-end gap-2 pt-3 border-t border-brand-border">
              <Button variant="ghost" size="sm" onClick={() => setShowLogEffortModal(false)}>
                Cancel
              </Button>
              <Button
                variant="primary"
                size="sm"
                onClick={handleSaveLogEffort}
                disabled={parseFloat(logEffortHours) <= 0}
                className="bg-brand-primary hover:bg-brand-primary-hover text-white font-semibold cursor-pointer"
              >
                Save Effort Entry
              </Button>
            </div>
          </div>
        </Modal>
      )}

      {/* MODAL 3: Submit Timesheet Modal */}
      <Modal
        isOpen={showSubmitModal}
        onClose={() => setShowSubmitModal(false)}
        title="Submit Timesheet for Review"
      >
        <div className="space-y-4">
          <p className="text-xs text-brand-text-muted">
            Once submitted, your timesheet will be sent for review and manager approval. You can recall it anytime before approval.
          </p>

          {/* Reviewer / Approver Selection Section */}
          <div className="p-3 bg-brand-surface border border-brand-border rounded-xl space-y-2.5">
            <div className="flex items-center justify-between">
              <label className="block text-xs font-semibold text-brand-text flex items-center gap-1.5">
                <ShieldCheck size={14} className="text-brand-primary" />
                Select Approver Manager
              </label>
              {loadingApprovers && (
                <span className="text-[11px] text-brand-text-muted flex items-center gap-1">
                  <Loader2 size={10} className="animate-spin" /> Loading approvers...
                </span>
              )}
            </div>

            <div>
              <select
                value={selectedApproverId}
                onChange={(e) => setSelectedApproverId(e.target.value)}
                className="w-full bg-brand-bg border border-brand-border rounded-lg p-2.5 text-xs text-brand-text focus:outline-none focus:border-brand-primary font-medium"
              >
                {eligibleApprovers.length === 0 ? (
                  <option value="">No approvers configured in organization</option>
                ) : (
                  eligibleApprovers.map((app) => (
                    <option key={app.user_id} value={app.user_id}>
                      👤 {app.display_name} ({app.role}) — {app.email}
                    </option>
                  ))
                )}
              </select>
              <p className="text-[11px] text-brand-text-muted mt-1">
                Select a manager designated by your organization's Superadmin to review your timesheet.
              </p>
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-brand-text-muted mb-1">
              Member Note (Optional)
            </label>
            <textarea
              rows={3}
              value={memberNote}
              onChange={(e) => setMemberNote(e.target.value)}
              placeholder="Add any context or comments for your reviewer..."
              className="w-full bg-brand-surface border border-brand-border rounded-lg p-2.5 text-xs text-brand-text focus:outline-none focus:border-brand-primary resize-none"
            />
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button variant="ghost" size="sm" onClick={() => setShowSubmitModal(false)}>
              Cancel
            </Button>
            <Button
              variant="primary"
              size="sm"
              onClick={handleConfirmSubmit}
              disabled={isActionLoading}
            >
              {isActionLoading ? 'Submitting...' : 'Confirm Submission'}
            </Button>
          </div>
        </div>
      </Modal>

      {/* MODAL 4: Recall Timesheet Modal */}
      <Modal
        isOpen={showRecallModal}
        onClose={() => setShowRecallModal(false)}
        title="Recall Timesheet to Draft"
      >
        <div className="space-y-4">
          <p className="text-xs text-brand-text-muted">
            Recalling will revert your timesheet status to DRAFT so you can make modifications.
          </p>

          <div>
            <Input
              label="Reason for Recall *"
              placeholder="e.g. Correcting logged hours for Tuesday..."
              value={recallReason}
              onChange={(e) => setRecallReason(e.target.value)}
            />
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button variant="ghost" size="sm" onClick={() => setShowRecallModal(false)}>
              Cancel
            </Button>
            <Button
              variant="danger"
              size="sm"
              onClick={handleConfirmRecall}
              disabled={isActionLoading || !recallReason.trim()}
            >
              {isActionLoading ? 'Recalling...' : 'Confirm Recall'}
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
};

export default TimesheetWeekView;
