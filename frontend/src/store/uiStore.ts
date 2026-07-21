import { create } from 'zustand';

interface UiState {
  selectedTaskId: number | null;
  highlightedCommentId: number | null;
  activeTaskTab: 'comments' | 'attachments' | 'activity';
  isTaskModalOpen: boolean;
  openTaskModal: (taskId: number, options?: { commentId?: number; tab?: 'comments' | 'attachments' | 'activity' }) => void;
  closeTaskModal: () => void;
  isCreateProjectModalOpen: boolean;
  openCreateProjectModal: () => void;
  closeCreateProjectModal: () => void;
  isCreateTaskModalOpen: boolean;
  openCreateTaskModal: () => void;
  closeCreateTaskModal: () => void;
  pageTitle: string;
  setPageTitle: (title: string) => void;
  isSidebarCollapsed: boolean;
  toggleSidebar: () => void;
  setSidebarCollapsed: (collapsed: boolean) => void;
}

export const useUiStore = create<UiState>((set) => ({
  selectedTaskId: null,
  highlightedCommentId: null,
  activeTaskTab: 'comments',
  isTaskModalOpen: false,
  isCreateProjectModalOpen: false,
  isCreateTaskModalOpen: false,
  pageTitle: '',
  isSidebarCollapsed: localStorage.getItem('kanban-sidebar-collapsed') === 'true',

  openTaskModal: (taskId, options) => set({ 
    selectedTaskId: taskId, 
    highlightedCommentId: options?.commentId || null,
    activeTaskTab: options?.tab || 'comments',
    isTaskModalOpen: true 
  }),
  closeTaskModal: () => set({ selectedTaskId: null, highlightedCommentId: null, isTaskModalOpen: false }),

  openCreateProjectModal: () => set({ isCreateProjectModalOpen: true }),
  closeCreateProjectModal: () => set({ isCreateProjectModalOpen: false }),

  openCreateTaskModal: () => set({ isCreateTaskModalOpen: true }),
  closeCreateTaskModal: () => set({ isCreateTaskModalOpen: false }),

  setPageTitle: (title) => set({ pageTitle: title }),
  toggleSidebar: () => set((state) => {
    const newState = !state.isSidebarCollapsed;
    localStorage.setItem('kanban-sidebar-collapsed', String(newState));
    
    // Sync with backend if authenticated/preferences loaded
    // We import dynamically to avoid circular dependency issues during initialization
    import('./preferencesStore').then(({ usePreferencesStore }) => {
      const prefsStore = usePreferencesStore.getState();
      if (prefsStore.preferences) {
        prefsStore.updatePreferences({ sidebar_collapsed: newState }).catch(console.error);
      }
    });

    return { isSidebarCollapsed: newState };
  }),
  setSidebarCollapsed: (collapsed) => set((state) => {
    if (state.isSidebarCollapsed === collapsed) return state; // Avoid infinite loops

    localStorage.setItem('kanban-sidebar-collapsed', String(collapsed));
    return { isSidebarCollapsed: collapsed };
  }),
}));
