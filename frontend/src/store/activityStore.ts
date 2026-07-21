import { create } from 'zustand';
import { getTaskActivity } from '../services/activityApi';
import type { CanonicalActivity as Activity } from '../services/activityApi';

interface ActivityState {
  activitiesByTask: Record<number, Activity[]>;
  cursorByTask: Record<number, number | null>;
  hasMoreByTask: Record<number, boolean>;
  loading: Record<number, boolean>;
  error: Record<number, string | null>;
  
  fetchActivity: (taskId: number, limit?: number) => Promise<void>;
  appendActivity: (taskId: number, activity: Partial<Activity> & { entity_type: string, entity_id: number, activity_type: string }) => void;
  clearActivity: (taskId: number) => void;
}

export const useActivityStore = create<ActivityState>((set, get) => ({
  activitiesByTask: {},
  cursorByTask: {},
  hasMoreByTask: {},
  loading: {},
  error: {},

  fetchActivity: async (taskId, limit = 50, reset = true) => {
    set((state) => ({
      loading: { ...state.loading, [taskId]: true },
      error: { ...state.error, [taskId]: null },
      ...(reset ? { cursorByTask: { ...state.cursorByTask, [taskId]: null } } : {})
    }));

    try {
      const cursor = reset ? null : (get().cursorByTask[taskId] || null);
      const response = await getTaskActivity(taskId, cursor, limit);
      
      set((state) => {
        const currentList = reset ? [] : (state.activitiesByTask[taskId] || []);
        
        // Merge server response with current optimistic items
        const map = new Map<number, Activity>();
        response.data.forEach(a => map.set(a.id, a));
        currentList.forEach(a => {
          if (!map.has(a.id)) {
            map.set(a.id, a);
          }
        });

        const sorted = Array.from(map.values()).sort((a, b) => 
          new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
        );

        return {
          activitiesByTask: {
            ...state.activitiesByTask,
            [taskId]: sorted
          },
          hasMoreByTask: {
            ...state.hasMoreByTask,
            [taskId]: response.meta.has_more
          },
          cursorByTask: {
            ...state.cursorByTask,
            [taskId]: response.meta.cursor ? Number(response.meta.cursor) : null
          },
          loading: { ...state.loading, [taskId]: false }
        };
      });
    } catch (error: any) {
      set((state) => ({
        error: { ...state.error, [taskId]: error.message || 'Failed to fetch activity' },
        loading: { ...state.loading, [taskId]: false }
      }));
    }
  },

  appendActivity: (taskId, partialActivity) => {
    const newActivity: Activity = {
      ...partialActivity,
      id: partialActivity.id ?? Math.floor(Math.random() * -1000000), // Temporary negative ID
      created_at: partialActivity.created_at ?? new Date().toISOString(),
    } as Activity;

    set((state) => {
      const current = state.activitiesByTask[taskId] || [];
      return {
        activitiesByTask: {
          ...state.activitiesByTask,
          [taskId]: [newActivity, ...current].sort((a, b) => 
            new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
          )
        }
      };
    });
  },

  clearActivity: (taskId) => {
    set((state) => {
      const { [taskId]: _, ...restActivities } = state.activitiesByTask;
      const { [taskId]: __, ...restHasMore } = state.hasMoreByTask;
      const { [taskId]: ___, ...restCursor } = state.cursorByTask;
      return {
        activitiesByTask: restActivities,
        hasMoreByTask: restHasMore,
        cursorByTask: restCursor
      };
    });
  }
}));
