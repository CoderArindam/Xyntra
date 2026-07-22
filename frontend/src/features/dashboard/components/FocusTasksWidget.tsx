import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { CheckCircle2, Circle, ListTodo, Loader2 } from 'lucide-react';
import { Card, CardHeader, CardTitle } from '../../../components/ui/Card';
import { getMyTasks, type MyTask } from '../../../services/myWorkApi';
import { updateTask } from '../../../services/tasksApi';

interface FocusTasksWidgetProps {
  pendingPropsCount: number;
  onOpenProposalsModal: () => void;
  summaryBoards?: any[];
}

export const FocusTasksWidget: React.FC<FocusTasksWidgetProps> = ({
  pendingPropsCount,
  onOpenProposalsModal,
}) => {
  const navigate = useNavigate();
  const [tasks, setTasks] = useState<MyTask[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const fetchUserTasks = useCallback(async () => {
    setIsLoading(true);
    try {
      const data = await getMyTasks({ limit: 5 });
      setTasks(data || []);
    } catch (err) {
      console.error('Failed to load user focus tasks:', err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchUserTasks();
  }, [fetchUserTasks]);

  // Toggle completion in real PostgreSQL database via API
  const handleToggleTask = async (task: MyTask) => {
    const nextCompletedState = !task.is_completed;

    // Optimistic UI update
    setTasks((prev) =>
      prev.map((t) => (t.id === task.id ? { ...t, is_completed: nextCompletedState } : t))
    );

    try {
      await updateTask(task.id, {
        column_id: task.column_id,
      });
    } catch (err) {
      console.error('Failed to update task status in DB:', err);
      // Revert on error
      setTasks((prev) =>
        prev.map((t) => (t.id === task.id ? { ...t, is_completed: !nextCompletedState } : t))
      );
    }
  };

  return (
    <Card variant="default" padding="md" className="space-y-4 shadow-sm">
      <CardHeader className="flex-row items-center justify-between mb-0 pb-1">
        <CardTitle className="text-base font-bold text-brand-text flex items-center gap-2">
          <ListTodo className="w-4 h-4 text-brand-primary" aria-hidden="true" />
          <span>Focus Tasks</span>
        </CardTitle>
      </CardHeader>

      {/* Real Task Item List */}
      {isLoading ? (
        <div className="py-4 flex justify-center text-brand-text-muted">
          <Loader2 className="w-5 h-5 animate-spin text-brand-primary opacity-60" />
        </div>
      ) : tasks.length === 0 ? (
        <div className="space-y-2">
          {/* Static proposal queue trigger item */}
          {pendingPropsCount > 0 && (
            <button
              onClick={onOpenProposalsModal}
              className="w-full text-left flex items-center gap-3 p-3 rounded-xl border bg-emerald-500/5 hover:bg-emerald-500/10 border-emerald-500/20 text-brand-text cursor-pointer transition-colors"
            >
              <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" />
              <span className="text-xs font-semibold text-emerald-600 dark:text-emerald-400 min-w-0 truncate">
                Review AI Task Proposals ({pendingPropsCount})
              </span>
            </button>
          )}

          <p className="text-xs text-brand-text-muted italic text-center py-2">
            No assigned focus tasks currently pending.
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {/* Review proposals quick action item if pending */}
          {pendingPropsCount > 0 && (
            <button
              onClick={onOpenProposalsModal}
              className="w-full text-left flex items-center gap-3 p-3 rounded-xl border bg-emerald-500/5 hover:bg-emerald-500/10 border-emerald-500/20 text-brand-text cursor-pointer transition-colors"
            >
              <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" />
              <span className="text-xs font-semibold text-emerald-600 dark:text-emerald-400 min-w-0 truncate">
                Review AI Task Proposals ({pendingPropsCount})
              </span>
            </button>
          )}

          {tasks.slice(0, 4).map((task) => (
            <button
              key={task.id}
              onClick={() => handleToggleTask(task)}
              className={`w-full text-left flex items-center gap-3 p-3 rounded-xl border transition-all cursor-pointer ${
                task.is_completed
                  ? 'bg-brand-primary/5 border-brand-primary/20 text-brand-text'
                  : 'bg-brand-surface-low/40 hover:bg-brand-surface-low border-brand-border/60 text-brand-text'
              }`}
            >
              {task.is_completed ? (
                <CheckCircle2 className="w-4 h-4 text-brand-primary shrink-0" />
              ) : (
                <Circle className="w-4 h-4 text-brand-text-muted shrink-0" />
              )}
              <div className="min-w-0 flex-1">
                <span
                  className={`text-xs font-medium block truncate ${
                    task.is_completed ? 'line-through text-brand-text-muted' : ''
                  }`}
                >
                  {task.title}
                </span>
                {task.board_name && (
                  <span className="text-[10px] text-brand-text-muted block truncate">
                    {task.board_name}
                  </span>
                )}
              </div>
            </button>
          ))}
        </div>
      )}

      {/* Bottom Action Button - Navigates to /my-work */}
      <div className="pt-2">
        <button
          onClick={() => navigate('/my-work')}
          className="w-full py-2.5 rounded-xl border border-brand-border/80 hover:bg-brand-surface-low text-brand-text font-semibold text-xs transition-colors shadow-2xs cursor-pointer text-center"
        >
          View Details
        </button>
      </div>
    </Card>
  );
};

export default FocusTasksWidget;
