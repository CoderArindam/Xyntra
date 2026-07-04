import React from 'react';
import { CalendarClock } from 'lucide-react';

interface DueDatePickerProps {
  dueDate: string | null | undefined;
  onChange: (newDueDate: string | null) => void;
  disabled?: boolean;
}

const DueDatePicker: React.FC<DueDatePickerProps> = ({ dueDate, onChange, disabled }) => {
  const currentDueDate = dueDate ? new Date(dueDate).toISOString().split('T')[0] : "";

  const handleDueDateChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    if (val) {
      const dateObj = new Date(val);
      if (!isNaN(dateObj.getTime())) {
        onChange(dateObj.toISOString());
      }
    } else {
      onChange(null);
    }
  };

  return (
    <div className="flex items-center gap-2">
      <CalendarClock size={14} className="text-brand-text-muted" />
      <input 
        type="date"
        value={currentDueDate}
        onChange={handleDueDateChange}
        disabled={disabled}
        className="bg-brand-surface border border-brand-border rounded px-2 py-1 text-sm outline-none focus:border-brand-primary min-w-[140px]"
      />
    </div>
  );
};

export default DueDatePicker;
