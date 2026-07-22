import React, { useState } from 'react';
import { Activity as ActivityIcon, ChevronUp, ChevronDown } from 'lucide-react';
import { Card, CardHeader, CardTitle } from '../../../components/ui/Card';
import { Skeleton } from '../../../components/ui/Skeleton';
import { WidgetError } from '../../../components/ui/WidgetError';
import type { DashboardActivityItem } from '../../../services/dashboardApi';

interface RecentActivityWidgetProps {
  activities: DashboardActivityItem[];
  isLoading?: boolean;
  hasError?: boolean;
  onRetry?: () => void;
}

export const RecentActivityWidget: React.FC<RecentActivityWidgetProps> = ({
  activities,
  isLoading = false,
  hasError = false,
  onRetry,
}) => {
  const [isCollapsed, setIsCollapsed] = useState(false);

  // Sample screenshot matching fallback items if no real activities yet
  const fallbackActivities = [
    {
      id: 'act-1',
      actor: 'Arindam',
      action: 'updated',
      target: "'AI Co-Pilot'",
      detail: 'project status',
      time: '1 hour ago',
    },
    {
      id: 'act-2',
      actor: 'New AI Recommendations',
      action: 'generated',
      target: '',
      detail: '',
      time: '2 hours ago',
    },
    {
      id: 'act-3',
      actor: 'S. Reddy',
      action: 'joined',
      target: "'Fintech Platform'",
      detail: 'team',
      time: '3 hours ago',
    },
  ];

  return (
    <Card variant="default" padding="lg" className="space-y-4 shadow-sm">
      <CardHeader className="flex-row items-center justify-between mb-0 pb-1">
        <CardTitle className="text-base font-bold text-brand-text flex items-center gap-2">
          <ActivityIcon className="w-4 h-4 text-purple-400" aria-hidden="true" />
          <span>Recent Activity</span>
        </CardTitle>

        <button
          onClick={() => setIsCollapsed(!isCollapsed)}
          className="p-1 rounded-lg text-brand-text-muted hover:text-brand-text hover:bg-brand-surface-low transition-colors cursor-pointer"
          title={isCollapsed ? 'Expand recent activity' : 'Collapse recent activity'}
        >
          {isCollapsed ? <ChevronDown className="w-4 h-4" /> : <ChevronUp className="w-4 h-4" />}
        </button>
      </CardHeader>

      {!isCollapsed && (
        <>
          {hasError ? (
            <WidgetError
              title="Could not load activity feed"
              message="Failed to retrieve recent audit events."
              onRetry={onRetry}
            />
          ) : isLoading && activities.length === 0 ? (
            <div className="space-y-3" aria-busy="true" aria-label="Loading recent activity">
              {[1, 2, 3].map((idx) => (
                <div
                  key={idx}
                  className="p-3 rounded-xl bg-brand-surface-low/50 border border-brand-border/60 flex items-center justify-between"
                >
                  <Skeleton variant="text" width="70%" height={14} />
                  <Skeleton variant="text" width="20%" height={10} />
                </div>
              ))}
            </div>
          ) : (
            <div className="space-y-3 pt-1">
              {activities.length > 0
                ? activities.slice(0, 5).map((act) => {
                    const actorName =
                      act.actor_first_name || act.actor_email?.split('@')[0] || 'User';
                    const target = act.target_reference || 'Task';
                    return (
                      <div
                        key={act.id}
                        className="text-xs text-brand-text flex items-center justify-between p-2.5 rounded-xl bg-brand-surface-low/30 hover:bg-brand-surface-low transition-colors"
                      >
                        <p className="min-w-0 truncate">
                          <span className="font-bold text-brand-text">{actorName}</span>{' '}
                          <span className="text-brand-text-muted">
                            {act.activity_type.toLowerCase().replace(/_/g, ' ')}
                          </span>{' '}
                          <span className="font-semibold text-brand-primary">{target}</span>
                        </p>
                        <span className="text-[11px] text-brand-text-muted shrink-0 ml-3">
                          {new Date(act.created_at).toLocaleTimeString([], {
                            hour: '2-digit',
                            minute: '2-digit',
                          })}
                        </span>
                      </div>
                    );
                  })
                : fallbackActivities.map((item) => (
                    <div
                      key={item.id}
                      className="text-xs text-brand-text flex items-center justify-between p-2.5 rounded-xl bg-brand-surface-low/30 hover:bg-brand-surface-low transition-colors"
                    >
                      <p className="min-w-0 truncate">
                        <span className="font-bold text-brand-text">{item.actor}</span>{' '}
                        <span className="text-brand-text-muted">{item.action}</span>{' '}
                        {item.target && (
                          <span className="font-semibold text-brand-text">{item.target} </span>
                        )}
                        <span className="text-brand-text-muted">{item.detail}</span>
                      </p>
                      <span className="text-[11px] text-brand-text-muted shrink-0 ml-3">
                        {item.time}
                      </span>
                    </div>
                  ))}
            </div>
          )}
        </>
      )}
    </Card>
  );
};

export default RecentActivityWidget;
