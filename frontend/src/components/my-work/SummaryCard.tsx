import React from 'react';

interface SummaryCardProps {
  title: string;
  value: number;
  icon: React.ReactNode;
  colorClass: string;
  onClick?: () => void;
  isActive?: boolean;
}

const SummaryCard: React.FC<SummaryCardProps> = ({ title, value, icon, colorClass, onClick, isActive }) => {
  return (
    <div 
      onClick={onClick}
      className={`p-6 rounded-2xl border bg-brand-surface shadow-sm transition-colors ${onClick ? 'cursor-pointer' : ''} ${isActive ? 'ring-2 ring-brand-primary border-transparent ' + colorClass : 'border-brand-border ' + colorClass}`}
    >
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-medium text-brand-text-muted">{title}</h3>
        <div className="opacity-70">{icon}</div>
      </div>
      <p className="text-3xl font-bold text-brand-text">{value}</p>
    </div>
  );
};

export default SummaryCard;
