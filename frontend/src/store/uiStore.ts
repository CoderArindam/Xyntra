import { create } from 'zustand';

interface UiState {
  selectedTaskId: number | null;
  isTaskModalOpen: boolean;
  openTaskModal: (taskId: number) => void;
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
}

export const useUiStore = create<UiState>((set) => ({
  selectedTaskId: null,
  isTaskModalOpen: false,
  isCreateProjectModalOpen: false,
  isCreateTaskModalOpen: false,
  pageTitle: '',
  isSidebarCollapsed: localStorage.getItem('kanban-sidebar-collapsed') === 'true',

  openTaskModal: (taskId) => set({ selectedTaskId: taskId, isTaskModalOpen: true }),
  closeTaskModal: () => set({ selectedTaskId: null, isTaskModalOpen: false }),

  openCreateProjectModal: () => set({ isCreateProjectModalOpen: true }),
  closeCreateProjectModal: () => set({ isCreateProjectModalOpen: false }),

  openCreateTaskModal: () => set({ isCreateTaskModalOpen: true }),
  closeCreateTaskModal: () => set({ isCreateTaskModalOpen: false }),

  setPageTitle: (title) => set({ pageTitle: title }),
  toggleSidebar: () => set((state) => {
    const newState = !state.isSidebarCollapsed;
    localStorage.setItem('kanban-sidebar-collapsed', String(newState));
    return { isSidebarCollapsed: newState };
  }),
}));
