import { useState, useCallback } from 'react';
import { getBoardTasks, type Task } from '../../../../services/tasksApi';

/** Manages a cache of tasks per board ID and loading state. */
export function useBoardTasks() {
  const [boardTasksMap, setBoardTasksMap] = useState<Record<string, Task[]>>({});
  const [loadingTasks, setLoadingTasks] = useState(false);

  const loadBoardTasks = useCallback(async (boardId: string) => {
    if (boardId === 'general' || boardTasksMap[boardId]) return;
    setLoadingTasks(true);
    try {
      const boardData = await getBoardTasks(boardId);
      setBoardTasksMap((prev) => ({ ...prev, [boardId]: boardData.tasks || [] }));
    } catch (err) {
      console.error('Failed to load board tasks:', err);
    } finally {
      setLoadingTasks(false);
    }
  }, [boardTasksMap]);

  return { boardTasksMap, loadingTasks, loadBoardTasks };
}
