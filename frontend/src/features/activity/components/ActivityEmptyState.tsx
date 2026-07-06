import React from 'react';
import { Activity as ActivityIcon } from 'lucide-react';

const ActivityEmptyState: React.FC = () => {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <div className="w-12 h-12 rounded-full bg-brand-surface-low flex items-center justify-center mb-4">
        <ActivityIcon size={24} className="text-brand-text-muted" />
      </div>
      <h3 className="text-sm font-medium text-brand-text-primary mb-1">No activity yet</h3>
      <p className="text-xs text-brand-text-muted max-w-[250px]">
        Changes made to this task will appear here.
      </p>
    </div>
  );
};

export default ActivityEmptyState;
