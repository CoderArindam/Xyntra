import { create } from 'zustand';
import { getBoardTasks, createTask, updateTaskStatus, deleteTask, updateTaskAssignee, updateTask, type Task, type Column } from '../api/tasksApi';
import { useActivityStore } from './activityStore';
import { getUsers, getBoardMembers, type User, type BoardMember } from '../api/usersApi';
import toast from 'react-hot-toast';

interface TaskState {
  // --- ENTITIES ---
  entities: {
    tasks: Record<number, Task>;
    columns: Record<number, Column>;
    users: Record<number, User>;
    boardMembers: Record<number, BoardMember>;
  };

  // --- VIEWS ---
  boardView: {
    boardId: number | null;
    taskIds: number[];
    columnIds: number[];
    selectedAssigneeId: number | null;
    isFetching: boolean;
  };

  myWorkView: {
    taskIds: number[];
    isFetching: boolean;
  };

  isSubmitting: boolean;

  // --- SELECTORS ---
  getTaskById: (taskId: number) => Task | undefined;
  getBoardTasksList: () => Task[];
  getMyTasksList: () => Task[];
  getColumnsList: () => Column[];
  getBoardMembersList: () => BoardMember[];

  // --- ACTIONS ---
  setSelectedAssigneeId: (boardId: number, val: number | null) => void;
  initializeBoard: (boardId: number) => Promise<void>;
  loadMyTasks: (params?: any) => Promise<void>;
  
  createNewTask: (taskData: Partial<Task>) => Promise<void>;
  moveTask: (taskId: number, newColumnId: number) => Promise<void>;
  removeTask: (taskId: number) => Promise<void>;
  assignTask: (taskId: number, assigneeId: number | null) => Promise<void>;
  updateTaskData: (taskId: number, data: Partial<Task>) => Promise<void>;

  // Internal helpers
  _updateTaskEntity: (taskId: number, updater: (task: Task) => Partial<Task>) => void;
}

