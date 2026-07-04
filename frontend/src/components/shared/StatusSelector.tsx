import React from 'react';
import { Columns } from 'lucide-react';
import { type Column } from '../../api/tasksApi';

interface StatusSelectorProps {
  columnId: number | undefined;
  columns: Column[];
  onChange: (newColumnId: number) => void;
  disabled?: boolean;
}

const StatusSelector: React.FC<StatusSelectorProps> = ({ columnId, columns, onChange, disabled }) => {
  return (
    <div className="flex items-center gap-2">
      <Columns size={14} className="text-brand-text-muted" />
      <select
        value={columnId ?? ""}
        onChange={(e) => onChange(parseInt(e.target.value, 10))}
        disabled={disabled}
        className="bg-brand-surface border border-brand-border rounded px-2 py-1 text-sm outline-none focus:border-brand-primary"
      >
        <option value="" disabled>Select status</option>
        {columns.map(c => (
          <option key={c.id} value={c.id}>{c.name}</option>
        ))}
      </select>
    </div>
  );
};

export default StatusSelector;
