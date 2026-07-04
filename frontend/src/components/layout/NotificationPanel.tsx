import React, { useEffect, useRef } from 'react';
import { useNotificationStore } from '../../store/notificationStore';
import NotificationItem from '../notifications/NotificationItem';
import { Bell, CheckCheck, Loader2 } from 'lucide-react';

interface NotificationPanelProps {
  onClose: () => void;
}

const NotificationPanel: React.FC<NotificationPanelProps> = ({ onClose }) => {
  const { 
    notifications, 
    isLoading, 
    hasMore, 
    fetchNotifications, 
    markAllAsRead,
    markAsRead,
    removeNotification
  } = useNotificationStore();

  const observerTarget = useRef<HTMLDivElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);

  // Grouping logic
  const grouped = React.useMemo(() => {
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);
    const lastWeek = new Date(today);
    lastWeek.setDate(lastWeek.getDate() - 7);

    const groups = {
      'Today': [] as typeof notifications,
      'Yesterday': [] as typeof notifications,
      'Last 7 Days': [] as typeof notifications,
      'Earlier': [] as typeof notifications,
    };

    notifications.forEach(n => {
      const d = new Date(n.created_at);
      if (d >= today) groups['Today'].push(n);
      else if (d >= yesterday) groups['Yesterday'].push(n);
      else if (d >= lastWeek) groups['Last 7 Days'].push(n);
      else groups['Earlier'].push(n);
    });

    return groups;
  }, [notifications]);

  // Initial fetch on mount if empty
  useEffect(() => {
    if (notifications.length === 0) {
      fetchNotifications(0);
    }
  }, [fetchNotifications, notifications.length]);

  // Infinite scroll
  useEffect(() => {
    const observer = new IntersectionObserver(
      entries => {
        if (entries[0].isIntersecting && hasMore && !isLoading) {
          fetchNotifications(notifications.length);
        }
      },
      { threshold: 0.1 }
    );

    if (observerTarget.current) {
      observer.observe(observerTarget.current);
    }

    return () => observer.disconnect();
  }, [hasMore, isLoading, fetchNotifications, notifications.length]);

  // Click outside to close
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        onClose();
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [onClose]);

  return (
    <div 
      ref={panelRef}
      className="absolute top-full right-0 mt-2 w-96 max-h-[85vh] bg-brand-surface border border-brand-border rounded-xl shadow-2xl flex flex-col z-50 overflow-hidden"
    >
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-brand-border bg-brand-surface-low">
        <h3 className="font-semibold text-brand-text flex items-center gap-2">
          <Bell size={18} />
          Notifications
        </h3>
        {notifications.some(n => !n.is_read) && (
          <button 
            onClick={() => markAllAsRead()}
            className="text-xs font-medium text-brand-primary hover:text-brand-primary/80 flex items-center gap-1 transition-colors"
          >
            <CheckCheck size={14} />
            Mark all read
          </button>
        )}
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto">
        {notifications.length === 0 && !isLoading ? (
          <div className="flex flex-col items-center justify-center p-8 text-center">
            <div className="w-12 h-12 bg-brand-surface-low rounded-full flex items-center justify-center mb-3">
              <Bell size={20} className="text-brand-text-muted" />
            </div>
            <p className="text-sm font-medium text-brand-text">All caught up!</p>
            <p className="text-xs text-brand-text-muted mt-1">No new notifications.</p>
          </div>
        ) : (
          Object.entries(grouped).map(([label, items]) => {
            if (items.length === 0) return null;
            return (
              <div key={label}>
                <div className="sticky top-0 bg-brand-surface-low/90 backdrop-blur text-xs font-semibold text-brand-text-muted uppercase tracking-wider px-4 py-2 z-10 border-b border-brand-border/50">
                  {label}
                </div>
                <div>
                  {items.map(n => (
                    <NotificationItem 
                      key={n.id} 
                      notification={n} 
                      onMarkRead={markAsRead}
                      onDelete={removeNotification}
                      onClosePanel={onClose}
                    />
                  ))}
                </div>
              </div>
            );
          })
        )}

        {/* Loading / End of list */}
        {hasMore && (
          <div ref={observerTarget} className="p-4 flex justify-center">
            {isLoading ? <Loader2 size={20} className="animate-spin text-brand-text-muted" /> : <div className="h-4" />}
          </div>
        )}
      </div>
    </div>
  );
};

export default NotificationPanel;
