import React from 'react';

const ActivitySkeleton: React.FC = () => {
  return (
    <div className="animate-pulse flex gap-4 w-full pt-4">
      <div className="w-8 h-8 rounded-full bg-brand-surface-low flex-shrink-0" />
      <div className="flex-1 space-y-2 mt-1">
        <div className="h-4 bg-brand-surface-low rounded w-1/4" />
        <div className="h-3 bg-brand-surface-low rounded w-3/4" />
      </div>
    </div>
  );
};

export default ActivitySkeleton;
