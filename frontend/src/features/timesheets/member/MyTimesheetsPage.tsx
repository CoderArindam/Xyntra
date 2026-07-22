import React, { useEffect, useState, useCallback } from 'react';
import {
  ChevronLeft,
  ChevronRight,
  Calendar as CalendarIcon,
  AlertTriangle,
  Clock,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import type { Timesheet } from '../../../services/timesheetService';
import {
  getMyTimesheets,
  createTimesheet,
} from '../../../services/timesheetService';
import { TimesheetWeekView } from './TimesheetWeekView';
import { Button } from '../../../components/ui/Button';
import { Badge } from '../../../components/ui/Badge';

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
  const [showSidePanelMobile, setShowSidePanelMobile] = useState(false);

  const selectedWeekIso = formatIsoDate(selectedMonday);
  const currentMondayIso = formatIsoDate(getMonday(new Date()));
  const isCurrentWeek = selectedWeekIso === currentMondayIso;

  // Load user's recent timesheets
  const loadTimesheets = useCallback(async () => {
    setLoading(true);
    try {
      const list = await getMyTimesheets();
      setTimesheets(list);

      // Check if timesheet for selected week exists (compare YYYY-MM-DD prefix)
      let match = list.find((t) => (t.week_start_date || '').slice(0, 10) === selectedWeekIso);

      // If no timesheet exists, auto-create or fetch existing for selected week
      if (!match) {
        try {
          const created = await createTimesheet({ week_start_date: selectedWeekIso });
          if (created) {
            match = created;
            setTimesheets((prev) => {
              const exists = prev.some((t) => t.id === created.id);
              return exists ? prev : [created, ...prev];
            });
          }
        } catch (err: any) {
          const refreshed = await getMyTimesheets();
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

  // Handle Week Navigation
  const navigateWeek = (weeks: number) => {
    const next = new Date(selectedMonday);
    next.setDate(selectedMonday.getDate() + weeks * 7);
    setSelectedMonday(next);
  };

  const jumpToCurrentWeek = () => {
    setSelectedMonday(getMonday(new Date()));
  };

  // Find any rejected timesheets for top banner alert
  const rejectedTimesheet = timesheets.find((t) => t.status === 'REJECTED');

  const getStatusBadge = (status?: string) => {
    if (!status) return null;
    switch (status.toUpperCase()) {
      case 'APPROVED':
        return <Badge variant="success">APPROVED</Badge>;
      case 'SUBMITTED':
        return <Badge variant="warning">SUBMITTED</Badge>;
      case 'REJECTED':
        return <Badge variant="danger">REJECTED</Badge>;
      case 'DRAFT':
      default:
        return <Badge variant="secondary">DRAFT</Badge>;
    }
  };

  return (
    <div className="flex flex-col min-h-screen bg-brand-surface-low/30 text-brand-text p-4 md:p-8">
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

      {/* Main Page Header & Navigation */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Clock className="text-brand-primary" size={24} /> My Timesheets
          </h1>
          <p className="text-xs text-brand-text-muted mt-1">
            Log weekly hours against projects and submit for manager approval.
          </p>
        </div>

        {/* Week Selector Bar */}
        <div className="flex items-center gap-2 bg-brand-surface border border-brand-border p-1.5 rounded-xl shadow-sm">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigateWeek(-1)}
            className="p-1.5 text-brand-text-muted hover:text-brand-text"
            title="Previous Week"
          >
            <ChevronLeft size={18} />
          </Button>

          <Button
            variant={isCurrentWeek ? 'primary' : 'outline'}
            size="sm"
            onClick={jumpToCurrentWeek}
            className="text-xs font-semibold px-3"
          >
            Current Week
          </Button>

          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigateWeek(1)}
            className="p-1.5 text-brand-text-muted hover:text-brand-text"
            title="Next Week"
          >
            <ChevronRight size={18} />
          </Button>

          <div className="h-5 w-px bg-brand-border mx-1" />

          {/* Current status chip */}
          {getStatusBadge(activeTimesheet?.status)}
        </div>
      </div>

      {/* Grid Content Layout with Side Panel */}
      <div className="flex flex-col lg:flex-row gap-6">
        {/* Main Content Area */}
        <div className="flex-1 min-w-0">
          {loading ? (
            <div className="p-12 text-center text-brand-text-muted">Loading week timesheet...</div>
          ) : activeTimesheet ? (
            <TimesheetWeekView
              key={activeTimesheet.id}
              timesheetId={activeTimesheet.id}
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

        {/* Side Panel: Past Timesheets (Collapsible on mobile) */}
        <div className="lg:w-72 shrink-0">
          <div className="bg-brand-surface border border-brand-border rounded-xl p-4 shadow-md">
            <div
              className="flex items-center justify-between cursor-pointer lg:cursor-default"
              onClick={() => setShowSidePanelMobile(!showSidePanelMobile)}
            >
              <h2 className="text-sm font-bold text-brand-text flex items-center gap-2">
                <CalendarIcon size={16} className="text-brand-primary" /> Recent Weeks
              </h2>
              <button className="lg:hidden text-brand-text-muted">
                {showSidePanelMobile ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
              </button>
            </div>

            <div className={`mt-3 space-y-2 ${showSidePanelMobile ? 'block' : 'hidden lg:block'}`}>
              {timesheets.slice(0, 12).map((ts) => {
                const isSelected = ts.week_start_date === selectedWeekIso;
                return (
                  <div
                    key={ts.id}
                    onClick={() => {
                      setSelectedMonday(new Date(ts.week_start_date + 'T00:00:00'));
                      setShowSidePanelMobile(false);
                    }}
                    className={`p-2.5 rounded-lg border text-xs cursor-pointer transition-all ${
                      isSelected
                        ? 'bg-brand-primary/10 border-brand-primary text-brand-text font-semibold'
                        : 'bg-brand-surface-low/40 border-brand-border/60 hover:bg-brand-surface-low text-brand-text-muted hover:text-brand-text'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span>Week of {ts.week_start_date}</span>
                      {getStatusBadge(ts.status)}
                    </div>
                    <div className="text-[11px] font-mono text-brand-text-muted">
                      {ts.total_hours.toFixed(1)} hrs logged
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default MyTimesheetsPage;
