import React, { useEffect, useState, useCallback, useRef } from 'react';
import { ChevronLeft, ChevronRight, AlertTriangle, Plus } from 'lucide-react';
import type { Timesheet } from '../../../services/timesheetService';
import {
  getMyTimesheets,
  createTimesheet,
} from '../../../services/timesheetService';
import { TimesheetWeekView } from './TimesheetWeekView';
import { Button } from '../../../components/ui/Button';
import { formatWeekTabLabel, formatWeekHeaderLabel } from '../shared/utils';

const getMonday = (d: Date): Date => {
  const date = new Date(d);
  const day = date.getDay();
  const diff = date.getDate() - day + (day === 0 ? -6 : 1);
  const monday = new Date(date.setDate(diff));
  monday.setHours(0, 0, 0, 0);
  return monday;
};

const formatIsoDate = (d: Date): string => {
  const yyyy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, '0');
  const dd = String(d.getDate()).padStart(2, '0');
  return `${yyyy}-${mm}-${dd}`;
};

export const MyTimesheetsPage: React.FC = () => {
  const [selectedMonday, setSelectedMonday] = useState<Date>(getMonday(new Date()));
  const [timesheets, setTimesheets] = useState<Timesheet[]>([]);
  const [activeTimesheet, setActiveTimesheet] = useState<Timesheet | null>(null);
  const [loading, setLoading] = useState(true);
  const triggerLogEffortRef = useRef<(() => void) | null>(null);

  const selectedWeekIso = formatIsoDate(selectedMonday);

  // Helper to deduplicate and sort timesheets by week_start_date DESC
  const processTimesheets = (rawList: Timesheet[]): Timesheet[] => {
    const map = new Map<string, Timesheet>();
    for (const t of rawList) {
      const weekKey = (t.week_start_date || '').slice(0, 10);
      if (!map.has(weekKey)) {
        map.set(weekKey, t);
      }
    }
    return Array.from(map.values()).sort((a, b) => (b.week_start_date || '').localeCompare(a.week_start_date || ''));
  };

  // Load user's recent timesheets
  const loadTimesheets = useCallback(async () => {
    setLoading(true);
    try {
      const list = processTimesheets(await getMyTimesheets());
      setTimesheets(list);

      let match = list.find((t) => (t.week_start_date || '').slice(0, 10) === selectedWeekIso);

      if (!match) {
        try {
          const created = await createTimesheet({ week_start_date: selectedWeekIso });
          if (created) {
            match = created;
            setTimesheets((prev) => processTimesheets([created, ...prev]));
          }
        } catch (err: any) {
          const refreshed = processTimesheets(await getMyTimesheets());
          setTimesheets(refreshed);
          match = refreshed.find((t) => (t.week_start_date || '').slice(0, 10) === selectedWeekIso) || refreshed[0];
        }
      }
      setActiveTimesheet(match || null);
    } catch (err) {
      console.error('Failed to load timesheets:', err);
    } finally {
      setLoading(false);
    }
  }, [selectedWeekIso]);

  useEffect(() => {
    loadTimesheets();
  }, [loadTimesheets]);

  const navigateWeek = (weeks: number) => {
    const next = new Date(selectedMonday);
    next.setDate(selectedMonday.getDate() + weeks * 7);
    setSelectedMonday(next);
  };

  const rejectedTimesheet = timesheets.find((t) => t.status === 'REJECTED');

  // Dynamically compute a 6-week window centered around selectedMonday so active week is always visible and selectable
  const weekTabDates = Array.from({ length: 6 }, (_, i) => {
    const d = new Date(selectedMonday);
    d.setDate(selectedMonday.getDate() + (i - 2) * 7);
    return formatIsoDate(d);
  });

  return (
    <div className="flex flex-col min-h-screen bg-brand-surface-low/30 text-brand-text p-4 md:p-8 max-w-7xl mx-auto w-full">
      {/* Global Rejected Banner */}
      {rejectedTimesheet && (
        <div className="mb-6 p-4 bg-red-500/15 border border-red-500/30 rounded-xl flex flex-wrap items-center justify-between gap-4 animate-in fade-in">
          <div className="flex items-center gap-3">
            <AlertTriangle className="text-red-400 shrink-0" size={20} />
            <div>
              <p className="text-sm font-semibold text-red-300">
                Action Required: Timesheet for week of {rejectedTimesheet.week_start_date} was rejected
              </p>
              {rejectedTimesheet.approver_comment && (
                <p className="text-xs text-red-300/80 mt-0.5">
                  Reason: &quot;{rejectedTimesheet.approver_comment}&quot;
                </p>
              )}
            </div>
          </div>
          <Button
            variant="danger"
            size="sm"
            onClick={() => setSelectedMonday(new Date(rejectedTimesheet.week_start_date + 'T00:00:00'))}
          >
            View and Resubmit
          </Button>
        </div>
      )}

      {/* Main Page Header & Action Controls */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold text-brand-text tracking-tight">My Timesheets</h1>
          <p className="text-sm text-brand-text-muted mt-1">
            Track hours against projects for approval.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {/* Week Navigator Pill */}
          <div className="flex items-center bg-brand-surface border border-brand-border rounded-xl px-1 py-1 shadow-xs">
            <button
              type="button"
              onClick={() => navigateWeek(-1)}
              className="p-1.5 text-brand-text-muted hover:text-brand-text transition-colors rounded-lg hover:bg-brand-surface-low cursor-pointer"
              title="Previous Week"
            >
              <ChevronLeft size={18} />
            </button>

            <span className="text-xs font-semibold text-brand-text px-3 py-1 min-w-[200px] text-center select-none">
              {formatWeekHeaderLabel(selectedWeekIso)}
            </span>

            <button
              type="button"
              onClick={() => navigateWeek(1)}
              className="p-1.5 text-brand-text-muted hover:text-brand-text transition-colors rounded-lg hover:bg-brand-surface-low cursor-pointer"
              title="Next Week"
            >
              <ChevronRight size={18} />
            </button>
          </div>

          {/* + Log Effort Primary Button */}
          <Button
            variant="primary"
            size="sm"
            onClick={() => {
              if (triggerLogEffortRef.current) {
                triggerLogEffortRef.current();
              }
            }}
            className="flex items-center gap-1.5 px-4 py-2 bg-brand-primary hover:bg-brand-primary-hover text-white font-semibold text-xs rounded-xl shadow-sm cursor-pointer shrink-0"
          >
            <Plus size={16} /> Log Effort
          </Button>
        </div>
      </div>

      {/* Top Recent Weeks Tabs Bar */}
      <div className="flex items-center gap-3 border-b border-brand-border/60 mb-6 px-1 overflow-x-auto">
        <span className="text-xs font-bold text-brand-text-muted uppercase tracking-wider py-2.5 shrink-0 pr-2 border-r border-brand-border/40">
          Recent Weeks
        </span>

        {weekTabDates.map((weekIso) => {
          const isSelected = weekIso === selectedWeekIso;
          const label = formatWeekTabLabel(weekIso);
          return (
            <button
              key={weekIso}
              type="button"
              onClick={() => setSelectedMonday(new Date(weekIso + 'T00:00:00'))}
              className={`py-2.5 px-3.5 text-xs font-semibold transition-all border-b-2 shrink-0 cursor-pointer ${
                isSelected
                  ? 'border-brand-primary text-brand-primary font-bold'
                  : 'border-transparent text-brand-text-muted hover:text-brand-text hover:border-brand-border/60'
              }`}
            >
              {label}
            </button>
          );
        })}
      </div>

      {/* Main Grid View */}
      <div className="flex-1 min-w-0">
        {loading ? (
          <div className="p-12 text-center text-brand-text-muted">Loading week timesheet...</div>
        ) : activeTimesheet ? (
          <TimesheetWeekView
            key={activeTimesheet.id}
            timesheetId={activeTimesheet.id}
            onRegisterLogEffortTrigger={(fn) => {
              triggerLogEffortRef.current = fn;
            }}
            onStatusChange={(newStatus) => {
              setTimesheets((prev) =>
                prev.map((t) => (t.id === activeTimesheet.id ? { ...t, status: newStatus } : t))
              );
              setActiveTimesheet((prev) => (prev ? { ...prev, status: newStatus } : null));
            }}
          />
        ) : (
          <div className="p-12 text-center bg-brand-surface border border-brand-border rounded-xl">
            <p className="text-brand-text-muted">No timesheet found for this week.</p>
            <Button
              variant="primary"
              size="sm"
              onClick={() => createTimesheet({ week_start_date: selectedWeekIso }).then(loadTimesheets)}
              className="mt-4"
            >
              Create Timesheet
            </Button>
          </div>
        )}
      </div>
    </div>
  );
};

export default MyTimesheetsPage;
