import React from 'react';
import { Flag } from 'lucide-react';

interface PrioritySelectorProps {
  priority: string;
  onChange: (newPriority: string) => void;
  disabled?: boolean;
}

const PrioritySelector: React.FC<PrioritySelectorProps> = ({ priority, onChange, disabled }) => {
  return (
    <div className="flex items-center gap-2">
      <Flag size={14} className="text-brand-text-muted" />
      <select
        value={priority}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        className="bg-brand-surface border border-brand-border rounded px-2 py-1 text-sm outline-none focus:border-brand-primary"
      >
        <option value="Low">Low</option>
        <option value="Medium">Medium</option>
        <option value="High">High</option>
      </select>
    </div>
  );
};

export default PrioritySelector;
