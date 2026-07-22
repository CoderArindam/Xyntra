import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Loader2, Plus, UserPlus } from 'lucide-react';
import {
  DndContext,
  DragOverlay,
  PointerSensor,
  useSensor,
  useSensors,
  type DragStartEvent,
  type DragEndEvent,
  type DragOverEvent,
} from '@dnd-kit/core';
import { useDroppable, useDraggable } from '@dnd-kit/core';
import { useTaskStore } from '../../../store/taskStore';
import { useUiStore } from '../../../store/uiStore';
import { useAuthStore } from '../../../store/authStore';
import { isManagerOrAdmin } from '../../../lib/rbac';
import TaskCard from './TaskCard';
import TaskDetailsModal from '../modals/task-details';
import CreateTaskModal from '../modals/CreateTaskModal';
import AddMemberModal from '../modals/AddMemberModal';
import AssigneeFilter from './AssigneeFilter';
import DueDateFilter, { type DueDateFilterOption } from './DueDateFilter';
import { type Column, type Task } from '../../../services/tasksApi';
import { type User } from '../../../services/usersApi';
import ConfirmDialog from '../../../components/common/ConfirmDialog';

interface KanbanBoardProps {
  boardId: number;
}

// Droppable column wrapper
function DroppableColumn({
  column,
  children,
}: {
  column: Column;
  children: React.ReactNode;
}) {
  const { setNodeRef, isOver } = useDroppable({ id: `col-${column.id}` });
  return (
    <div
      ref={setNodeRef}
      className={`flex-1 overflow-y-auto space-y-4 min-h-[200px] rounded-2xl transition-colors ${isOver ? "bg-brand-surface-container" : ""}`}
    >
      {children}
    </div>
  );
}

// Draggable task wrapper
function DraggableTask({
  task,
  columns,
  users,
  onStatusChange,
  onDelete,
  onAssigneeChange,
  onOpen,
  canEdit,
  canReassign,
}: {
  task: Task;
  columns: Column[];
  users: User[];
  onStatusChange: (columnId: number) => void;
  onDelete: () => void;
  onAssigneeChange: (assignedTo: number | null) => void;
  onOpen: () => void;
  canEdit: boolean;
  canReassign: boolean;
}) {
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({
    id: `task-${task.id}`,
    data: { task },
    disabled: !canEdit,
  });

  return (
    <div
      ref={setNodeRef}
      style={{ opacity: isDragging ? 0.4 : 1 }}
      {...listeners}
      {...attributes}
    >
      <TaskCard
        task={task}
        columns={columns}
        users={users}
        onStatusChange={onStatusChange}
        onDelete={onDelete}
        onAssigneeChange={onAssigneeChange}
        onOpen={onOpen}
        canEdit={canEdit}
        canReassign={canReassign}
      />
    </div>
  );
}

