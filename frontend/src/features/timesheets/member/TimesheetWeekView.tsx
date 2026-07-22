import React, { useEffect, useState, useCallback } from 'react';
import toast from 'react-hot-toast';
import { AlertTriangle, FolderPlus, Loader2, Clock } from 'lucide-react';
import {
  type TimesheetDetail,
  type TimesheetEntry,
  getTimesheetDetail,
  deleteEntry,
  submitTimesheet,
  recallTimesheet,
} from '../../../services/timesheetService';
import { getTimesheetPolicy, type TimesheetPolicy, getEligibleApprovers, type EligibleApprover } from '../../../services/timesheetAdminService';
import { getBoards, type Board } from '../../../services/boardsApi';
import { TimesheetSummaryBar } from './TimesheetSummaryBar';
import { Button } from '../../../components/ui/Button';
import { TimesheetErrorBanner, parseTimesheetError, type TimesheetApiError } from '../shared/TimesheetErrorBanner';
import { groupEntriesByBoard, buildWeekDates, toDateStr } from '../shared/utils';
import { useBoardTasks } from '../shared/hooks/useBoardTasks';
import { useTimesheetAutoSave } from '../shared/hooks/useTimesheetAutoSave';
import { TimesheetGridHeader } from './components/TimesheetGridHeader';
import { TimesheetBoardSection } from './components/TimesheetBoardSection';
import { AddBoardModal } from './modals/AddBoardModal';
import { AddEntryModal } from './modals/AddEntryModal';
import { LogEffortModal } from './modals/LogEffortModal';
import { SubmitTimesheetModal } from './modals/SubmitTimesheetModal';
import { RecallTimesheetModal } from './modals/RecallTimesheetModal';
import { EditEntryModal } from './modals/EditEntryModal';

export interface TimesheetWeekViewProps {
  timesheetId: string;
  onStatusChange?: (newStatus: string) => void;
  onRegisterLogEffortTrigger?: (fn: () => void) => void;
}

