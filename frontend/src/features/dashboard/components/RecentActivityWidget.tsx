import React from 'react';
import { Activity as ActivityIcon, Clock } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardDescription } from '../../../components/ui/Card';
import { Skeleton } from '../../../components/ui/Skeleton';
import { WidgetError } from '../../../components/ui/WidgetError';
import type { DashboardActivityItem } from '../../../services/dashboardApi';
import { formatActivity } from '../../activity/utils/activityFormatter';

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
  return (
    <Card variant="default" padding="lg" className="space-y-6">
      <CardHeader className="flex-row items-center justify-between mb-0">
        <div className="space-y-1">
          <CardTitle>
            <ActivityIcon className="w-5 h-5 text-purple-400" aria-hidden="true" />
            <span>Recent Organization Activity</span>
          </CardTitle>
          <CardDescription>
            Audit feed of recent task creations, status moves, assignees, and comments across all boards
          </CardDescription>
        </div>
        <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-purple-500/10 text-purple-400 border border-purple-500/20">
          Live Feed
        </span>
      </CardHeader>

      {hasError ? (
        <WidgetError
          title="Could not load activity feed"
          message="Failed to retrieve recent audit events."
          onRetry={onRetry}
        />
      ) : isLoading && activities.length === 0 ? (
        /* Shape-accurate Activity Row Skeletons */
        <div className="space-y-3" aria-busy="true" aria-label="Loading recent activity">
          {[1, 2, 3, 4].map((idx) => (
            <div key={idx} className="p-3.5 rounded-xl bg-brand-surface-low/50 border border-brand-border/60 flex items-center justify-between gap-4">
              <div className="flex items-center gap-3 flex-1">
                <Skeleton variant="rectangular" width={32} height={32} />
                <div className="space-y-1.5 flex-1">
                  <Skeleton variant="text" width="70%" height={14} />
                  <Skeleton variant="text" width="40%" height={10} />
                </div>
              </div>
              <Skeleton variant="circular" width={28} height={28} />
            </div>
          ))}
        </div>
      ) : activities.length === 0 ? (
        /* Purposeful Empty State for 0 Activity */
        <div className="p-8 text-center border border-dashed border-brand-border rounded-xl space-y-2">
          <Clock className="w-8 h-8 mx-auto text-brand-text-muted opacity-60" aria-hidden="true" />
          <h4 className="text-xs font-bold text-brand-text">No recent activity recorded yet</h4>
          <p className="text-[11px] text-brand-text-muted max-w-sm mx-auto">
            Audit logs will automatically appear here as team members create tasks, move cards across columns, or leave comments.
          </p>
        </div>
      ) : (
        /* Activity Feed Items */
        <div className="space-y-3" aria-label="Activity list">
          {activities.slice(0, 10).map((act) => {
            const formatted = formatActivity({
              id: act.id,
              organization_id: act.organization_id,
              entity_type: act.entity_type as any,
              entity_id: act.entity_id,
              actor_id: act.actor_id || null,
              activity_type: act.activity_type as any,
              old_value: act.old_value ?? null,
              new_value: act.new_value ?? null,
              metadata: act.metadata ?? null,
              created_at: act.created_at,
              actor_first_name: act.actor_first_name ?? null,
              actor_last_name: act.actor_last_name ?? null,
              actor_email: act.actor_email ?? null,
              actor_avatar_url: act.actor_avatar_url ?? null,
              target_reference: act.target_reference ?? null,
            });

            const IconComponent = formatted.icon;
            const actorInitials = act.actor_first_name
              ? `${act.actor_first_name[0]}${act.actor_last_name ? act.actor_last_name[0] : ''}`.toUpperCase()
              : act.actor_email
              ? act.actor_email.substring(0, 2).toUpperCase()
              : 'SY';

            return (
              <div
                key={act.id}
                className="p-3.5 rounded-xl bg-brand-surface-low/50 hover:bg-brand-surface-low border border-brand-border/60 flex items-center justify-between gap-4 text-xs transition-colors"
              >
                <div className="flex items-center gap-3 min-w-0 flex-1">
                  <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 border ${formatted.accentColor}`}>
                    <IconComponent className="w-4 h-4" aria-hidden="true" />
                  </div>

                  <div className="min-w-0 flex-1">
                    <div className="text-brand-text font-medium text-xs leading-snug truncate">
                      {formatted.description}
                    </div>
                    <div className="flex items-center gap-2 text-[10px] text-brand-text-muted mt-0.5">
                      <span>{new Date(act.created_at).toLocaleString()}</span>
                      {act.target_reference && (
                        <>
                          <span>·</span>
                          <span className="font-mono text-brand-primary font-semibold">
                            {act.target_reference}
                          </span>
                        </>
                      )}
                    </div>
                  </div>
                </div>

                <div
                  className="w-7 h-7 rounded-full bg-brand-surface-container border border-brand-border flex items-center justify-center text-[10px] font-bold text-brand-text shrink-0"
                  title={act.actor_email || 'User'}
                  aria-label={`User ${act.actor_first_name || act.actor_email || 'System'}`}
                >
                  {actorInitials}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </Card>
  );
};
