import { create } from 'zustand';
import { getProjectSettings, updateProjectSettings, archiveProject, type ProjectSettingsUpdate, type ProjectSettingsResponse } from '../api/projectSettingsApi';
import { useBoardStore } from './boardStore';
import toast from 'react-hot-toast';

interface ProjectSettingsState {
  currentSettings: ProjectSettingsResponse | null;
  isLoading: boolean;
  isSaving: boolean;
  isArchiving: boolean;
  fetchSettings: (boardId: number) => Promise<void>;
  updateSettings: (boardId: number, updates: ProjectSettingsUpdate) => Promise<void>;
  archiveProject: (boardId: number) => Promise<void>;
}

export const useProjectSettingsStore = create<ProjectSettingsState>((set, get) => ({
  currentSettings: null,
  isLoading: false,
  isSaving: false,
  isArchiving: false,

  fetchSettings: async (boardId: number) => {
    set({ isLoading: true });
    try {
      const data = await getProjectSettings(boardId);
      set({ currentSettings: data });
    } catch (error: any) {
      console.error('Failed to fetch project settings:', error);
      toast.error('Failed to load project settings');
    } finally {
      set({ isLoading: false });
    }
  },

  updateSettings: async (boardId: number, updates: ProjectSettingsUpdate) => {
    set({ isSaving: true });
    try {
      // Optimistic update to global board store so UI changes instantly
      const globalBoards = useBoardStore.getState().boards;
      const boardIndex = globalBoards.findIndex(b => b.id === boardId);
      if (boardIndex !== -1) {
        const updatedBoard = { ...globalBoards[boardIndex], ...updates };
        const newBoards = [...globalBoards];
        newBoards[boardIndex] = updatedBoard;
        useBoardStore.setState({ boards: newBoards });
      }

      const data = await updateProjectSettings(boardId, updates);
      set({ currentSettings: data });
      
      // Update global store with canonical response
      const updatedGlobalBoards = useBoardStore.getState().boards;
      const updatedBoardIndex = updatedGlobalBoards.findIndex(b => b.id === boardId);
      if (updatedBoardIndex !== -1) {
         const newBoards = [...updatedGlobalBoards];
         newBoards[updatedBoardIndex] = data.settings;
         useBoardStore.setState({ boards: newBoards });
      }
      toast.success('Project settings saved');
    } catch (error: any) {
      console.error('Failed to update project settings:', error);
      toast.error(error.message || 'Failed to update settings');
    } finally {
      set({ isSaving: false });
    }
  },

  archiveProject: async (boardId: number) => {
    set({ isArchiving: true });
    try {
      const data = await archiveProject(boardId);
      
      // Update from global board store so it moves to Archived section
      const globalBoards = useBoardStore.getState().boards;
      const boardIndex = globalBoards.findIndex(b => b.id === boardId);
      if (boardIndex !== -1) {
         const newBoards = [...globalBoards];
         newBoards[boardIndex] = data.settings;
         useBoardStore.setState({ boards: newBoards });
      }
      
      // Clear project-specific state
      set({ currentSettings: null });
      
      toast.success('Project archived successfully.');
    } catch (error: any) {
      console.error('Failed to archive project:', error);
      toast.error(error.message || 'Failed to archive project');
    } finally {
      set({ isArchiving: false });
    }
  }
}));
