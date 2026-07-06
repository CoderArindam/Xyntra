import React from 'react';
import type { Activity } from '../../../services/activityApi';
import { formatActivity } from '../utils/activityFormatter';
import ActivityAvatar from './ActivityAvatar';
import ActivityIcon from './ActivityIcon';

interface ActivityItemProps {
  activity: Activity;
  isLast?: boolean;
}

const ActivityItem: React.FC<ActivityItemProps> = ({ activity, isLast = false }) => {
  const formatted = formatActivity(activity);

  // Formatting relative time e.g., "2 minutes ago"
  const rtf = new Intl.RelativeTimeFormat('en', { numeric: 'auto' });
  const getRelativeTime = (dateString: string) => {
    const date = new Date(dateString);
    const diffMs = date.getTime() - new Date().getTime();
    const diffMins = Math.round(diffMs / 60000);
    const diffHours = Math.round(diffMs / 3600000);
    const diffDays = Math.round(diffMs / 86400000);

    if (Math.abs(diffMins) < 60) return rtf.format(diffMins, 'minute');
    if (Math.abs(diffHours) < 24) return rtf.format(diffHours, 'hour');
    return rtf.format(diffDays, 'day');
  };

  return (
    <div className="flex gap-4 relative">
      {!isLast && (
        <div className="absolute left-4 top-10 bottom-[-16px] w-[1px] bg-brand-border" />
      )}
      
      <div className="relative z-10 flex-shrink-0 mt-1">
        <ActivityAvatar activity={activity} />
        <div className="absolute -bottom-1 -right-1 bg-brand-surface rounded-full p-[2px]">
          <ActivityIcon icon={formatted.icon} accentColor={formatted.accentColor} />
        </div>
      </div>

      <div className="flex-1 pb-6 mt-[2px]">
        <div className="flex items-baseline justify-between gap-4">
          <p className="text-sm text-brand-text-primary leading-tight">
            {formatted.description}
          </p>
          <span className="text-xs text-brand-text-muted whitespace-nowrap flex-shrink-0" title={new Date(activity.created_at).toLocaleString()}>
            {getRelativeTime(activity.created_at)}
          </span>
        </div>
      </div>
    </div>
  );
};

export default ActivityItem;
