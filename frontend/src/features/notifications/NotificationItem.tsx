import React from 'react';
import { useNavigate } from 'react-router-dom';
import type { Notification } from '../../services/notificationsApi';
import { formatActivity } from '../activity/utils/activityFormatter';
import { Check, MailOpen, Trash2 } from 'lucide-react';
import { useUiStore } from '../../store/uiStore';
import { resolveNotificationDestination, executeNotificationNavigation } from './utils/notificationResolver';

interface NotificationItemProps {
  notification: Notification;
  onMarkRead: (id: number) => void;
  onMarkUnread?: (id: number) => void;
  onDelete: (id: number) => void;
  onClosePanel?: () => void;
}

const NotificationItem: React.FC<NotificationItemProps> = ({
  notification,
  onMarkRead,
  onMarkUnread,
  onDelete,
  onClosePanel,
}) => {
  const navigate = useNavigate();
  const { is_read } = notification;
  const mockActivity = {
    activity_type: notification.activity_type,
    actor_first_name: notification.activity_actor_first_name,
    actor_last_name: notification.activity_actor_last_name,
    actor_email: 'Someone',
    old_value: notification.activity_old_value,
    new_value: notification.activity_new_value,
  } as any;
  const formatted = formatActivity(mockActivity, notification.user_id);
  const openTaskModal = useUiStore((state) => state.openTaskModal);

  const handleClick = () => {
    if (!is_read) {
      onMarkRead(notification.id);
    }

    const destination = resolveNotificationDestination(notification);
    executeNotificationNavigation(destination, {
      navigate,
      openTaskModal,
    });

    if (onClosePanel) {
      onClosePanel();
    }
  };

  return (
    <div
      className={`group relative flex gap-4 p-4 hover:bg-brand-surface-low transition-colors border-b border-brand-border last:border-0 cursor-pointer ${
        !is_read ? "bg-brand-surface font-medium" : "bg-transparent opacity-75"
      }`}
      onClick={handleClick}
    >
      {/* Unread Indicator */}
      {!is_read && (
        <div className="absolute left-0 top-0 bottom-0 w-1 bg-brand-primary" />
      )}

      {/* Icon */}
      <div
        className={`mt-1 w-10 h-10 rounded-full flex items-center justify-center shrink-0 border ${formatted.accentColor}`}
      >
        <formatted.icon size={18} />
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <p className="text-sm text-brand-text mb-1">{formatted.description}</p>

        {notification.activity_target_reference && (
          <p className="text-xs font-medium text-brand-text-muted truncate mb-2">
            on{" "}
            <span className="text-brand-text-primary font-semibold">
              {notification.activity_target_reference}
            </span>
          </p>
        )}

        <span className="text-[11px] text-brand-text-muted">
          {new Date(notification.created_at).toLocaleString([], {
            month: "short",
            day: "numeric",
            hour: "2-digit",
            minute: "2-digit",
          })}
        </span>
      </div>

      {/* Quick Actions */}
      <div className="flex flex-col gap-1.5 opacity-0 group-hover:opacity-100 transition-opacity justify-center">
        {!is_read ? (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onMarkRead(notification.id);
            }}
            className="p-1.5 text-brand-text-muted hover:text-brand-primary hover:bg-brand-surface-low rounded-md transition-colors"
            title="Mark as read"
          >
            <Check size={16} />
          </button>
        ) : (
          onMarkUnread && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onMarkUnread(notification.id);
              }}
              className="p-1.5 text-brand-text-muted hover:text-brand-primary hover:bg-brand-surface-low rounded-md transition-colors"
              title="Mark as unread"
            >
              <MailOpen size={16} />
            </button>
          )
        )}
        <button
          onClick={(e) => {
            e.stopPropagation();
            onDelete(notification.id);
          }}
          className="p-1.5 text-brand-text-muted hover:text-red-500 hover:bg-red-500/10 rounded-md transition-colors"
          title="Delete notification"
        >
          <Trash2 size={16} />
        </button>
      </div>
    </div>
  );
};

export default NotificationItem;
