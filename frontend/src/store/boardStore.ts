import { useMemo } from 'react';
import { create } from 'zustand';
import { getBoards, createBoard, deleteBoard, type Board } from '../api/boardsApi';
import toast from 'react-hot-toast';

interface BoardState {
  boards: Board[];
  isFetching: boolean;
  isSubmitting: boolean;
  fetchBoards: () => Promise<void>;
  createNewBoard: (boardData: Partial<Board>) => Promise<Board | undefined>;
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

  createNewBoard: async (boardData: Partial<Board>) => {
    if (!boardData.name?.trim()) return;
    set({ isSubmitting: true });
    try {
      const newBoard = await createBoard(boardData);
      set({ boards: [...get().boards, newBoard] });
      toast.success('Project created successfully');
      return newBoard;
    } catch (error: any) {
      console.error('Failed to create board:', error);
      toast.error(error.response?.data?.detail || error.message || 'Failed to create project');
      throw error;
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

export const useActiveBoards = () => {
  const boards = useBoardStore(state => state.boards);
  return useMemo(() => boards.filter(b => !b.archived_at), [boards]);
};

export const useArchivedBoards = () => {
  const boards = useBoardStore(state => state.boards);
  return useMemo(() => boards.filter(b => b.archived_at), [boards]);
};
