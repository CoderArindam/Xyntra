import React from 'react';
import { AlertCircle, RefreshCw } from 'lucide-react';

export interface WidgetErrorProps {
  title?: string;
  message?: string;
  onRetry?: () => void;
  className?: string;
}

export const WidgetError: React.FC<WidgetErrorProps> = ({
  title = "Failed to load data",
  message = "An error occurred while loading this section.",
  onRetry,
  className = "",
}) => {
  return (
    <div
      className={`p-6 rounded-2xl bg-red-500/5 border border-red-500/20 flex flex-col items-center justify-center text-center space-y-3 ${className}`}
      role="alert"
    >
      <div className="w-10 h-10 rounded-full bg-red-500/10 border border-red-500/20 flex items-center justify-center text-red-400 shrink-0">
        <AlertCircle className="w-5 h-5" />
      </div>

      <div className="space-y-1">
        <h4 className="text-sm font-bold text-brand-text">{title}</h4>
        <p className="text-xs text-brand-text-muted max-w-sm">{message}</p>
      </div>

      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-2 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/30 text-xs font-semibold transition-colors cursor-pointer"
          aria-label="Retry loading data"
        >
          <RefreshCw className="w-3.5 h-3.5" /> Retry
        </button>
      )}
    </div>
  );
};

export default WidgetError;
