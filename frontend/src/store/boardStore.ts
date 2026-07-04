import { create } from 'zustand';
import { getBoards, createBoard, deleteBoard, type Board } from '../api/boardsApi';
import toast from 'react-hot-toast';

interface BoardState {
  boards: Board[];
  isFetching: boolean;
  isSubmitting: boolean;
  fetchBoards: () => Promise<void>;
  createNewBoard: (name: string) => Promise<void>;
  removeBoard: (boardId: number) => Promise<void>;
}

export const useBoardStore = create<BoardState>((set, get) => ({
  boards: [],
  isFetching: true,
  isSubmitting: false,

  fetchBoards: async () => {
    set({ isFetching: true });
    try {
      const data = await getBoards();
      set({ boards: data || [] });
    } catch (error) {
      console.error('Failed to fetch boards:', error);
      toast.error('Failed to load projects');
    } finally {
      set({ isFetching: false });
    }
  },

  createNewBoard: async (name: string) => {
    if (!name.trim()) return;
    set({ isSubmitting: true });
    try {
      const newBoard = await createBoard(name);
      set({ boards: [...get().boards, newBoard] });
      toast.success('Project created successfully');
    } catch (error) {
      console.error('Failed to create board:', error);
      toast.error(error instanceof Error ? error.message : 'Failed to create project');
    } finally {
      set({ isSubmitting: false });
    }
  },

  removeBoard: async (boardId: number) => {
    try {
      await deleteBoard(boardId);
      set({ boards: get().boards.filter(b => b.id !== boardId) });
      toast.success('Project deleted');
    } catch (error) {
      console.error('Failed to delete board:', error);
      toast.error(error instanceof Error ? error.message : 'Failed to delete project');
    }
  }
}));
