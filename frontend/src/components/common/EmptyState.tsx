import React from 'react';

interface EmptyStateProps {
  icon: React.ReactNode;
  title: React.ReactNode;
  description: React.ReactNode;
  action?: React.ReactNode;
  className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  icon,
  title,
  description,
  action,
  className = ''
}) => {
  return (
    <div className={`w-full flex flex-col items-center justify-center text-center p-12 border-2 border-dashed border-brand-border rounded-2xl bg-brand-surface-low ${className}`}>
      <div className="text-brand-outline mb-4 opacity-50 flex items-center justify-center">
        {icon}
      </div>
      <h3 className="text-lg font-semibold text-brand-text">
        {title}
      </h3>
      <div className="text-sm text-brand-text-muted mt-2 max-w-md">
        {description}
      </div>
      {action && (
        <div className="mt-6">
          {action}
        </div>
      )}
    </div>
  );
};

export default EmptyState;
