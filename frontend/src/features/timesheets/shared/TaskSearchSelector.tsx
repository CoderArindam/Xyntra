import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Search, Loader2, Check, X, Tag, UserCheck } from 'lucide-react';
import { searchTasks, type Task } from '../../../services/tasksApi';

interface TaskSearchSelectorProps {
  value?: string;
  onChange: (taskId: string, taskTitle?: string, boardId?: string) => void;
  boardId?: string;
  assignedToMe?: boolean;
  placeholder?: string;
  disabled?: boolean;
  className?: string;
}

export const TaskSearchSelector: React.FC<TaskSearchSelectorProps> = ({
  value,
  onChange,
  boardId,
  assignedToMe = true,
  placeholder = 'Search assigned tasks by title, ID (#PAY-12), or board...',
  disabled = false,
  className = '',
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);

  const containerRef = useRef<HTMLDivElement>(null);
  const debounceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Close dropdown on click outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const fetchTasks = useCallback(
    async (searchQuery: string, pageNum: number = 1, append: boolean = false) => {
      setLoading(true);
      try {
        const res = await searchTasks({
          query: searchQuery,
          board_id: boardId && boardId !== 'general' ? boardId : undefined,
          assigned_to_me: assignedToMe,
          page: pageNum,
          limit: 20,
        });

        if (append) {
          setTasks((prev) => [...prev, ...res.items]);
        } else {
          setTasks(res.items);
        }

        setHasMore(pageNum * 20 < res.total);

        // Find selected task detail if value is set
        if (value) {
          const match = res.items.find((t) => String(t.id) === String(value));
          if (match) setSelectedTask(match);
        }
      } catch (err) {
        console.error('Failed to search tasks:', err);
      } finally {
        setLoading(false);
      }
    },
    [boardId, assignedToMe, value]
  );

  // Trigger search on query / boardId / assignedToMe change with debounce
  useEffect(() => {
    if (debounceTimerRef.current) clearTimeout(debounceTimerRef.current);

    debounceTimerRef.current = setTimeout(() => {
      setPage(1);
      fetchTasks(query, 1, false);
    }, 300);

    return () => {
      if (debounceTimerRef.current) clearTimeout(debounceTimerRef.current);
    };
  }, [query, boardId, assignedToMe, fetchTasks]);

  const handleSelect = (task: Task) => {
    setSelectedTask(task);
    onChange(String(task.id), task.title, String(task.board_id));
    setIsOpen(false);
  };

  const handleClear = (e: React.MouseEvent) => {
    e.stopPropagation();
    setSelectedTask(null);
    setQuery('');
    onChange('', undefined, undefined);
  };

  const handleLoadMore = () => {
    const nextPage = page + 1;
    setPage(nextPage);
    fetchTasks(query, nextPage, true);
  };

  const priorityColors: Record<string, string> = {
    High: 'bg-red-500/10 text-red-400 border-red-500/20',
    Medium: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
    Low: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
    Urgent: 'bg-rose-600/20 text-rose-300 border-rose-500/30 font-semibold',
  };

  return (
    <div className={`relative w-full ${className}`} ref={containerRef}>
      {/* Search Input Control */}
      <div
        onClick={() => !disabled && setIsOpen((prev) => !prev)}
        className={`flex items-center gap-2 px-3 py-2.5 rounded-lg border bg-brand-surface text-brand-text text-sm transition-all cursor-pointer ${
          isOpen ? 'border-brand-primary ring-2 ring-brand-primary/20' : 'border-brand-border hover:border-brand-border-highlight'
        } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
      >
        <Search size={16} className="text-brand-text-muted shrink-0" />

        {selectedTask ? (
          <div className="flex items-center gap-2 flex-1 min-w-0">
            <span className="px-1.5 py-0.5 text-xs font-semibold font-mono bg-brand-primary/10 text-brand-primary border border-brand-primary/20 rounded">
              #{selectedTask.task_reference || selectedTask.id}
            </span>
            <span className="truncate font-medium text-brand-text">{selectedTask.title}</span>
            <span className="text-xs text-brand-text-muted truncate hidden sm:inline">({selectedTask.board_name})</span>
          </div>
        ) : (
          <input
            type="text"
            className="w-full bg-transparent border-none outline-none text-sm text-brand-text placeholder:text-brand-text-muted cursor-text"
            placeholder={placeholder}
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setIsOpen(true);
            }}
            onClick={(e) => e.stopPropagation()}
            disabled={disabled}
          />
        )}

        {loading && <Loader2 size={16} className="animate-spin text-brand-primary shrink-0" />}

        {selectedTask && !disabled && (
          <button
            type="button"
            onClick={handleClear}
            className="p-1 text-brand-text-muted hover:text-brand-text hover:bg-brand-surface-highlight rounded transition-colors"
          >
            <X size={14} />
          </button>
        )}
      </div>

      {/* Helper text badge */}
      {assignedToMe && (
        <div className="flex items-center gap-1 mt-1 text-[11px] text-brand-text-muted">
          <UserCheck size={12} className="text-emerald-400" />
          <span>Only showing tasks assigned to you</span>
        </div>
      )}

      {/* Dropdown Menu */}
      {isOpen && !disabled && (
        <div className="absolute z-50 left-0 right-0 mt-1 max-h-72 overflow-y-auto rounded-lg border border-brand-border bg-brand-surface text-brand-text shadow-2xl p-1.5 flex flex-col gap-1 opacity-100">
          {/* Inner Search Box when task is selected */}
          {selectedTask && (
            <div className="p-1.5 border-b border-brand-border/60">
              <input
                type="text"
                className="w-full px-2.5 py-1.5 bg-brand-surface border border-brand-border rounded text-xs text-brand-text placeholder:text-brand-text-muted outline-none focus:border-brand-primary"
                placeholder="Search assigned tasks..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                autoFocus
              />
            </div>
          )}

          {tasks.length === 0 ? (
            <div className="p-4 text-center text-xs text-brand-text-muted">
              {loading ? (
                <div className="flex items-center justify-center gap-2">
                  <Loader2 size={14} className="animate-spin text-brand-primary" />
                  <span>Searching tasks...</span>
                </div>
              ) : (
                'No assigned tasks found.'
              )}
            </div>
          ) : (
            tasks.map((task) => {
              const isSelected = String(task.id) === String(value);
              const pColor = priorityColors[task.priority || 'Medium'] || priorityColors.Medium;

              return (
                <div
                  key={task.id}
                  onClick={() => handleSelect(task)}
                  className={`flex flex-col gap-1 p-2 rounded-md cursor-pointer text-xs transition-colors ${
                    isSelected
                      ? 'bg-brand-primary/10 border border-brand-primary/30 text-brand-text'
                      : 'hover:bg-brand-surface-highlight text-brand-text'
                  }`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-1.5 min-w-0">
                      <span className="px-1.5 py-0.5 font-mono text-[10px] font-semibold bg-brand-surface text-brand-primary border border-brand-primary/20 rounded shrink-0">
                        #{task.task_reference || task.id}
                      </span>
                      <span className="font-medium text-brand-text truncate">{task.title}</span>
                    </div>

                    {isSelected && <Check size={14} className="text-brand-primary shrink-0" />}
                  </div>

                  <div className="flex items-center justify-between gap-2 text-[11px] text-brand-text-muted mt-0.5">
                    <span className="truncate flex items-center gap-1">
                      <Tag size={10} />
                      {task.board_name}
                    </span>

                    <div className="flex items-center gap-1.5 shrink-0">
                      {task.priority && (
                        <span className={`px-1.5 py-0.2 border rounded text-[10px] ${pColor}`}>
                          {task.priority}
                        </span>
                      )}
                      <span className="px-1.5 py-0.2 bg-brand-surface border border-brand-border rounded text-[10px] capitalize">
                        {task.column_name || task.column_type}
                      </span>
                    </div>
                  </div>
                </div>
              );
            })
          )}

          {hasMore && (
            <button
              type="button"
              onClick={handleLoadMore}
              disabled={loading}
              className="w-full py-1.5 text-center text-xs text-brand-primary hover:bg-brand-primary/10 rounded transition-colors font-medium"
            >
              {loading ? 'Loading...' : 'Load more tasks'}
            </button>
          )}
        </div>
      )}
    </div>
  );
};
