import api from './axios';

export interface CanonicalActivity {
    id: number;
    organization_id: number;
    entity_type: string;
    entity_id: number;
    activity_type: string;
    old_value: Record<string, any> | null;
    new_value: Record<string, any> | null;
    metadata: Record<string, any> | null;
    created_at: string;
    
    actor_id: number | null;
    actor_first_name: string | null;
    actor_last_name: string | null;
    actor_avatar_url: string | null;
    actor_email: string | null;
    
    target_reference: string | null;
}

export interface ActivityResponse {
  data: CanonicalActivity[];
  meta: {
    cursor: string | null;
    has_more: boolean;
  };
}

export const getTaskActivity = async (taskId: number, cursor: number | null = null, limit: number = 50): Promise<ActivityResponse> => {
  const response = await api.get(`/tasks/${taskId}/activity`, { params: { cursor, limit } });
  return response.data;
};

export type Activity = CanonicalActivity;
export type ActivityActor = any;
