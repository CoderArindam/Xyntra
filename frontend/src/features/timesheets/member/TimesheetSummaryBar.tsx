import React from "react";
import { AlertTriangle, CheckCircle2, RotateCcw, Send } from "lucide-react";
import type {
  Timesheet,
  TimesheetDetail,
} from "../../../services/timesheetService";
import type { TimesheetPolicy } from "../../../services/timesheetAdminService";
import { Button } from "../../../components/ui/Button";
import { Badge } from "../../../components/ui/Badge";

export interface TimesheetSummaryBarProps {
  timesheet: Timesheet | TimesheetDetail;
  policy: TimesheetPolicy;
  onSubmit: () => void;
  onRecall: () => void;
  isSubmitting: boolean;
  dayTotals?: number[];
  weekDates?: Date[];
}

export const TimesheetSummaryBar: React.FC<TimesheetSummaryBarProps> = ({
  timesheet,
  policy,
  onSubmit,
  onRecall,
  isSubmitting,
  dayTotals = [0, 0, 0, 0, 0, 0, 0],
  weekDates = [],
}) => {
  const targetHours = policy.standard_hours_per_week || 40;
  const totalHours = timesheet.total_hours || 0;

  // Status badge variant
  const getStatusBadge = (status: string) => {
    switch (status.toUpperCase()) {
      case "APPROVED":
        return <Badge variant="success">APPROVED</Badge>;
      case "SUBMITTED":
        return <Badge variant="warning">SUBMITTED</Badge>;
      case "REJECTED":
        return <Badge variant="danger">REJECTED</Badge>;
      case "DRAFT":
      default:
        return <Badge variant="secondary">DRAFT</Badge>;
    }
  };

  // Format header date range
  const startDateStr = timesheet.week_start_date
    ? new Date(timesheet.week_start_date + "T00:00:00").toLocaleDateString(
        "en-US",
        {
          month: "short",
          day: "numeric",
        },
      )
    : "";
  const endDateStr = timesheet.week_end_date
    ? new Date(timesheet.week_end_date + "T00:00:00").toLocaleDateString(
        "en-US",
        {
          month: "short",
          day: "numeric",
        },
      )
    : "";

  // Total status color
  let totalColorClass = "text-brand-text-muted";
  if (totalHours === targetHours) {
    totalColorClass = "text-emerald-400 font-bold";
  } else if (totalHours > targetHours) {
    totalColorClass = "text-red-400 font-bold";
  }

  const statusUpper = (timesheet.status || "").toUpperCase();
  const isRejected = statusUpper === "REJECTED";
  const isSubmitted = statusUpper === "SUBMITTED";
  const isApproved = statusUpper === "APPROVED";
  const isDraft = statusUpper === "DRAFT";


  return (
    <div className="sticky bottom-0 z-30 w-full bg-brand-surface/95 backdrop-blur-md border-t border-brand-border shadow-2xl transition-all">
      {/* Rejected Banner */}
      {isRejected && timesheet.approver_comment && (
        <div className="bg-red-500/15 border-b border-red-500/30 px-6 py-2 flex items-center gap-2 text-xs text-red-300">
          <AlertTriangle size={14} className="text-red-400 shrink-0" />
          <span>
            <strong className="font-semibold">Rejected:</strong>{" "}
            {timesheet.approver_comment}
          </span>
        </div>
      )}

      <div className="px-6 py-3 flex flex-wrap items-center justify-between gap-4">
        {/* Left: Week Date Range & Status */}
        <div className="flex items-center gap-3">
          {getStatusBadge(timesheet.status)}
          <div className="text-sm font-semibold text-brand-text">
            Week of {startDateStr} – {endDateStr}
          </div>
        </div>

        {/* Center: 7 Day Columns Live Totals */}
        <div className="hidden md:flex items-center gap-2">
          {dayTotals.map((hrs, idx) => {
            const dateObj = weekDates[idx];
            const dayLabel = dateObj
              ? dateObj.toLocaleDateString("en-US", { weekday: "narrow" })
              : ["M", "T", "W", "T", "F", "S", "S"][idx];

            const std = policy.standard_hours_per_day || 8;
            const max = policy.max_hours_per_day || 24;

            let colColor = "bg-brand-surface-low text-brand-text-muted/60";
            if (hrs > max) {
              colColor = "bg-red-500/20 text-red-400 border border-red-500/30";
            } else if (hrs > std) {
              colColor =
                "bg-amber-500/20 text-amber-300 border border-amber-500/30";
            } else if (hrs > 0) {
              colColor =
                "bg-blue-500/20 text-blue-300 border border-blue-500/30";
            }

            return (
              <div
                key={idx}
                className={`flex flex-col items-center justify-center w-11 h-10 rounded text-center transition-colors ${colColor}`}
              >
                <span className="text-[10px] uppercase font-bold opacity-75">
                  {dayLabel}
                </span>
                <span className="text-xs font-mono font-semibold">
                  {hrs > 0 ? hrs.toFixed(1) : "—"}
                </span>
              </div>
            );
          })}
        </div>

        {/* Right: Total & Action Button */}
        <div className="flex items-center gap-6">
          <div className="text-sm font-medium">
            <span className="text-brand-text-muted mr-1.5">Total:</span>
            <span className={`font-mono text-base ${totalColorClass}`}>
              {totalHours.toFixed(1)}
            </span>
            <span className="text-brand-text-muted text-xs">
              {" "}
              / {targetHours.toFixed(1)} hrs
            </span>
          </div>

          <div>
            {(isDraft || isRejected) && (
              <Button
                variant="primary"
                size="md"
                onClick={onSubmit}
                disabled={isSubmitting || totalHours === 0}
                className="flex items-center gap-2 shadow-lg shadow-brand-primary/20"
              >
                <Send size={15} />
                <span>
                  {isSubmitting ? "Submitting..." : "Submit Timesheet"}
                </span>
              </Button>
            )}

            {isSubmitted && policy.allow_member_recall !== false && (
              <Button
                variant="outline"
                size="md"
                onClick={onRecall}
                disabled={isSubmitting}
                className="flex items-center gap-2 border-amber-500/50 text-amber-300 hover:bg-amber-500/10"
              >
                <RotateCcw size={15} />
                <span>{isSubmitting ? "Recalling..." : "Recall"}</span>
              </Button>
            )}

            {isApproved && (
              <div className="flex items-center gap-1.5 text-xs text-emerald-400 font-medium px-3 py-2 bg-emerald-500/10 border border-emerald-500/20 rounded-lg">
                <CheckCircle2 size={16} />
                <span>Approved</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default TimesheetSummaryBar;
