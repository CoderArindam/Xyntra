import React from 'react';
import { CheckCircle2, Clock, Calendar, Briefcase } from 'lucide-react';
import SummaryCard from './SummaryCard';
import { type MyWorkSummary as SummaryType } from '../../api/myWorkApi';

interface MyWorkSummaryProps {
  summary: SummaryType | null;
  activeFilter?: string;
  onFilterClick?: (filter: string) => void;
}

const MyWorkSummary: React.FC<MyWorkSummaryProps> = ({ summary, activeFilter, onFilterClick }) => {
  if (!summary) return null;

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      <SummaryCard 
        title="Assigned Tasks" 
        value={summary.assigned} 
        icon={<Briefcase size={20} className="text-brand-primary" />} 
        colorClass="hover:border-brand-primary" 
        onClick={() => onFilterClick?.('all')}
        isActive={activeFilter === 'all'}
      />
      <SummaryCard 
        title="Due Today" 
        value={summary.due_today} 
        icon={<Clock size={20} className="text-orange-500" />} 
        colorClass="hover:border-orange-500" 
        onClick={() => onFilterClick?.('today')}
        isActive={activeFilter === 'today'}
      />
      <SummaryCard 
        title="Overdue" 
        value={summary.overdue} 
        icon={<Calendar size={20} className="text-red-500" />} 
        colorClass="hover:border-red-500" 
        onClick={() => onFilterClick?.('overdue')}
        isActive={activeFilter === 'overdue'}
      />
      <SummaryCard 
        title="Completed This Week" 
        value={summary.completed_this_week} 
        icon={<CheckCircle2 size={20} className="text-green-500" />} 
        colorClass="hover:border-green-500" 
        onClick={() => onFilterClick?.('completed')}
        isActive={activeFilter === 'completed'}
      />
    </div>
  );
};

export default MyWorkSummary;