export const KanbanBoard: React.FC<KanbanBoardProps> = ({ boardId }) => {
  const {
    getColumnsList,
    getBoardTasksList,
    getBoardMembersList,
    boardView,
    moveTask,
    removeTask,
    assignTask,
    setSelectedAssigneeId,
    initializeBoard,
  } = useTaskStore();

  const columns = getColumnsList();
  const tasks = getBoardTasksList();
  const boardMembers = getBoardMembersList();
  const { isFetching, selectedAssigneeId } = boardView;

  const { openTaskModal, openCreateTaskModal } = useUiStore();
  const { user } = useAuthStore();

  const [activeTask, setActiveTask] = useState<Task | null>(null);
  const [selectedDueDateFilter, setSelectedDueDateFilter] =
    useState<DueDateFilterOption>("All");
  const [taskToDelete, setTaskToDelete] = useState<number | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [isAddMemberModalOpen, setIsAddMemberModalOpen] = useState(false);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
  );

  const [searchParams] = useSearchParams();

  useEffect(() => {
    initializeBoard(boardId);
  }, [boardId, initializeBoard]);

  useEffect(() => {
    const taskIdParam = searchParams.get('taskId');
    if (taskIdParam && !isFetching) {
      const taskIdNum = parseInt(taskIdParam, 10);
      if (!isNaN(taskIdNum)) {
        openTaskModal(taskIdNum);
      }
    }
  }, [searchParams, isFetching, openTaskModal]);

  const handleDeleteTask = (taskId: number) => {
    setTaskToDelete(taskId);
  };

  const handleConfirmDeleteTask = async () => {
    if (taskToDelete === null) return;
    setIsDeleting(true);
    await removeTask(taskToDelete);
    setIsDeleting(false);
    setTaskToDelete(null);
  };

  // DnD handlers
  const handleDragStart = (event: DragStartEvent) => {
    const task = event.active.data.current?.task as Task;
    setActiveTask(task ?? null);
  };

  const handleDragOver = (event: DragOverEvent) => {
    const { over, active } = event;
    if (!over) return;

    const task = active.data.current?.task as Task;
    if (!task) return;

    const overId = String(over.id);
    let targetColumnId: number | null = null;

    if (overId.startsWith("col-")) {
      targetColumnId = parseInt(overId.replace("col-", ""), 10);
    } else if (overId.startsWith("task-")) {
      const overTaskId = parseInt(overId.replace("task-", ""), 10);
      const overTask = tasks.find((t: any) => t.id === overTaskId);
      if (overTask) targetColumnId = overTask.column_id;
    }

    if (targetColumnId !== null && task.column_id !== targetColumnId) {
      task.column_id = targetColumnId;
    }
  };

  const handleDragEnd = async (event: DragEndEvent) => {
    const { over, active } = event;
    setActiveTask(null);

    if (!over) return;

    const task = active.data.current?.task as Task;
    if (!task) return;

    let targetColumnId: number | null = null;
    const overId = String(over.id);
    if (overId.startsWith("col-")) {
      targetColumnId = parseInt(overId.replace("col-", ""), 10);
    } else if (overId.startsWith("task-")) {
      const overTaskId = parseInt(overId.replace("task-", ""), 10);
      const overTask = tasks.find((t: any) => t.id === overTaskId);
      if (overTask) targetColumnId = overTask.column_id;
    }

    if (targetColumnId === null) return;
    if (task.column_id === targetColumnId) return;

    await moveTask(task.id, targetColumnId);
  };

  const isManager = isManagerOrAdmin(user);

  return (
    <DndContext
      sensors={sensors}
      onDragStart={handleDragStart}
      onDragOver={handleDragOver}
      onDragEnd={handleDragEnd}
    >
      <div className="h-full flex flex-col overflow-hidden bg-brand-bg relative">
        <header className="h-20 flex items-center justify-between px-4 md:px-8 shrink-0">
          <h1 className="text-2xl md:text-3xl font-bold text-brand-text">
            Kanban
          </h1>

          <div className="flex gap-3 items-center">
            {isManager && (
              <button
                onClick={() => setIsAddMemberModalOpen(true)}
                className="bg-brand-primary hover:bg-brand-primary-hover text-white px-4 py-2 rounded-full text-xs font-semibold flex items-center gap-1.5 transition-all shadow-xs cursor-pointer focus:ring-2 focus:ring-brand-primary focus:outline-none"
              >
                <UserPlus className="w-4 h-4" /> Add Member
              </button>
            )}
          </div>
        </header>

        {/* Filters */}
        <div className="px-4 md:px-8 flex flex-wrap gap-4">
          <AssigneeFilter
            users={boardMembers}
            selectedAssigneeId={selectedAssigneeId}
            onChange={(val) => setSelectedAssigneeId(boardId, val)}
          />
          <DueDateFilter
            value={selectedDueDateFilter}
            onChange={setSelectedDueDateFilter}
          />
        </div>

        {/* Board columns */}
        <div className="flex-1 overflow-x-auto overflow-y-hidden px-4 md:px-8 pb-40 pt-4">
          {isFetching ? (
            <div className="h-full flex flex-col items-center justify-center text-brand-text-muted">
              <Loader2 className="w-10 h-10 animate-spin text-brand-primary opacity-50 mb-4" />
              <p>Loading board...</p>
            </div>
          ) : (
            <div className="flex gap-6 h-full">
              {columns.map((column: any) => {
                let columnTasks = tasks.filter((task: any) => {
                  if (task.column_id !== column.id) return false;
                  if (
                    selectedAssigneeId !== null &&
                    task.assigned_to !== selectedAssigneeId
                  )
                    return false;

                  if (selectedDueDateFilter !== "All") {
                    if (selectedDueDateFilter === "No Due Date")
                      return !task.due_date;
                    if (!task.due_date) return false;

                    const due = new Date(task.due_date);
                    due.setHours(0, 0, 0, 0);
                    const now = new Date();
                    now.setHours(0, 0, 0, 0);
                    const diffDays = Math.round(
                      (due.getTime() - now.getTime()) / (1000 * 3600 * 24),
                    );

                    if (selectedDueDateFilter === "Overdue")
                      return diffDays < 0 && !column.is_completed;
                    if (selectedDueDateFilter === "Today")
                      return diffDays === 0;
                    if (selectedDueDateFilter === "This Week")
                      return diffDays >= 0 && diffDays <= 7;
                  }

                  return true;
                });

                columnTasks.sort((a: any, b: any) => {
                  const getUrgency = (t: any) => {
                    if (column.is_completed) return 100;
                    if (!t.due_date) return 50;
                    const due = new Date(t.due_date);
                    due.setHours(0, 0, 0, 0);
                    const now = new Date();
                    now.setHours(0, 0, 0, 0);
                    const diffDays = Math.round(
                      (due.getTime() - now.getTime()) / (1000 * 3600 * 24),
                    );
                    if (diffDays < 0) return 1; // Overdue
                    if (diffDays === 0) return 2; // Today
                    if (diffDays === 1) return 3; // Tomorrow
                    return 4 + diffDays; // Future
                  };
                  const scoreA = getUrgency(a);
                  const scoreB = getUrgency(b);
                  if (scoreA !== scoreB) return scoreA - scoreB;
                  return a.id - b.id;
                });

                return (
                  <div
                    key={column.id}
                    className="w-[340px] shrink-0 flex flex-col"
                  >
                    <div className="flex justify-between items-center px-4 py-3 bg-brand-surface rounded-2xl border border-brand-border mb-4">
                      <div className="flex items-center gap-3">
                        <div className="w-3 h-3 rounded-full bg-brand-primary" />
                        <h3 className="font-semibold text-brand-text">
                          {column.name}
                        </h3>
                      </div>
                      <span className="px-3 py-1 rounded-full bg-brand-surface-low text-xs">
                        {columnTasks.length}
                      </span>
                    </div>

                    <DroppableColumn column={column}>
                      {columnTasks.length === 0 ? (
                        <div className="h-[200px] flex flex-col items-center justify-center text-brand-text-muted border-2 border-dashed border-brand-border rounded-xl bg-brand-surface-low opacity-60">
                          <p className="text-sm">No tasks</p>
                        </div>
                      ) : (
                        columnTasks.map((task: any) => {
                          const canEdit =
                            user?.role !== "MEMBER" ||
                            task.assigned_to === user?.id;
                          const canReassign = canEdit;
                          return (
                            <DraggableTask
                              key={task.id}
                              task={task}
                              columns={columns}
                              users={boardMembers}
                              onStatusChange={(newColumnId) =>
                                moveTask(task.id, newColumnId)
                              }
                              onDelete={() => handleDeleteTask(task.id)}
                              onAssigneeChange={(assignedTo) =>
                                assignTask(task.id, assignedTo)
                              }
                              onOpen={() => openTaskModal(task.id)}
                              canEdit={canEdit}
                              canReassign={canReassign}
                            />
                          );
                        })
                      )}
                    </DroppableColumn>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Floating Create Bar */}
        {user?.role !== "MEMBER" && (
          <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-40">
            <button
              onClick={openCreateTaskModal}
              className="bg-brand-primary hover:bg-brand-primary-hover text-white shadow-xl shadow-brand-primary/20 px-6 py-3 rounded-full font-medium flex items-center gap-2 transition cursor-pointer"
            >
              <Plus size={18} />
              Create Task
            </button>
          </div>
        )}
      </div>

      {/* Drag overlay */}
      <DragOverlay>
        {activeTask && (
          <div style={{ opacity: 0.9, cursor: "grabbing" }}>
            <TaskCard
              task={activeTask}
              columns={columns}
              users={boardMembers}
              onStatusChange={() => {}}
              onDelete={() => {}}
              onAssigneeChange={() => {}}
              onOpen={() => {}}
              canEdit={
                user?.role !== "MEMBER" || activeTask.assigned_to === user?.id
              }
              canReassign={
                user?.role !== "MEMBER" || activeTask.assigned_to === user?.id
              }
            />
          </div>
        )}
      </DragOverlay>

      <TaskDetailsModal />
      <CreateTaskModal />
      <AddMemberModal
        isOpen={isAddMemberModalOpen}
        onClose={() => setIsAddMemberModalOpen(false)}
        boardId={boardId}
        onMemberAdded={() => initializeBoard(boardId)}
      />

      <ConfirmDialog
        isOpen={taskToDelete !== null}
        onClose={() => setTaskToDelete(null)}
        onConfirm={handleConfirmDeleteTask}
        title="Delete Task"
        description="Are you sure you want to delete this task? This action cannot be undone."
        confirmText="Delete"
        isDestructive={true}
        isLoading={isDeleting}
      />
    </DndContext>
  );
};

export default KanbanBoard;
