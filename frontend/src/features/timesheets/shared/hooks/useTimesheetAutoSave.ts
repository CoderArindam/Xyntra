import { useState, useRef, useCallback } from 'react';
import {
  type TimesheetDetail,
  type UpsertEntryRequest,
  upsertEntry,
  getTimesheetDetail,
} from '../../../../services/timesheetService';
import type { TimesheetPolicy } from '../../../../services/timesheetAdminService';

interface UseTimesheetAutoSaveOptions {
  timesheetId: string;
  readOnly: boolean;
  detail: TimesheetDetail | null;
  policy: TimesheetPolicy | null;
  onDetailUpdate: (detail: TimesheetDetail) => void;
  onStatusChange?: (status: string) => void;
}

export function useTimesheetAutoSave({
  timesheetId,
  readOnly,
  detail,
  policy,
  onDetailUpdate,
  onStatusChange,
}: UseTimesheetAutoSaveOptions) {
  const [pendingQueue, setPendingQueue] = useState<Map<string, UpsertEntryRequest>>(new Map());
  const [isSaving, setIsSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const debounceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

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
        const updated = await getTimesheetDetail(timesheetId);
        onDetailUpdate(updated);
        if (onStatusChange) onStatusChange(updated.status);

        setSaveSuccess(true);
        setTimeout(() => setSaveSuccess(false), 2000);
      } catch (err: any) {
        console.error('Auto-save error:', err);
      } finally {
        setIsSaving(false);
      }
    },
    [timesheetId, onStatusChange, readOnly, onDetailUpdate]
  );

  const enqueueChange = useCallback(
    (req: UpsertEntryRequest) => {
      if (readOnly) return;

      const key = `${req.board_id || 'nobd'}_${req.task_id || 'notk'}_${req.entry_date}_${req.entry_type}`;
      const nextQueue = new Map(pendingQueue);
      nextQueue.set(key, req);
      setPendingQueue(nextQueue);

      // Optimistic update
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
        onDetailUpdate({ ...detail, entries: updatedEntries, total_hours: newTotal });
      }

      if (debounceTimerRef.current) clearTimeout(debounceTimerRef.current);
      debounceTimerRef.current = setTimeout(() => {
        flushPendingQueue(nextQueue);
        setPendingQueue(new Map());
      }, 800);
    },
    [readOnly, pendingQueue, detail, policy, timesheetId, flushPendingQueue, onDetailUpdate]
  );

  return { isSaving, saveSuccess, enqueueChange };
}
