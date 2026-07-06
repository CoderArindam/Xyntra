import React from 'react';
import TaskHeader from './TaskHeader';
import TaskDescription from './TaskDescription';
import TaskSidebar from './TaskSidebar';
import TaskTabs from './TaskTabs';
import { useTaskStore } from '../../../../store/taskStore';
import { useUiStore } from '../../../../store/uiStore';
import { useAuthStore } from '../../../../store/authStore';
import Modal from '../../../../components/common/Modal';

const TaskDetailsModal: React.FC = () => {
  const selectedTaskId = useUiStore((state: any) => state.selectedTaskId);
  const isOpen = useUiStore((state: any) => state.isTaskModalOpen);
  const closeTaskModal = useUiStore((state: any) => state.closeTaskModal);

  const { getColumnsList, getBoardMembersList, boardView, initializeBoard, getTaskById } = useTaskStore();
  const columns = getColumnsList();
  const boardMembers = getBoardMembersList();

  const boardId = boardView.boardId;
  const { user } = useAuthStore();

  const task = getTaskById(selectedTaskId || 0);

  React.useEffect(() => {
    if (isOpen && task && task.board_id !== boardId) {
      // Lazy load board data if we opened a task from a different context (like My Work)
      initializeBoard(task.board_id);
    }
  }, [isOpen, task?.board_id, boardId, initializeBoard]);

  if (!isOpen || !task) return null;

  const canEdit = user?.role !== "MEMBER" || task.assigned_to === user?.id;
  const createdDate = new Date(task.created_at).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });

  return (
    <Modal isOpen={isOpen} onClose={closeTaskModal} width="max-w-6xl" noPadding={true}>
      <div className="flex flex-col h-[90vh]">
        <TaskHeader task={task} onClose={closeTaskModal} canEdit={canEdit} />

        <div className="flex flex-1 overflow-hidden">
          <div className="flex-1 p-8 overflow-y-auto space-y-8">
            <TaskDescription task={task} canEdit={canEdit} />
            <TaskTabs
              task={task}
              currentUserId={user?.id || null}
              users={boardMembers}
            />
          </div>

          <TaskSidebar
            task={task}
            columns={columns}
            boardMembers={boardMembers}
            canEdit={canEdit}
            createdDate={createdDate}
          />
        </div>
      </div>
    </Modal>
  );
};

export default TaskDetailsModal;
