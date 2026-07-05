import React, { useEffect, useMemo, useCallback } from "react";
import { useSearchParams } from "react-router-dom";
import { useTaskStore } from "../store/taskStore";
import { useUiStore } from "../store/uiStore";
import MyWorkSummary from "../components/my-work/MyWorkSummary";
import MyWorkEmptyState from "../components/my-work/MyWorkEmptyState";
import MyWorkSkeleton from "../components/my-work/MyWorkSkeleton";
import MyWorkToolbar from "../components/my-work/MyWorkToolbar";
import TaskCard from "../components/TaskCard";
import TaskDetailsModal from "../components/modals/task-details";
import { useDebounce } from "../hooks/useDebounce";
import { usePageTitle } from "../hooks/usePageTitle";
import {
  deriveMyWorkSummary,
  filterMyTasks,
  sortMyTasks,
  groupMyTasks,
  getCompletedThisWeekTasks,
} from "../selectors/myWorkSelectors";

const MyWork: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const { loadMyTasks, getMyTasksList, myWorkView, entities } = useTaskStore();
  const myTasks = getMyTasksList();
  const isFetching = myWorkView.isFetching;
  const users = Object.values(entities.users);
  const { openTaskModal } = useUiStore();

  usePageTitle("My Work");

  // URL State
  const searchParam = searchParams.get("search") || "";
  const statusParam = searchParams.get("status") || "all";
  const priorityParam = searchParams.get("priority") || "all";
  const dueParam = searchParams.get("due") || "all";
  const sortParam = searchParams.get("sort") || "due";
  const groupingParam = searchParams.get("grouping") || "none";

  // Debounced search for API or client filtering
  const debouncedSearch = useDebounce(searchParam, 300);

  // Handlers for Toolbar
  const updateParam = useCallback(
    (key: string, value: string) => {
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev);
          if (value && value !== "all" && value !== "") {
            next.set(key, value);
          } else {
            next.delete(key);
          }
          return next;
        },
        { replace: true },
      );
    },
    [setSearchParams],
  );

  // Fetch all tasks once on mount
  useEffect(() => {
    loadMyTasks({ due: "all", sort: "due" });
  }, [loadMyTasks]);

  // Derived state
  const summary = useMemo(() => deriveMyWorkSummary(myTasks), [myTasks]);

  const filteredTasks = useMemo(() => {
    return filterMyTasks(myTasks, {
      status: statusParam,
      priority: priorityParam,
      due: dueParam,
      search: debouncedSearch,
    });
  }, [myTasks, priorityParam, statusParam, dueParam, debouncedSearch]);

  const sortedTasks = useMemo(() => {
    return sortMyTasks(filteredTasks, sortParam);
  }, [filteredTasks, sortParam]);

  const groupedTasks = useMemo(() => {
    return groupMyTasks(sortedTasks, groupingParam);
  }, [sortedTasks, groupingParam]);

  const completedThisWeekTasks = useMemo(() => {
    return getCompletedThisWeekTasks(myTasks);
  }, [myTasks]);

  const handleTaskOpen = useCallback(
    (taskId: number) => {
      openTaskModal(taskId);
    },
    [openTaskModal],
  );

  if (isFetching && myTasks.length === 0) {
    return <MyWorkSkeleton />;
  }

  return (
    <div className="flex-1 overflow-y-auto bg-brand-bg text-brand-text">
      <div className="max-w-5xl mx-auto py-10 px-8 flex flex-col gap-8">
        <header className="flex justify-between items-end">
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-brand-text mb-2">
              My Work
            </h1>
            <p className="text-brand-text-muted">
              Here's an overview of everything assigned to you.
            </p>
          </div>
        </header>

        <section>
          <MyWorkSummary
            summary={summary}
            activeFilter={dueParam}
            onFilterClick={(filter) => updateParam("due", filter)}
          />
        </section>

        <section className="flex flex-col gap-6">
          <MyWorkToolbar
            search={searchParam}
            setSearch={(val) => updateParam("search", val)}
            status={statusParam}
            setStatus={(val) => updateParam("status", val)}
            priority={priorityParam}
            setPriority={(val) => updateParam("priority", val)}
            due={dueParam}
            setDue={(val) => updateParam("due", val)}
            sort={sortParam}
            setSort={(val) => updateParam("sort", val)}
            grouping={groupingParam}
            setGrouping={(val) => updateParam("grouping", val)}
          />

          {filteredTasks.length === 0 ? (
            <MyWorkEmptyState />
          ) : (
            <div className="flex flex-col gap-8">
              {Object.entries(groupedTasks).map(([groupName, groupTasks]) => (
                <div key={groupName} className="flex flex-col gap-4">
                  {groupingParam !== "none" && (
                    <h2 className="text-lg font-semibold text-brand-text border-b border-brand-border pb-2">
                      {groupName}{" "}
                      <span className="text-sm font-normal text-brand-text-muted ml-2">
                        ({(groupTasks as any[]).length})
                      </span>
                    </h2>
                  )}
                  <div className="flex flex-col gap-3">
                    {(groupTasks as any[]).map((task) => (
                      <TaskCard
                        key={task.id}
                        task={task}
                        columns={[]} // Lazy loaded on open
                        users={users}
                        variant="list"
                        onStatusChange={() => {}}
                        onDelete={() => {}}
                        onAssigneeChange={() => {}}
                        onOpen={() => handleTaskOpen(task.id)}
                        canEdit={false}
                        canReassign={false}
                      />
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Completed This Week Section */}
          {completedThisWeekTasks.length > 0 && (
            <div className="mt-8 pt-8 border-t border-brand-border">
              <h2 className="text-xl font-semibold text-brand-text mb-6 flex items-center gap-2">
                Completed This Week
                <span className="bg-brand-surface border border-brand-border text-brand-text-muted text-xs px-2 py-0.5 rounded-full font-normal">
                  {completedThisWeekTasks.length}
                </span>
              </h2>
              <div className="flex flex-col gap-3 opacity-75">
                {completedThisWeekTasks.map((task) => (
                  <TaskCard
                    key={task.id}
                    task={task}
                    columns={[]}
                    users={users}
                    variant="list"
                    onStatusChange={() => {}}
                    onDelete={() => {}}
                    onAssigneeChange={() => {}}
                    onOpen={() => handleTaskOpen(task.id)}
                    canEdit={false}
                    canReassign={false}
                  />
                ))}
              </div>
            </div>
          )}
        </section>
      </div>
      <TaskDetailsModal />
    </div>
  );
};

export default MyWork;
