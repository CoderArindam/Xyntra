import React from 'react';
import { Check } from 'lucide-react';

const GRADIENTS = [
  { id: 'blue', class: 'bg-gradient-to-br from-blue-400 to-indigo-600' },
  { id: 'purple', class: 'bg-gradient-to-br from-purple-400 to-indigo-600' },
  { id: 'emerald', class: 'bg-gradient-to-br from-emerald-400 to-teal-600' },
  { id: 'orange', class: 'bg-gradient-to-br from-orange-400 to-rose-600' },
  { id: 'gray', class: 'bg-gradient-to-br from-gray-300 to-gray-600' },
];

interface ProjectCoverPickerProps {
  value: string;
  onChange: (gradient: string) => void;
}

export const ProjectCoverPicker: React.FC<ProjectCoverPickerProps> = ({ value, onChange }) => {
  return (
    <div className="flex flex-wrap gap-4">
      {GRADIENTS.map(g => (
        <button
          key={g.id}
          type="button"
          onClick={() => onChange(g.id)}
          className={`w-24 h-16 rounded-xl flex items-center justify-center transition-all shadow-sm ${g.class} ${
            value === g.id ? 'ring-2 ring-offset-2 ring-brand-primary dark:ring-offset-brand-bg scale-105' : 'hover:scale-105 opacity-80 hover:opacity-100'
          }`}
          title={g.id.charAt(0).toUpperCase() + g.id.slice(1)}
        >
          {value === g.id && <Check size={20} className="text-white shadow-sm" />}
        </button>
      ))}
    </div>
  );
};
