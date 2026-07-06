import api from '../lib/axios';

export interface CanonicalNotification {
    id: number;
    user_id: number;
    is_read: boolean;
    created_at: string;
    
    activity_id: number;
    activity_entity_type: string;
    activity_entity_id: number;
    activity_type: string;
    activity_target_reference: string | null;
    activity_actor_first_name: string | null;
    activity_actor_last_name: string | null;
    activity_actor_avatar_url: string | null;
}

export type Notification = CanonicalNotification;

export interface NotificationResponse {
  data: CanonicalNotification[];
  meta: {
    cursor: string | null;
    has_more: boolean;
  };
}

export const getNotifications = async (cursor: number | null = null, limit: number = 50): Promise<NotificationResponse> => {
  const params: any = { limit };
  if (cursor !== null) {
    params.cursor = cursor;
  }
  const response = await api.get('/notifications', { params });
  return response.data;
};

export const markNotificationRead = async (id: number): Promise<void> => {
  await api.patch(`/notifications/${id}/read`);
};

export const markBatchRead = async (ids: number[]): Promise<void> => {
  await api.patch('/notifications/read-batch', { notification_ids: ids });
};

export const markAllRead = async (): Promise<void> => {
  await api.patch('/notifications/read-all');
};

export const deleteNotification = async (id: number): Promise<void> => {
  await api.delete(`/notifications/${id}`);
};
