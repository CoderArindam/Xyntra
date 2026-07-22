import React from "react";
import { AlertTriangle, RotateCcw, Send } from "lucide-react";
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

  const statusUpper = (timesheet.status || "").toUpperCase();
  const isRejected = statusUpper === "REJECTED";
  const isSubmitted = statusUpper === "SUBMITTED";
  const isApproved = statusUpper === "APPROVED";
  const isDraft = statusUpper === "DRAFT";

  const progressPercent = Math.min(100, Math.max(0, (totalHours / targetHours) * 100));

  return (
    <div className="sticky bottom-0 z-30 w-full bg-brand-surface border-t border-brand-border shadow-xl transition-all rounded-b-xl overflow-hidden">
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

      <div className="px-6 py-4 flex flex-col sm:flex-row items-center justify-between gap-6">
        {/* Left: Status chip & Week range label */}
        <div className="flex items-center gap-3 shrink-0">
          {getStatusBadge(timesheet.status)}
          <div className="text-xs font-semibold text-brand-text">
            Week of {startDateStr} – {endDateStr}
          </div>
        </div>

        {/* Center: Weekly Progress Bar */}
        <div className="flex flex-col gap-1.5 w-full sm:max-w-md flex-1">
          <div className="flex items-center justify-between text-xs">
            <span className="font-bold text-brand-text-muted uppercase tracking-wider text-[10px]">
              WEEKLY PROGRESS
            </span>
            <span className="font-mono font-bold text-brand-text text-xs">
              {totalHours.toFixed(1)} / {targetHours.toFixed(1)} hrs
            </span>
          </div>
          <div className="w-full bg-brand-surface-low h-2.5 rounded-full overflow-hidden border border-brand-border/40">
            <div
              className="bg-brand-primary h-full rounded-full transition-all duration-300 shadow-sm"
              style={{ width: `${progressPercent}%` }}
            />
          </div>
        </div>

        {/* Right: Total & Primary Submit / Recall Button */}
        <div className="flex items-center gap-4 shrink-0 justify-end w-full sm:w-auto">
          <div className="text-sm font-semibold text-brand-text">
            Total: <span className="font-mono font-bold">{totalHours.toFixed(1)} hrs</span>
          </div>

          <div>
            {(isDraft || isRejected) && (
              <Button
                variant="primary"
                size="md"
                onClick={onSubmit}
                disabled={isSubmitting || totalHours === 0}
                className="flex items-center gap-2 px-5 py-2.5 bg-brand-primary hover:bg-brand-primary-hover text-white font-semibold text-xs rounded-xl shadow-md cursor-pointer"
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
                className="flex items-center gap-2 border-amber-500/50 text-amber-300 hover:bg-amber-500/10 cursor-pointer"
              >
                <RotateCcw size={15} />
                <span>Recall Timesheet</span>
              </Button>
            )}

            {isApproved && (
              <Badge variant="success" size="md" className="px-3 py-1 text-xs">
                APPROVED
              </Badge>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