export const useTaskStore = create<TaskState>((set, get) => ({
  entities: {
    tasks: {},
    columns: {},
    users: {},
    boardMembers: {}
  },
  
  boardView: {
    boardId: null,
    taskIds: [],
    columnIds: [],
    selectedAssigneeId: null,
    isFetching: true,
  },

  myWorkView: {
    taskIds: [],
    isFetching: false,
  },

  isSubmitting: false,

  // --- SELECTORS ---
  getTaskById: (taskId) => get().entities.tasks[taskId],
  getBoardTasksList: () => {
    const { entities, boardView } = get();
    return boardView.taskIds.map(id => entities.tasks[id]).filter(Boolean);
  },
  getMyTasksList: () => {
    const { entities, myWorkView } = get();
    return myWorkView.taskIds.map(id => entities.tasks[id]).filter(Boolean);
  },
  getColumnsList: () => {
    const { entities, boardView } = get();
    return boardView.columnIds.map(id => entities.columns[id]).filter(Boolean).sort((a, b) => a.position - b.position);
  },
  getBoardMembersList: () => {
    return Object.values(get().entities.boardMembers);
  },

  // --- INTERNAL HELPERS ---
  _updateTaskEntity: (taskId, updater) => {
    set((state) => {
      const currentTask = state.entities.tasks[taskId];
      if (!currentTask) return state;

      const updates = updater(currentTask);
      const updatedTask = { ...currentTask, ...updates };

      // Re-calculate derived fields
      if (updatedTask.column_id) {
        const targetColumn = state.entities.columns[updatedTask.column_id];
        if (targetColumn) {
          updatedTask.column_name = targetColumn.name;
          updatedTask.column_type = targetColumn.column_type;
          updatedTask.is_completed = targetColumn.column_type === 'DONE';
          
          if (targetColumn.column_type === 'DONE' && !updatedTask.completed_at) {
            updatedTask.completed_at = new Date().toISOString();
          } else if (targetColumn.column_type !== 'DONE') {
            updatedTask.completed_at = null;
          }
        }
      }

      return {
        ...state,
        entities: {
          ...state.entities,
          tasks: {
            ...state.entities.tasks,
            [taskId]: updatedTask
          }
        }
      };
    });
  },

  // --- ACTIONS ---
  setSelectedAssigneeId: (boardId, val) => {
    set((state) => ({
      boardView: { ...state.boardView, selectedAssigneeId: val }
    }));
    localStorage.setItem(`kanban_selected_assignee_${boardId}`, JSON.stringify(val));
  },

  initializeBoard: async (boardId) => {
    set((state) => ({ boardView: { ...state.boardView, boardId, isFetching: true } }));
    
    const saved = localStorage.getItem(`kanban_selected_assignee_${boardId}`);
    let initialAssigneeId = null;
    if (saved !== null) {
      try {
        const parsed = JSON.parse(saved);
        initialAssigneeId = typeof parsed === 'number' ? parsed : null;
      } catch {
        // ignore
      }
    }

    try {
      const [boardData, usersList, membersList] = await Promise.all([
        getBoardTasks(boardId),
        getUsers(),
        getBoardMembers(boardId)
      ]);
      
      const fetchedTasks = boardData.tasks || [];
      const fetchedColumns = boardData.columns || [];

      set((state) => {
        const newTasks = { ...state.entities.tasks };
        const newColumns = { ...state.entities.columns };
        const newUsers = { ...state.entities.users };
        const newMembers: Record<number, BoardMember> = {};

        fetchedTasks.forEach(t => { newTasks[t.id] = t; });
        fetchedColumns.forEach(c => { newColumns[c.id] = c; });
        usersList.forEach(u => { newUsers[u.id] = u; });
        membersList.forEach(m => { newMembers[m.id] = m; });

        return {
          entities: {
            tasks: newTasks,
            columns: newColumns,
            users: newUsers,
            boardMembers: newMembers
          },
          boardView: {
            boardId,
            taskIds: fetchedTasks.map(t => t.id),
            columnIds: fetchedColumns.map(c => c.id),
            selectedAssigneeId: initialAssigneeId,
            isFetching: false
          }
        };
      });
    } catch (error) {
      console.error('Failed to initialize board data', error);
      toast.error('Failed to load board data');
      set((state) => ({ boardView: { ...state.boardView, isFetching: false } }));
    }
  },

  loadMyTasks: async (params) => {
    set((state) => ({ myWorkView: { ...state.myWorkView, isFetching: true } }));
    try {
      const { getMyTasks } = await import('../api/myWorkApi');
      const myTasksList = await getMyTasks(params);
      
      set((state) => {
        const newTasks = { ...state.entities.tasks };
        myTasksList.forEach(t => { newTasks[t.id] = t; });

        return {
          entities: { ...state.entities, tasks: newTasks },
          myWorkView: {
            taskIds: myTasksList.map(t => t.id),
            isFetching: false
          }
        };
      });
    } catch (error) {
      console.error('Failed to load my tasks', error);
      toast.error('Failed to load your tasks');
      set((state) => ({ myWorkView: { ...state.myWorkView, isFetching: false } }));
    }
  },

  createNewTask: async (taskData) => {
    const { boardView } = get();
    if (!boardView.boardId || !taskData.title?.trim() || boardView.columnIds.length === 0) return;
    
    set({ isSubmitting: true });
    try {
      const createdTask = await createTask({
        board_id: boardView.boardId,
        column_id: taskData.column_id || boardView.columnIds[0],
        title: taskData.title,
        description: taskData.description,
        priority: taskData.priority,
        due_date: taskData.due_date,
        assigned_to: taskData.assigned_to,
      });
      
      set((state) => ({
        entities: {
          ...state.entities,
          tasks: { ...state.entities.tasks, [createdTask.id]: createdTask }
        },
        boardView: {
          ...state.boardView,
          taskIds: [...state.boardView.taskIds, createdTask.id]
        }
      }));
      toast.success("Task created");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to create task");
    } finally {
      set({ isSubmitting: false });
    }
  },

  moveTask: async (taskId, newColumnId) => {
    const prevTask = get().getTaskById(taskId);
    if (!prevTask) return;

    // Optimistic update
    get()._updateTaskEntity(taskId, () => ({ column_id: newColumnId }));
    
    try {
      useActivityStore.getState().appendActivity(taskId, {
        entity_type: 'TASK', entity_id: taskId, activity_type: 'STATUS_CHANGED',
        old_value: { column_id: prevTask.column_id }, new_value: { column_id: newColumnId }, metadata: {}
      });

      const updatedTask = await updateTaskStatus(taskId, newColumnId);
      get()._updateTaskEntity(taskId, () => updatedTask);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to move task");
      get()._updateTaskEntity(taskId, () => prevTask); // rollback
    }
  },

  removeTask: async (taskId) => {
    const prevTask = get().getTaskById(taskId);
    if (!prevTask) return;

    // Optimistically remove
    set((state) => {
      const newTasks = { ...state.entities.tasks };
      delete newTasks[taskId];
      return {
        entities: { ...state.entities, tasks: newTasks },
        boardView: { ...state.boardView, taskIds: state.boardView.taskIds.filter(id => id !== taskId) },
        myWorkView: { ...state.myWorkView, taskIds: state.myWorkView.taskIds.filter(id => id !== taskId) }
      };
    });

    try {
      await deleteTask(taskId);
      toast.success("Task deleted");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to delete task");
      // Rollback
      set((state) => ({
        entities: { ...state.entities, tasks: { ...state.entities.tasks, [taskId]: prevTask } },
        boardView: { ...state.boardView, taskIds: [...state.boardView.taskIds, taskId] } // Simplistic rollback
      }));
    }
  },

  assignTask: async (taskId, assigneeId) => {
    const prevTask = get().getTaskById(taskId);
    if (!prevTask) return;

    get()._updateTaskEntity(taskId, () => ({ assigned_to: assigneeId || undefined }));

    try {
      const updatedTask = await updateTaskAssignee(taskId, assigneeId);
      get()._updateTaskEntity(taskId, () => updatedTask);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to update assignee");
      get()._updateTaskEntity(taskId, () => prevTask); // rollback
    }
  },

  updateTaskData: async (taskId, data) => {
    const prevTask = get().getTaskById(taskId);
    if (!prevTask) return;

    get()._updateTaskEntity(taskId, () => data);
    
    try {
      const updatedTask = await updateTask(taskId, data);
      get()._updateTaskEntity(taskId, () => updatedTask);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to update task");
      get()._updateTaskEntity(taskId, () => prevTask); // rollback
    }
  },
}));
