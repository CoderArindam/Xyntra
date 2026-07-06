import React, { useEffect } from 'react';
import { useActivityStore } from '../../../store/activityStore';
import type { Activity } from '../../../services/activityApi';
import ActivityGroup from './ActivityGroup';
import ActivitySkeleton from './ActivitySkeleton';
import ActivityEmptyState from './ActivityEmptyState';

interface ActivityTimelineProps {
  taskId: number;
}

// Helper to group activities by date
const groupActivities = (activities: Activity[]) => {
  const groups: Record<string, Activity[]> = {};
  
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  
  const yesterday = new Date(today);
  yesterday.setDate(yesterday.getDate() - 1);

  activities.forEach(activity => {
    const activityDate = new Date(activity.created_at);
    const dateOnly = new Date(activityDate);
    dateOnly.setHours(0, 0, 0, 0);

    let label = '';
    if (dateOnly.getTime() === today.getTime()) {
      label = 'Today';
    } else if (dateOnly.getTime() === yesterday.getTime()) {
      label = 'Yesterday';
    } else if (today.getTime() - dateOnly.getTime() < 7 * 24 * 60 * 60 * 1000) {
      label = 'Earlier this week';
    } else if (today.getTime() - dateOnly.getTime() < 30 * 24 * 60 * 60 * 1000) {
      label = 'Earlier this month';
    } else {
      label = activityDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
    }

    if (!groups[label]) {
      groups[label] = [];
    }
    groups[label].push(activity);
  });

  return groups;
};

const ActivityTimeline: React.FC<ActivityTimelineProps> = ({ taskId }) => {
  const { activitiesByTask, loading, error, fetchActivity } = useActivityStore();
  const activities = activitiesByTask[taskId];
  const isLoading = loading[taskId];
  const errorMessage = error[taskId];

  useEffect(() => {
    // Only fetch if we don't have activities for this task yet
    if (!activities && !isLoading && !errorMessage) {
      fetchActivity(taskId);
    }
  }, [taskId, activities, isLoading, errorMessage, fetchActivity]);

  if (errorMessage) {
    return (
      <div className="p-4 text-center text-sm text-red-500 bg-red-500/10 rounded-lg">
        {errorMessage}
      </div>
    );
  }

  if (isLoading && !activities) {
    return (
      <div className="space-y-6 pt-2">
        <ActivitySkeleton />
        <ActivitySkeleton />
        <ActivitySkeleton />
      </div>
    );
  }

  if (!activities || activities.length === 0) {
    return <ActivityEmptyState />;
  }

  const grouped = groupActivities(activities);

  return (
    <div className="pt-2 animate-in fade-in slide-in-from-bottom-2 duration-300">
      {Object.entries(grouped).map(([dateLabel, groupActivities]) => (
        <ActivityGroup 
          key={dateLabel} 
          dateLabel={dateLabel} 
          activities={groupActivities} 
        />
      ))}
    </div>
  );
};

export default ActivityTimeline;
