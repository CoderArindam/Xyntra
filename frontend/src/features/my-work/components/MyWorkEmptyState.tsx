import React from 'react';
import { CheckCircle2 } from 'lucide-react';

const MyWorkEmptyState: React.FC = () => {
  return (
    <div className="flex flex-col items-center justify-center py-20 px-4 text-center bg-brand-surface rounded-2xl border border-brand-border">
      <div className="w-16 h-16 bg-green-50 rounded-full flex items-center justify-center mb-6">
        <CheckCircle2 size={32} className="text-green-600" />
      </div>
      <h3 className="text-xl font-bold text-brand-text mb-2">You're all caught up 🎉</h3>
      <p className="text-brand-text-muted max-w-sm">
        No tasks are currently assigned to you. Enjoy your day or check other boards for tasks to pick up!
      </p>
    </div>
  );
};

export default MyWorkEmptyState;
