import React from 'react';

interface ProjectStatisticsCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: React.ReactNode;
}

export const ProjectStatisticsCard: React.FC<ProjectStatisticsCardProps> = ({ title, value, subtitle, icon }) => {
  return (
    <div className="bg-brand-surface border border-brand-border rounded-xl p-5 flex items-center gap-4 shadow-sm">
      <div className="w-12 h-12 bg-brand-surface-low rounded-lg flex items-center justify-center text-brand-text-muted">
        {icon}
      </div>
      <div>
        <p className="text-xs font-semibold text-brand-text-muted uppercase tracking-wider">{title}</p>
        <div className="flex items-baseline gap-2 mt-1">
          <h4 className="text-2xl font-bold text-brand-text leading-none">{value}</h4>
          {subtitle && <span className="text-xs text-brand-text-muted">{subtitle}</span>}
        </div>
      </div>
    </div>
  );
};
