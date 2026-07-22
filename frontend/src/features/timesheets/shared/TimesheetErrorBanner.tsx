import React from 'react';
import { AlertCircle, AlertTriangle, Info, Clock, X } from 'lucide-react';

export interface TimesheetApiError {
  error_code: string;
  detail: string;
}

export interface TimesheetErrorBannerProps {
  error: TimesheetApiError | { error_code?: string; detail?: string } | string | null;
  onDismiss?: () => void;
}

export const parseTimesheetError = (err: any): TimesheetApiError | null => {
  if (!err) return null;
  if (typeof err === 'string') {
    return { error_code: '', detail: err };
  }
  const data = err.response?.data || err;
  if (!data) {
    return { error_code: '', detail: err.message || 'An unexpected error occurred' };
  }
  if (typeof data.detail === 'object' && data.detail !== null) {
    return {
      error_code: data.detail.error_code || data.error_code || '',
      detail: data.detail.detail || JSON.stringify(data.detail),
    };
  }
  if (typeof data.detail === 'string') {
    return {
      error_code: data.error_code || '',
      detail: data.detail,
    };
  }
  return {
    error_code: data.error_code || '',
    detail: data.message || 'An error occurred',
  };
};

export const TimesheetErrorBanner: React.FC<TimesheetErrorBannerProps> = ({
  error,
  onDismiss,
}) => {
  if (!error) return null;

  const parsedError: TimesheetApiError = typeof error === 'string'
    ? { error_code: '', detail: error }
    : {
        error_code: error.error_code || '',
        detail: error.detail || '',
      };

  if (!parsedError.error_code && !parsedError.detail) return null;

  const { error_code, detail } = parsedError;

  if (error_code === 'SUBMISSION_DEADLINE_PASSED') {
    return (
      <div className="p-4 mb-4 rounded-lg border border-amber-300 bg-amber-50 dark:bg-amber-950/40 dark:border-amber-700/50 text-amber-900 dark:text-amber-200 flex items-start gap-3 shadow-sm transition-all">
        <Clock className="w-5 h-5 text-amber-600 dark:text-amber-400 mt-0.5 shrink-0" />
        <div className="flex-1 text-sm font-medium">
          <div>Your submission window has closed. Contact your manager.</div>
          {detail && detail !== "The submission deadline for this timesheet has passed." && (
            <div className="text-xs mt-1 text-amber-700 dark:text-amber-300 font-normal">{detail}</div>
          )}
        </div>
        {onDismiss && (
          <button onClick={onDismiss} className="text-amber-500 hover:text-amber-700 dark:hover:text-amber-200 p-0.5">
            <X className="w-4 h-4" />
          </button>
        )}
      </div>
    );
  }

  if (error_code === 'OVERTIME_BLOCKED') {
    return (
      <div className="p-4 mb-4 rounded-lg border border-red-300 bg-red-50 dark:bg-red-950/40 dark:border-red-700/50 text-red-900 dark:text-red-200 flex items-start gap-3 shadow-sm transition-all">
        <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400 mt-0.5 shrink-0" />
        <div className="flex-1 text-sm font-medium">
          <div>Overtime is blocked by policy. Reduce hours to maximum per day.</div>
          {detail && detail !== "This entry would exceed the maximum hours per day. Overtime entries are blocked by policy." && (
            <div className="text-xs mt-1 text-red-700 dark:text-red-300 font-normal">{detail}</div>
          )}
        </div>
        {onDismiss && (
          <button onClick={onDismiss} className="text-red-500 hover:text-red-700 dark:hover:text-red-200 p-0.5">
            <X className="w-4 h-4" />
          </button>
        )}
      </div>
    );
  }

  if (error_code === 'NO_APPROVER_CONFIGURED') {
    return (
      <div className="p-4 mb-4 rounded-lg border border-blue-300 bg-blue-50 dark:bg-blue-950/40 dark:border-blue-700/50 text-blue-900 dark:text-blue-200 flex items-start gap-3 shadow-sm transition-all">
        <Info className="w-5 h-5 text-blue-600 dark:text-blue-400 mt-0.5 shrink-0" />
        <div className="flex-1 text-sm font-medium">
          <div>Submitted. Your organization hasn't assigned an approver yet — a superadmin has been notified.</div>
        </div>
        {onDismiss && (
          <button onClick={onDismiss} className="text-blue-500 hover:text-blue-700 dark:hover:text-blue-200 p-0.5">
            <X className="w-4 h-4" />
          </button>
        )}
      </div>
    );
  }

  if (error_code === 'EMPTY_TIMESHEET') {
    return (
      <div className="p-4 mb-4 rounded-lg border border-yellow-300 bg-yellow-50 dark:bg-yellow-950/40 dark:border-yellow-700/50 text-yellow-900 dark:text-yellow-200 flex items-start gap-3 shadow-sm transition-all">
        <AlertTriangle className="w-5 h-5 text-yellow-600 dark:text-yellow-400 mt-0.5 shrink-0" />
        <div className="flex-1 text-sm font-medium">
          <div>Add at least one time entry before submitting.</div>
        </div>
        {onDismiss && (
          <button onClick={onDismiss} className="text-yellow-500 hover:text-yellow-700 dark:hover:text-yellow-200 p-0.5">
            <X className="w-4 h-4" />
          </button>
        )}
      </div>
    );
  }

  // Generic fallback
  return (
    <div className="p-4 mb-4 rounded-lg border border-red-200 bg-red-50 dark:bg-red-950/30 dark:border-red-800/50 text-red-800 dark:text-red-200 flex items-start gap-3 shadow-sm transition-all">
      <AlertTriangle className="w-5 h-5 text-red-500 mt-0.5 shrink-0" />
      <div className="flex-1 text-sm font-medium">{detail || 'An error occurred.'}</div>
      {onDismiss && (
        <button onClick={onDismiss} className="text-red-400 hover:text-red-600 dark:hover:text-red-200 p-0.5">
          <X className="w-4 h-4" />
        </button>
      )}
    </div>
  );
};
