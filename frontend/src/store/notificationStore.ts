import { create } from 'zustand';
import { 
  getNotifications, 
  markNotificationRead, 
  markAllRead, 
  deleteNotification,
  markBatchRead
} from '../services/notificationsApi';
import type { Notification } from '../services/notificationsApi';
import toast from 'react-hot-toast';

interface NotificationState {
  notifications: Notification[];
  unreadCount: number;
  total: number;
  hasMore: boolean;
  isLoading: boolean;
  
  fetchNotifications: (offset?: number) => Promise<void>;
  markAsRead: (id: number) => Promise<void>;
  markAllAsRead: () => Promise<void>;
  markBatchAsRead: (ids: number[]) => Promise<void>;
  removeNotification: (id: number) => Promise<void>;
}

export const useNotificationStore = create<NotificationState>((set, get) => ({
  notifications: [],
  unreadCount: 0,
  total: 0,
  hasMore: false,
  isLoading: false,
  cursor: null,

  fetchNotifications: async (currentCursor: number | null = null) => {
    set({ isLoading: true });
    try {
      const response = await getNotifications(currentCursor, 20);
      
      set((state) => {
        const isFirstPage = currentCursor === null;
        const existingNotifications = isFirstPage ? [] : state.notifications;
        const newNotifications = response.data;
        
        return {
          notifications: [...existingNotifications, ...newNotifications],
          unreadCount: response.data.filter(n => !n.is_read).length,
          hasMore: response.meta.has_more,
          cursor: response.meta.cursor ? Number(response.meta.cursor) : null,
          isLoading: false,
        };
      });
    } catch (error) {
      console.error('Failed to fetch notifications', error);
      toast.error('Failed to load notifications');
    } finally {
      set({ isLoading: false });
    }
  },

  markAsRead: async (id: number) => {
    const { notifications, unreadCount } = get();
    const notification = notifications.find(n => n.id === id);
    
    if (!notification || notification.is_read) return;

    // Optimistic update
    set({
      notifications: notifications.map(n => n.id === id ? { ...n, is_read: true } : n),
      unreadCount: Math.max(0, unreadCount - 1)
    });

    try {
      await markNotificationRead(id);
    } catch (error) {
      // Rollback
      set({
        notifications,
        unreadCount
      });
      toast.error('Failed to mark notification as read');
    }
  },

  markBatchAsRead: async (ids: number[]) => {
    const { notifications, unreadCount } = get();
    const unreadIdsToMark = notifications.filter(n => ids.includes(n.id) && !n.is_read).map(n => n.id);
    
    if (unreadIdsToMark.length === 0) return;

    // Optimistic update
    set({
      notifications: notifications.map(n => ids.includes(n.id) ? { ...n, is_read: true } : n),
      unreadCount: Math.max(0, unreadCount - unreadIdsToMark.length)
    });

    try {
      await markBatchRead(ids);
    } catch (error) {
      // Rollback
      set({
        notifications,
        unreadCount
      });
      toast.error('Failed to mark notifications as read');
    }
  },

  markAllAsRead: async () => {
    const { notifications, unreadCount } = get();
    
    // Optimistic update
    set({
      notifications: notifications.map(n => ({ ...n, is_read: true })),
      unreadCount: 0
    });

    try {
      await markAllRead();
    } catch (error) {
      // Rollback
      set({
        notifications,
        unreadCount
      });
      toast.error('Failed to mark all as read');
    }
  },

  removeNotification: async (id: number) => {
    const { notifications, unreadCount } = get();
    const notification = notifications.find(n => n.id === id);
    
    if (!notification) return;

    // Optimistic update
    set({
      notifications: notifications.filter(n => n.id !== id),
      unreadCount: notification.is_read ? unreadCount : Math.max(0, unreadCount - 1),
      total: get().total - 1
    });

    try {
      await deleteNotification(id);
    } catch (error) {
      // Rollback
      set({
        notifications,
        unreadCount,
        total: get().total + 1
      });
      toast.error('Failed to delete notification');
    }
  }
}));
