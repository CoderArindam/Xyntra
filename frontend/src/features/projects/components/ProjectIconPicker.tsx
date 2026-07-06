import React from 'react';
import { Smile } from 'lucide-react';

interface ProjectIconPickerProps {
  value: string;
  onChange: (icon: string) => void;
}

// In the future this can be expanded to a full emoji picker or Lucide icon selector.
// For now, it provides a few presets or allows typing an emoji.
export const ProjectIconPicker: React.FC<ProjectIconPickerProps> = ({ value, onChange }) => {
  return (
    <div className="flex items-center gap-4">
      <div className="w-12 h-12 bg-brand-surface border border-brand-border rounded-xl flex items-center justify-center text-2xl shadow-sm">
        {value || '🚀'}
      </div>
      <div>
        <label className="text-xs text-brand-text-muted mb-1 block">Project Icon</label>
        <div className="relative">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-brand-text-muted">
            <Smile size={16} />
          </div>
          <input
            type="text"
            value={value}
            onChange={(e) => onChange(e.target.value)}
            className="pl-10 pr-4 py-2 bg-brand-bg border border-brand-border rounded-lg text-sm focus:border-brand-primary focus:ring-1 focus:ring-brand-primary outline-none transition-shadow max-w-[120px]"
            maxLength={2}
            placeholder="e.g. 🚀"
          />
        </div>
      </div>
    </div>
  );
};
