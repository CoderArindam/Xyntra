import { type Task } from '../../../services/tasksApi';

export interface MyWorkSummaryData {
  assigned: number;
  due_today: number;
  overdue: number;
  completed_this_week: number;
}

export interface FilterParams {
  status: string;
  priority: string;
  due: string;
  search: string;
}

export const deriveMyWorkSummary = (tasks: Task[]): MyWorkSummaryData => {
  let assigned = 0;
  let due_today = 0;
  let overdue = 0;
  let completed_this_week = 0;

  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const startOfWeek = new Date(today);
  const day = startOfWeek.getDay();
  const diff = startOfWeek.getDate() - day + (day === 0 ? -6 : 1); // Monday as start of week
  startOfWeek.setDate(diff);

  tasks.forEach((t) => {
    // If it's a completed task
    if (t.column_type === 'DONE') {
      if (t.completed_at) {
        const completedAt = new Date(t.completed_at);
        if (completedAt >= startOfWeek) {
          completed_this_week++;
        }
      }
      return; // Skip active counts
    }

    // Active tasks
    assigned++;

    if (t.due_date) {
      const due = new Date(t.due_date);
      due.setHours(0, 0, 0, 0);

      if (due < today) {
        overdue++;
      } else if (due.getTime() === today.getTime()) {
        due_today++;
      }
    }
  });

  return {
    assigned,
    due_today,
    overdue,
    completed_this_week
  };
};

export const filterMyTasks = (tasks: Task[], params: FilterParams): Task[] => {
  return tasks.filter((t) => {
    // 1. Priority
    if (params.priority !== 'all' && t.priority !== params.priority) return false;

    // 2. Status
    if (params.status === 'all') {
      if (t.column_type === 'DONE') return false; // Hide from active tasks
    } else {
      if (params.status === 'done' && t.column_type !== 'DONE') return false;
      if (params.status === 'todo' && t.column_type !== 'TODO') return false;
      if (params.status === 'in_progress' && t.column_type !== 'IN_PROGRESS') return false;
    }

    // 3. Due Date
    if (params.due !== 'all') {
      if (params.due === 'none') {
        if (t.due_date) return false;
      } else {
        if (!t.due_date) return false;
        if (t.column_type === 'DONE') return false; // Usually due date filters ignore done tasks
        
        const due = new Date(t.due_date);
        due.setHours(0, 0, 0, 0);
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        
        if (params.due === 'overdue' && due >= today) return false;
        if (params.due === 'today' && due.getTime() !== today.getTime()) return false;
        
        if (params.due === 'week') {
          const nextWeek = new Date(today);
          nextWeek.setDate(today.getDate() + 7);
          if (due < today || due > nextWeek) return false;
        }
      }
    }

    // 4. Search
    if (params.search) {
      const lowerSearch = params.search.toLowerCase();
      if (!t.title?.toLowerCase().includes(lowerSearch) && !t.description?.toLowerCase().includes(lowerSearch)) {
        return false;
      }
    }

    return true;
  });
};

export const sortMyTasks = (tasks: Task[], sortParam: string): Task[] => {
  return [...tasks].sort((a, b) => {
    if (sortParam === 'due') {
      if (!a.due_date && !b.due_date) return 0;
      if (!a.due_date) return 1;
      if (!b.due_date) return -1;
      return new Date(a.due_date).getTime() - new Date(b.due_date).getTime();
    }
    if (sortParam === 'priority') {
      const p = { 'High': 1, 'Medium': 2, 'Low': 3 };
      return (p[a.priority as keyof typeof p] || 4) - (p[b.priority as keyof typeof p] || 4);
    }
    if (sortParam === 'alpha') {
      return (a.title || '').localeCompare(b.title || '');
    }
    // updated / created
    const tA = new Date(a.created_at || 0).getTime();
    const tB = new Date(b.created_at || 0).getTime();
    return tB - tA; // Descending
  });
};

export const groupMyTasks = (tasks: Task[], groupingParam: string): Record<string, Task[]> => {
  if (groupingParam === 'none') return { 'All Tasks': tasks };

  const groups: Record<string, Task[]> = {};

  tasks.forEach((t) => {
    let key = 'Other';
    if (groupingParam === 'board') key = t.board_name || 'No Board';
    else if (groupingParam === 'status') key = t.column_name || 'No Status';
    else if (groupingParam === 'priority') key = t.priority || 'No Priority';
    else if (groupingParam === 'due') {
      if (!t.due_date) key = 'No Due Date';
      else {
        const due = new Date(t.due_date);
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        due.setHours(0, 0, 0, 0);
        if (due < today) key = 'Overdue';
        else if (due.getTime() === today.getTime()) key = 'Today';
        else key = 'Upcoming';
      }
    }

    if (!groups[key]) groups[key] = [];
    groups[key].push(t);
  });

  return groups;
};

export const getCompletedThisWeekTasks = (tasks: Task[]): Task[] => {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const startOfWeek = new Date(today);
  const day = startOfWeek.getDay();
  const diff = startOfWeek.getDate() - day + (day === 0 ? -6 : 1);
  startOfWeek.setDate(diff);

  return tasks.filter(t => {
    if (t.column_type !== 'DONE' || !t.completed_at) return false;
    const completedAt = new Date(t.completed_at);
    return completedAt >= startOfWeek;
  }).sort((a, b) => new Date(b.completed_at!).getTime() - new Date(a.completed_at!).getTime());
};
