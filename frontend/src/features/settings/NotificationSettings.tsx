import React, { useState, useEffect } from 'react';
import { useNotificationStore } from '../../store/notificationStore';
import NotificationItem from '../notifications/NotificationItem';
import { 
  Bell, 
  CheckCheck, 
  RefreshCw, 
  Loader2, 
  Mail, 
  Smartphone, 
  Sliders, 
  Inbox
} from 'lucide-react';

export const NotificationSettings: React.FC = () => {
  const { 
    notifications, 
    unreadCount, 
    isLoading, 
    hasMore, 
    cursor, 
    fetchNotifications, 
    markAllAsRead, 
    markAsRead, 
    markAsUnread, 
    removeNotification 
  } = useNotificationStore();

  const [activeView, setActiveView] = useState<'feed' | 'preferences'>('feed');
  const [feedFilter, setFeedFilter] = useState<'all' | 'unread'>('all');

  // Preferences UI mock state
  const [preferences, setPreferences] = useState({
    taskAssignedEmail: true,
    taskAssignedInApp: true,
    commentsEmail: true,
    commentsInApp: true,
    dueDatesEmail: true,
    dueDatesInApp: true,
    boardUpdatesEmail: false,
    boardUpdatesInApp: true,
    meetingProposalsEmail: true,
    meetingProposalsInApp: true,
  });

  useEffect(() => {
    fetchNotifications(null);
  }, [fetchNotifications]);

  const togglePref = (key: keyof typeof preferences) => {
    setPreferences(prev => ({ ...prev, [key]: !prev[key] }));
  };

  const filteredNotifications = notifications.filter(n => {
    if (feedFilter === 'unread') return !n.is_read;
    return true;
  });

  return (
    <div className="space-y-8 animate-in fade-in duration-200">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-brand-text">Notifications</h1>
        <p className="text-sm text-brand-text-muted mt-1">
          Manage your notification feed, review unread items, and configure alert preferences.
        </p>
      </div>

      {/* Main Tab Navigation */}
      <div className="flex border-b border-brand-border gap-6">
        <button
          onClick={() => setActiveView('feed')}
          className={`pb-3 text-sm font-semibold transition-colors border-b-2 flex items-center gap-2 ${
            activeView === 'feed'
              ? 'border-brand-primary text-brand-primary'
              : 'border-transparent text-brand-text-muted hover:text-brand-text'
          }`}
        >
          <Inbox size={17} />
          Notification Feed
          {unreadCount > 0 && (
            <span className="ml-1 bg-brand-primary text-white text-xs px-2 py-0.5 rounded-full font-bold">
              {unreadCount}
            </span>
          )}
        </button>

        <button
          onClick={() => setActiveView('preferences')}
          className={`pb-3 text-sm font-semibold transition-colors border-b-2 flex items-center gap-2 ${
            activeView === 'preferences'
              ? 'border-brand-primary text-brand-primary'
              : 'border-transparent text-brand-text-muted hover:text-brand-text'
          }`}
        >
          <Sliders size={17} />
          Notification Preferences
        </button>
      </div>

      {/* Tab 1: Notification Feed */}
      {activeView === 'feed' && (
        <div className="bg-brand-surface border border-brand-border rounded-xl shadow-sm overflow-hidden">
          {/* Feed Toolbar */}
          <div className="flex flex-wrap items-center justify-between p-4 border-b border-brand-border bg-brand-surface-low gap-3">
            <div className="flex gap-2">
              <button
                onClick={() => setFeedFilter('all')}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                  feedFilter === 'all'
                    ? 'bg-brand-primary text-white'
                    : 'bg-brand-surface border border-brand-border text-brand-text-muted hover:text-brand-text'
                }`}
              >
                All ({notifications.length})
              </button>
              <button
                onClick={() => setFeedFilter('unread')}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                  feedFilter === 'unread'
                    ? 'bg-brand-primary text-white'
                    : 'bg-brand-surface border border-brand-border text-brand-text-muted hover:text-brand-text'
                }`}
              >
                Unread ({unreadCount})
              </button>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => fetchNotifications(null)}
                className="p-1.5 text-brand-text-muted hover:text-brand-text hover:bg-brand-surface-low rounded-lg transition-colors"
                title="Refresh notifications"
              >
                <RefreshCw size={16} className={isLoading ? 'animate-spin' : ''} />
              </button>

              {unreadCount > 0 && (
                <button
                  onClick={() => markAllAsRead()}
                  className="px-3 py-1.5 text-xs font-semibold text-brand-primary hover:bg-brand-primary/10 rounded-lg flex items-center gap-1.5 transition-colors border border-brand-primary/20"
                >
                  <CheckCheck size={15} />
                  Mark all as read
                </button>
              )}
            </div>
          </div>

          {/* Feed List */}
          <div className="divide-y divide-brand-border">
            {isLoading && notifications.length === 0 ? (
              <div className="p-12 flex flex-col items-center justify-center text-brand-text-muted">
                <Loader2 size={28} className="animate-spin mb-2 opacity-50" />
                <p className="text-sm font-medium">Loading notifications...</p>
              </div>
            ) : filteredNotifications.length === 0 ? (
              <div className="p-12 flex flex-col items-center justify-center text-center">
                <div className="w-12 h-12 bg-brand-surface-low rounded-full flex items-center justify-center mb-3 text-brand-text-muted">
                  <Bell size={22} />
                </div>
                <h3 className="text-sm font-semibold text-brand-text">No notifications found</h3>
                <p className="text-xs text-brand-text-muted mt-1">
                  {feedFilter === 'unread' ? "You have read all your notifications!" : "You don't have any notifications right now."}
                </p>
              </div>
            ) : (
              filteredNotifications.map(notification => (
                <NotificationItem
                  key={notification.id}
                  notification={notification}
                  onMarkRead={markAsRead}
                  onMarkUnread={markAsUnread}
                  onDelete={removeNotification}
                />
              ))
            )}
          </div>

          {/* Pagination Footer */}
          {hasMore && (
            <div className="p-4 border-t border-brand-border bg-brand-surface-low text-center">
              <button
                onClick={() => fetchNotifications(cursor)}
                disabled={isLoading}
                className="px-4 py-2 text-xs font-semibold text-brand-primary hover:bg-brand-primary/10 rounded-lg transition-colors disabled:opacity-50"
              >
                {isLoading ? <Loader2 size={16} className="animate-spin inline mr-2" /> : null}
                Load more notifications
              </button>
            </div>
          )}
        </div>
      )}

      {/* Tab 2: Notification Preferences */}
      {activeView === 'preferences' && (
        <div className="bg-brand-surface border border-brand-border rounded-xl p-6 shadow-sm space-y-6">
          <div className="border-b border-brand-border pb-4">
            <h2 className="text-lg font-semibold text-brand-text">Notification Channels & Delivery</h2>
            <p className="text-xs text-brand-text-muted mt-0.5">
              Customize how and when you receive updates across Email and In-App channels.
            </p>
          </div>

          <div className="space-y-6">
            {/* Preference Group: Task Assignments */}
            <div className="flex items-start justify-between py-2 border-b border-brand-border/60 last:border-0">
              <div className="pr-4">
                <h3 className="text-sm font-semibold text-brand-text">Task Assignments & Updates</h3>
                <p className="text-xs text-brand-text-muted mt-0.5">
                  Receive notifications when a task is assigned to you or updated.
                </p>
              </div>
              <div className="flex items-center gap-4 shrink-0">
                <label className="flex items-center gap-2 cursor-pointer text-xs font-medium text-brand-text">
                  <Mail size={15} className="text-brand-text-muted" />
                  Email
                  <input
                    type="checkbox"
                    checked={preferences.taskAssignedEmail}
                    onChange={() => togglePref('taskAssignedEmail')}
                    className="w-4 h-4 rounded border-brand-border text-brand-primary focus:ring-brand-primary"
                  />
                </label>
                <label className="flex items-center gap-2 cursor-pointer text-xs font-medium text-brand-text">
                  <Smartphone size={15} className="text-brand-text-muted" />
                  In-App
                  <input
                    type="checkbox"
                    checked={preferences.taskAssignedInApp}
                    onChange={() => togglePref('taskAssignedInApp')}
                    className="w-4 h-4 rounded border-brand-border text-brand-primary focus:ring-brand-primary"
                  />
                </label>
              </div>
            </div>

            {/* Preference Group: Comments & Mentions */}
            <div className="flex items-start justify-between py-2 border-b border-brand-border/60 last:border-0">
              <div className="pr-4">
                <h3 className="text-sm font-semibold text-brand-text">Comments & @Mentions</h3>
                <p className="text-xs text-brand-text-muted mt-0.5">
                  Notify me when someone mentions me or leaves a comment on my tasks.
                </p>
              </div>
              <div className="flex items-center gap-4 shrink-0">
                <label className="flex items-center gap-2 cursor-pointer text-xs font-medium text-brand-text">
                  <Mail size={15} className="text-brand-text-muted" />
                  Email
                  <input
                    type="checkbox"
                    checked={preferences.commentsEmail}
                    onChange={() => togglePref('commentsEmail')}
                    className="w-4 h-4 rounded border-brand-border text-brand-primary focus:ring-brand-primary"
                  />
                </label>
                <label className="flex items-center gap-2 cursor-pointer text-xs font-medium text-brand-text">
                  <Smartphone size={15} className="text-brand-text-muted" />
                  In-App
                  <input
                    type="checkbox"
                    checked={preferences.commentsInApp}
                    onChange={() => togglePref('commentsInApp')}
                    className="w-4 h-4 rounded border-brand-border text-brand-primary focus:ring-brand-primary"
                  />
                </label>
              </div>
            </div>

            {/* Preference Group: Due Dates */}
            <div className="flex items-start justify-between py-2 border-b border-brand-border/60 last:border-0">
              <div className="pr-4">
                <h3 className="text-sm font-semibold text-brand-text">Due Date Reminders</h3>
                <p className="text-xs text-brand-text-muted mt-0.5">
                  Get reminded before task due dates expire.
                </p>
              </div>
              <div className="flex items-center gap-4 shrink-0">
                <label className="flex items-center gap-2 cursor-pointer text-xs font-medium text-brand-text">
                  <Mail size={15} className="text-brand-text-muted" />
                  Email
                  <input
                    type="checkbox"
                    checked={preferences.dueDatesEmail}
                    onChange={() => togglePref('dueDatesEmail')}
                    className="w-4 h-4 rounded border-brand-border text-brand-primary focus:ring-brand-primary"
                  />
                </label>
                <label className="flex items-center gap-2 cursor-pointer text-xs font-medium text-brand-text">
                  <Smartphone size={15} className="text-brand-text-muted" />
                  In-App
                  <input
                    type="checkbox"
                    checked={preferences.dueDatesInApp}
                    onChange={() => togglePref('dueDatesInApp')}
                    className="w-4 h-4 rounded border-brand-border text-brand-primary focus:ring-brand-primary"
                  />
                </label>
              </div>
            </div>

            {/* Preference Group: Board Updates */}
            <div className="flex items-start justify-between py-2 border-b border-brand-border/60 last:border-0">
              <div className="pr-4">
                <h3 className="text-sm font-semibold text-brand-text">Board & Member Activity</h3>
                <p className="text-xs text-brand-text-muted mt-0.5">
                  Updates on board additions, column changes, and workspace roles.
                </p>
              </div>
              <div className="flex items-center gap-4 shrink-0">
                <label className="flex items-center gap-2 cursor-pointer text-xs font-medium text-brand-text">
                  <Mail size={15} className="text-brand-text-muted" />
                  Email
                  <input
                    type="checkbox"
                    checked={preferences.boardUpdatesEmail}
                    onChange={() => togglePref('boardUpdatesEmail')}
                    className="w-4 h-4 rounded border-brand-border text-brand-primary focus:ring-brand-primary"
                  />
                </label>
                <label className="flex items-center gap-2 cursor-pointer text-xs font-medium text-brand-text">
                  <Smartphone size={15} className="text-brand-text-muted" />
                  In-App
                  <input
                    type="checkbox"
                    checked={preferences.boardUpdatesInApp}
                    onChange={() => togglePref('boardUpdatesInApp')}
                    className="w-4 h-4 rounded border-brand-border text-brand-primary focus:ring-brand-primary"
                  />
                </label>
              </div>
            </div>

            {/* Preference Group: Meeting Proposals */}
            <div className="flex items-start justify-between py-2 border-b border-brand-border/60 last:border-0">
              <div className="pr-4">
                <h3 className="text-sm font-semibold text-brand-text">AI Meeting Proposals Queue</h3>
                <p className="text-xs text-brand-text-muted mt-0.5">
                  Notify managers when automated meeting transcript task proposals are ready for review.
                </p>
              </div>
              <div className="flex items-center gap-4 shrink-0">
                <label className="flex items-center gap-2 cursor-pointer text-xs font-medium text-brand-text">
                  <Mail size={15} className="text-brand-text-muted" />
                  Email
                  <input
                    type="checkbox"
                    checked={preferences.meetingProposalsEmail}
                    onChange={() => togglePref('meetingProposalsEmail')}
                    className="w-4 h-4 rounded border-brand-border text-brand-primary focus:ring-brand-primary"
                  />
                </label>
                <label className="flex items-center gap-2 cursor-pointer text-xs font-medium text-brand-text">
                  <Smartphone size={15} className="text-brand-text-muted" />
                  In-App
                  <input
                    type="checkbox"
                    checked={preferences.meetingProposalsInApp}
                    onChange={() => togglePref('meetingProposalsInApp')}
                    className="w-4 h-4 rounded border-brand-border text-brand-primary focus:ring-brand-primary"
                  />
                </label>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default NotificationSettings;