export const TimesheetWeekView: React.FC<TimesheetWeekViewProps> = ({
  timesheetId,
  onStatusChange,
  onRegisterLogEffortTrigger,
}) => {
  const [detail, setDetail] = useState<TimesheetDetail | null>(null);
  const [policy, setPolicy] = useState<TimesheetPolicy | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [apiError, setApiError] = useState<TimesheetApiError | null>(null);

  // Modal state
  const [showSubmitModal, setShowSubmitModal] = useState(false);
  const [showRecallModal, setShowRecallModal] = useState(false);
  const [showAddBoardModal, setShowAddBoardModal] = useState(false);
  const [showAddEntryModal, setShowAddEntryModal] = useState<{ boardId: string; boardName: string } | null>(null);
  const [showLogEffortModal, setShowLogEffortModal] = useState(false);
  const [editingEntry, setEditingEntry] = useState<TimesheetEntry | null>(null);

  // Form state
  const [memberNote, setMemberNote] = useState('');
  const [recallReason, setRecallReason] = useState('');
  const [isActionLoading, setIsActionLoading] = useState(false);

  // Approver selection
  const [eligibleApprovers, setEligibleApprovers] = useState<EligibleApprover[]>([]);
  const [selectedApproverId, setSelectedApproverId] = useState<string>('auto');
  const [loadingApprovers, setLoadingApprovers] = useState(false);

  // Accessible boards
  const [accessibleBoards, setAccessibleBoards] = useState<Board[]>([]);

  // Add entry modal state
  const [selectedEntryType, setSelectedEntryType] = useState<string>('task');
  const [selectedTaskId, setSelectedTaskId] = useState<string>('');

  // Log effort modal state
  const [logEffortBoardId, setLogEffortBoardId] = useState<string>('');
  const [logEffortEntryType, setLogEffortEntryType] = useState<string>('task');
  const [logEffortTaskId, setLogEffortTaskId] = useState<string>('');
  const [logEffortDate, setLogEffortDate] = useState<string>('');
  const [logEffortHours, setLogEffortHours] = useState<string>('8.0');
  const [logEffortDescription, setLogEffortDescription] = useState<string>('');

  const { boardTasksMap, loadingTasks, loadBoardTasks } = useBoardTasks();

  const statusUpper = (detail?.status || '').toUpperCase();
  const readOnly = Boolean(detail && statusUpper !== 'DRAFT' && statusUpper !== 'REJECTED');

  const { isSaving, saveSuccess, enqueueChange } = useTimesheetAutoSave({
    timesheetId,
    readOnly,
    detail,
    policy,
    onDetailUpdate: setDetail,
    onStatusChange,
    onError: (msg) => setApiError(parseTimesheetError(msg)),
  });

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

  useEffect(() => { loadData(); }, [loadData]);

  useEffect(() => {
    if (onRegisterLogEffortTrigger) {
      onRegisterLogEffortTrigger(() => handleOpenLogEffortModal());
    }
  }, [onRegisterLogEffortTrigger]);

  useEffect(() => {
    if (showSubmitModal) {
      setLoadingApprovers(true);
      getEligibleApprovers()
        .then((approvers) => {
          setEligibleApprovers(approvers);
          if (approvers.length > 0) setSelectedApproverId(approvers[0].user_id);
        })
        .catch(() => [])
        .finally(() => setLoadingApprovers(false));
    }
  }, [showSubmitModal]);

  const weekDates = detail?.week_start_date ? buildWeekDates(detail.week_start_date) : [];
  const todayStr = toDateStr(new Date());

  const boardGroups = detail ? groupEntriesByBoard(detail) : [];

  const dayTotals = weekDates.map((date) => {
    const dateStr = toDateStr(date);
    return detail?.entries.reduce((sum, e) => {
      if (e.entry_date.split('T')[0] === dateStr) return sum + (Number(e.hours) || 0);
      return sum;
    }, 0) || 0;
  });

  const missingTaskLinksCount =
    policy?.require_task_link && detail
      ? detail.entries.filter((e) => e.entry_type === 'task' && !e.task_id).length
      : 0;

  const handleHoursChange = (
    boardId: string,
    taskId: string | undefined,
    entryType: string,
    date: Date,
    hours: number
  ) => {
    const dateStr = toDateStr(date);
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

  const handleDescriptionChange = (
    boardId: string,
    taskId: string | undefined,
    entryType: string,
    date: Date,
    description: string
  ) => {
    const dateStr = toDateStr(date);
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

  const handleDeleteEntry = async (entryId: string) => {
    if (!detail || entryId.startsWith('temp_')) return;
    try {
      await deleteEntry(timesheetId, entryId);
      const updated = await getTimesheetDetail(timesheetId);
      setDetail(updated);
    } catch (err: any) {
      console.error(err);
    }
  };

  const handleDeleteRow = async (entries: TimesheetEntry[]) => {
    if (!detail) return;
    for (const entry of entries) {
      if (entry.id && !entry.id.startsWith('temp_')) {
        try {
          await deleteEntry(timesheetId, entry.id);
        } catch (e) {
          console.error(e);
        }
      }
    }
    try {
      const updated = await getTimesheetDetail(timesheetId);
      setDetail(updated);
    } catch (e) {
      console.error(e);
    }
  };

  const handleSaveEditEntry = (data: {
    entryId?: string;
    boardId?: string;
    taskId?: string;
    entryDate: string;
    hours: number;
    entryType: string;
    description?: string;
  }) => {
    enqueueChange({
      board_id: data.boardId,
      task_id: data.taskId,
      entry_date: data.entryDate,
      hours: data.hours,
      entry_type: data.entryType,
      description: data.description,
    });
    setEditingEntry(null);
  };

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
      toast.success('Timesheet submitted successfully for approval!');
    } catch (err: any) {
      const parsed = parseTimesheetError(err);
      setApiError(parsed);
      setShowSubmitModal(false);
      toast.error(parsed?.detail || 'Failed to submit timesheet');
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
      toast.success('Timesheet recalled successfully.');
    } catch (err: any) {
      const parsed = parseTimesheetError(err);
      setApiError(parsed);
      setShowRecallModal(false);
      toast.error(parsed?.detail || 'Failed to recall timesheet');
    } finally {
      setIsActionLoading(false);
    }
  };

  const handleOpenAddEntry = async (boardId: string, boardName: string) => {
    setShowAddEntryModal({ boardId, boardName });
    setSelectedEntryType('task');
    setSelectedTaskId('');
    await loadBoardTasks(boardId);
  };

  const handleCreateNewRow = () => {
    if (!showAddEntryModal || !detail) return;
    const { boardId } = showAddEntryModal;
    const bId = boardId === 'general' ? undefined : boardId;
    const tId = selectedEntryType === 'task' && selectedTaskId ? selectedTaskId : undefined;
    enqueueChange({
      board_id: bId,
      task_id: tId,
      entry_date: detail.week_start_date,
      hours: 8.0,
      entry_type: selectedEntryType,
      description: '',
    });
    setShowAddEntryModal(null);
  };

  const handleOpenLogEffortModal = async (initialBoardId?: string) => {
    const todayISO = toDateStr(new Date());
    const isTodayInWeek = weekDates.some((d) => toDateStr(d) === todayISO);
    const defaultDate = isTodayInWeek ? todayISO : (detail?.week_start_date || todayISO);
    const bId = initialBoardId || (accessibleBoards.length > 0 ? String(accessibleBoards[0].id) : 'general');
    setLogEffortBoardId(bId);
    setLogEffortEntryType('task');
    setLogEffortTaskId('');
    setLogEffortHours('8.0');
    setLogEffortDescription('');
    setLogEffortDate(defaultDate);
    setShowLogEffortModal(true);
    await loadBoardTasks(bId);
  };

  const handleBoardSelectInLogEffort = async (newBoardId: string) => {
    setLogEffortBoardId(newBoardId);
    setLogEffortTaskId('');
    await loadBoardTasks(newBoardId);
  };

  const handleSaveLogEffort = () => {
    if (!detail) return;
    const numHours = parseFloat(logEffortHours) || 0;
    if (numHours <= 0) return;
    enqueueChange({
      board_id: logEffortBoardId === 'general' ? undefined : logEffortBoardId,
      task_id: logEffortEntryType === 'task' && logEffortTaskId ? logEffortTaskId : undefined,
      entry_date: logEffortDate || detail.week_start_date,
      hours: numHours,
      entry_type: logEffortEntryType,
      description: logEffortDescription,
    });
    setShowLogEffortModal(false);
  };

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

      <TimesheetGridHeader
        entryCount={detail.entry_count}
        readOnly={readOnly}
        isSaving={isSaving}
        saveSuccess={saveSuccess}
        onLogEffort={() => handleOpenLogEffortModal()}
      />

      {/* Grid Table Container */}
      <div className="w-full overflow-x-auto bg-brand-surface border border-brand-border rounded-xl shadow-lg">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-brand-border bg-brand-surface-low/60 text-[11px] font-bold text-brand-text-muted uppercase tracking-wider">
              <th className="py-3.5 px-4 text-left min-w-[240px]">PROJECT / TASK</th>
              {weekDates.map((date, idx) => {
                const dateKey = toDateStr(date);
                const isToday = dateKey === todayStr;
                const dayName = date.toLocaleDateString('en-US', { weekday: 'short' }).toUpperCase();
                const dayNum = date.getDate();
                const hrs = dayTotals[idx] || 0;
                return (
                  <th
                    key={dateKey}
                    className={`py-2.5 px-2 text-center min-w-[64px] ${isToday ? 'bg-brand-primary/10 text-brand-primary font-bold' : ''}`}
                  >
                    <div className="text-[11px] font-bold tracking-wider">{dayName} {dayNum}</div>
                    <div className={`text-[10px] font-mono mt-0.5 ${
                      hrs > 0 ? (isToday ? 'text-brand-primary font-bold' : 'text-brand-text font-bold') : 'text-brand-text-muted/60'
                    }`}>
                      {hrs > 0 ? `${hrs.toFixed(1)}h` : '—'}
                    </div>
                  </th>
                );
              })}
              <th className="py-3.5 px-4 text-right min-w-[80px]">TOTAL</th>
            </tr>
          </thead>

          <tbody>
            {boardGroups.map((group) => (
              <TimesheetBoardSection
                key={group.boardId}
                group={group}
                weekDates={weekDates}
                policy={policy}
                readOnly={readOnly}
                onHoursChange={handleHoursChange}
                onDescriptionChange={handleDescriptionChange}
                onDelete={handleDeleteEntry}
                onDeleteRow={handleDeleteRow}
                onEditEntry={(entry) => setEditingEntry(entry)}
                onAddEntry={handleOpenAddEntry}
              />
            ))}

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

          {boardGroups.length > 0 && (
            <tfoot className="border-t-2 border-brand-border/80 bg-brand-surface-low/80 font-semibold text-xs">
              <tr>
                <td className="py-3 px-4 text-left font-bold text-brand-text flex items-center gap-1.5">
                  <Clock size={14} className="text-brand-primary" />
                  <span>DAILY TOTAL</span>
                </td>
                {dayTotals.map((hrs, idx) => {
                  const isOverMax = hrs > (policy.max_hours_per_day || 24);
                  const isOverStd = hrs > (policy.standard_hours_per_day || 8);
                  return (
                    <td key={idx} className="py-3 px-2 text-center font-mono font-bold">
                      <span
                        className={`inline-block px-1.5 py-0.5 rounded text-[11px] ${
                          hrs === 0
                            ? 'text-brand-text-muted/40'
                            : isOverMax
                              ? 'bg-red-500/20 text-red-400 border border-red-500/40'
                              : isOverStd
                                ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                                : 'bg-brand-primary/10 text-brand-primary border border-brand-primary/20'
                        }`}
                      >
                        {hrs > 0 ? `${hrs.toFixed(1)}h` : '0h'}
                      </span>
                    </td>
                  );
                })}
                <td className="py-3 px-4 text-right font-mono font-bold text-brand-primary text-sm">
                  {detail.total_hours.toFixed(1)} hrs
                </td>
              </tr>
            </tfoot>
          )}
        </table>

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

      <TimesheetSummaryBar
        timesheet={detail}
        policy={policy}
        onSubmit={() => setShowSubmitModal(true)}
        onRecall={() => setShowRecallModal(true)}
        isSubmitting={isActionLoading}
        dayTotals={dayTotals}
        weekDates={weekDates}
      />

      {/* Modals */}
      <AddBoardModal
        isOpen={showAddBoardModal}
        onClose={() => setShowAddBoardModal(false)}
        accessibleBoards={accessibleBoards}
        onSelectBoard={handleOpenAddEntry}
      />

      {showAddEntryModal && (
        <AddEntryModal
          boardName={showAddEntryModal.boardName}
          onClose={() => setShowAddEntryModal(null)}
          selectedEntryType={selectedEntryType}
          onEntryTypeChange={setSelectedEntryType}
          selectedTaskId={selectedTaskId}
          onTaskChange={setSelectedTaskId}
          boardTasks={boardTasksMap[showAddEntryModal.boardId] || []}
          loadingTasks={loadingTasks}
          onConfirm={handleCreateNewRow}
        />
      )}

      <LogEffortModal
        isOpen={showLogEffortModal}
        onClose={() => setShowLogEffortModal(false)}
        weekDates={weekDates}
        accessibleBoards={accessibleBoards}
        boardTasksMap={boardTasksMap}
        loadingTasks={loadingTasks}
        boardId={logEffortBoardId}
        onBoardChange={handleBoardSelectInLogEffort}
        entryType={logEffortEntryType}
        onEntryTypeChange={setLogEffortEntryType}
        taskId={logEffortTaskId}
        onTaskChange={setLogEffortTaskId}
        date={logEffortDate}
        onDateChange={setLogEffortDate}
        hours={logEffortHours}
        onHoursChange={setLogEffortHours}
        description={logEffortDescription}
        onDescriptionChange={setLogEffortDescription}
        onSave={handleSaveLogEffort}
      />

      {editingEntry && (
        <EditEntryModal
          isOpen={Boolean(editingEntry)}
          onClose={() => setEditingEntry(null)}
          entry={editingEntry}
          accessibleBoards={accessibleBoards}
          boardTasksMap={boardTasksMap}
          loadingTasks={loadingTasks}
          onLoadTasks={loadBoardTasks}
          weekDates={weekDates}
          onSave={handleSaveEditEntry}
          onDelete={handleDeleteEntry}
        />
      )}

      <SubmitTimesheetModal
        isOpen={showSubmitModal}
        onClose={() => setShowSubmitModal(false)}
        eligibleApprovers={eligibleApprovers}
        loadingApprovers={loadingApprovers}
        selectedApproverId={selectedApproverId}
        onApproverChange={setSelectedApproverId}
        memberNote={memberNote}
        onNoteChange={setMemberNote}
        isActionLoading={isActionLoading}
        onConfirm={handleConfirmSubmit}
      />

      <RecallTimesheetModal
        isOpen={showRecallModal}
        onClose={() => setShowRecallModal(false)}
        recallReason={recallReason}
        onReasonChange={setRecallReason}
        isActionLoading={isActionLoading}
        onConfirm={handleConfirmRecall}
      />
    </div>
  );
};

export default TimesheetWeekView;
