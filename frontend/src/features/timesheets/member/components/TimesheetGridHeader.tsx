import React from 'react';
import { Calendar, Plus, Save, Check, Loader2 } from 'lucide-react';
import { Button } from '../../../../components/ui/Button';

interface TimesheetGridHeaderProps {
  entryCount: number;
  readOnly: boolean;
  isSaving: boolean;
  saveSuccess: boolean;
  onLogEffort: () => void;
}

export const TimesheetGridHeader: React.FC<TimesheetGridHeaderProps> = ({
  entryCount,
  readOnly,
  isSaving,
  saveSuccess,
  onLogEffort,
}) => (
  <div className="flex items-center justify-between mb-3 px-1">
    <div className="flex items-center gap-3">
      <div className="flex items-center gap-2">
        <Calendar size={16} className="text-brand-primary" />
        <span className="text-sm font-medium text-brand-text">
          Grid View ({entryCount} entries)
        </span>
      </div>
      {!readOnly && (
        <Button
          variant="primary"
          size="sm"
          onClick={onLogEffort}
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
);
