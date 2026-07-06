import React from 'react';
import type { Activity } from '../../../services/activityApi';
import ActivityItem from './ActivityItem';

interface ActivityGroupProps {
  dateLabel: string;
  activities: Activity[];
}

const ActivityGroup: React.FC<ActivityGroupProps> = ({ dateLabel, activities }) => {
  return (
    <div className="mb-6 last:mb-0">
      <h4 className="text-xs font-semibold text-brand-text-muted uppercase tracking-wider mb-4 pl-[3.25rem]">
        {dateLabel}
      </h4>
      <div className="flex flex-col">
        {activities.map((activity, index) => (
          <ActivityItem 
            key={activity.id} 
            activity={activity} 
            isLast={index === activities.length - 1} 
          />
        ))}
      </div>
    </div>
  );
};

export default ActivityGroup;
