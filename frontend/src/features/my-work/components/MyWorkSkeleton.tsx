import React from 'react';

const MyWorkSkeleton: React.FC = () => {
  return (
    <div className="animate-pulse flex flex-col gap-8 w-full max-w-5xl mx-auto py-10 px-8">
      <div className="h-8 bg-brand-surface-low rounded w-48 mb-4"></div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="h-32 bg-brand-surface-low rounded-2xl border border-brand-border"></div>
        ))}
      </div>
      
      <div className="h-6 bg-brand-surface-low rounded w-32 mt-8 mb-4"></div>
      
      <div className="flex flex-col gap-4">
        {[...Array(3)].map((_, i) => (
          <div key={i} className="h-24 bg-brand-surface-low rounded-xl border border-brand-border"></div>
        ))}
      </div>
    </div>
  );
};

export default MyWorkSkeleton;
