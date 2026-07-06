import React, { useState, useRef, useEffect } from 'react';
import { Calendar, ChevronDown, Check } from 'lucide-react';

export type DueDateFilterOption = "All" | "Today" | "This Week" | "Overdue" | "No Due Date";

interface DueDateFilterProps {
  value: DueDateFilterOption;
  onChange: (value: DueDateFilterOption) => void;
}

const options: DueDateFilterOption[] = ["All", "Today", "This Week", "Overdue", "No Due Date"];

export const DueDateFilter: React.FC<DueDateFilterProps> = ({ value, onChange }) => {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <div className="relative" ref={containerRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-1.5 rounded-xl border border-brand-border bg-brand-surface text-sm font-medium hover:bg-brand-surface-low transition text-brand-text"
      >
        <Calendar size={16} className="text-brand-text-muted" />
        <span>{value === "All" ? "Any Due Date" : value}</span>
        <ChevronDown size={14} className={`text-brand-text-muted transition-transform ${isOpen ? "rotate-180" : ""}`} />
      </button>

      {isOpen && (
        <div className="absolute top-full mt-2 left-0 w-48 bg-brand-surface border border-brand-border rounded-xl shadow-lg z-20 py-2">
          {options.map((opt) => (
            <button
              key={opt}
              onClick={() => {
                onChange(opt);
                setIsOpen(false);
              }}
              className="w-full text-left px-4 py-2 text-sm hover:bg-brand-surface-low flex items-center justify-between"
            >
              <span className={value === opt ? "text-brand-primary font-medium" : "text-brand-text"}>
                {opt === "All" ? "Any Due Date" : opt}
              </span>
              {value === opt && <Check size={14} className="text-brand-primary" />}
            </button>
          ))}
        </div>
      )}
    </div>
  );
};

export default DueDateFilter;
