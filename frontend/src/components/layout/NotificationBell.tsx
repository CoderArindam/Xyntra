import React, { useEffect, useState } from 'react';
import { Bell } from 'lucide-react';
import { useNotificationStore } from '../../store/notificationStore';
import NotificationPanel from './NotificationPanel';

const NotificationBell: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);
  const { unreadCount, fetchNotifications } = useNotificationStore();

  useEffect(() => {
    // Initial fetch on mount
    fetchNotifications(undefined);

    // Refetch on window focus
    const onFocus = () => {
      if (!isOpen) fetchNotifications(undefined);
    };
    window.addEventListener('focus', onFocus);
    
    // Poll for new notifications
    const interval = setInterval(() => {
      if (!isOpen) fetchNotifications(undefined);
    }, 15000);

    return () => {
      window.removeEventListener('focus', onFocus);
      clearInterval(interval);
    };
  }, [fetchNotifications, isOpen]);

  const togglePanel = () => {
    if (!isOpen) {
      fetchNotifications(undefined);
    }
    setIsOpen(!isOpen);
  };

  return (
    <div className="relative">
      <button 
        onClick={togglePanel}
        className={`p-2 rounded-full transition-colors relative ${
          isOpen ? 'bg-brand-surface text-brand-primary' : 'text-brand-text-muted hover:text-brand-text hover:bg-brand-surface-low'
        }`}
        aria-label="Notifications"
      >
        <Bell size={20} />
        {unreadCount > 0 && (
          <span className="absolute top-1 right-1.5 flex h-4 w-4 items-center justify-center rounded-full bg-red-500 text-[10px] font-bold text-white ring-2 ring-brand-bg shadow-sm">
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        )}
      </button>

      {isOpen && (
        <NotificationPanel onClose={() => setIsOpen(false)} />
      )}
    </div>
  );
};

export default NotificationBell;
