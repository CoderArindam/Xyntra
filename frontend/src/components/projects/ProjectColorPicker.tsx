import React from 'react';
import { Check } from 'lucide-react';

const COLORS = [
  { id: 'blue', class: 'bg-blue-500' },
  { id: 'indigo', class: 'bg-indigo-500' },
  { id: 'emerald', class: 'bg-emerald-500' },
  { id: 'amber', class: 'bg-amber-500' },
  { id: 'rose', class: 'bg-rose-500' },
  { id: 'orange', class: 'bg-orange-500' },
  { id: 'violet', class: 'bg-violet-500' },
  { id: 'gray', class: 'bg-gray-500' },
];

interface ProjectColorPickerProps {
  value: string;
  onChange: (color: string) => void;
}

export const ProjectColorPicker: React.FC<ProjectColorPickerProps> = ({ value, onChange }) => {
  return (
    <div className="flex flex-wrap gap-3">
      {COLORS.map(c => (
        <button
          key={c.id}
          type="button"
          onClick={() => onChange(c.id)}
          className={`w-8 h-8 rounded-full flex items-center justify-center transition-all ${c.class} ${
            value === c.id ? 'ring-2 ring-offset-2 ring-brand-primary dark:ring-offset-brand-bg scale-110' : 'hover:scale-110 opacity-80 hover:opacity-100'
          }`}
          title={c.id.charAt(0).toUpperCase() + c.id.slice(1)}
        >
          {value === c.id && <Check size={16} className="text-white" />}
        </button>
      ))}
    </div>
  );
};
