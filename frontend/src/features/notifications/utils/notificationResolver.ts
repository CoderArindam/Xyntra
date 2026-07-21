import type { Notification } from '../../../services/notificationsApi';

export type NotificationDestination = 
  | { type: 'TASK'; taskId: number; boardId?: number; commentId?: number }
  | { type: 'BOARD'; boardId: number }
  | { type: 'MEETING_PROPOSALS'; sessionId: string | number }
  | { type: 'NAVIGATE'; path: string }
  | { type: 'UNKNOWN' };

export const resolveNotificationDestination = (notification: Notification): NotificationDestination => {
  const entityType = (notification.activity_entity_type || '').toUpperCase();
  const activityType = (notification.activity_type || '').toUpperCase();
  const entityId = notification.activity_entity_id;
  const targetBoardId = notification.activity_target_board_id;

  // 1. Comment Notifications
  if (
    entityType === 'COMMENT' ||
    activityType === 'COMMENT_ADDED' ||
    activityType === 'COMMENT_DELETED' ||
    activityType === 'MENTION'
  ) {
    return {
      type: 'TASK',
      taskId: entityId,
      boardId: targetBoardId || undefined,
      commentId: notification.activity_id
    };
  }

  // 2. Task Notifications
  if (
    entityType === 'TASK' ||
    [
      'TASK_CREATED',
      'STATUS_CHANGED',
      'TITLE_CHANGED',
      'DESCRIPTION_CHANGED',
      'PRIORITY_CHANGED',
      'DUE_DATE_CHANGED',
      'ASSIGNEE_CHANGED',
      'TASK_ASSIGNED',
      'ATTACHMENT_ADDED',
      'ATTACHMENT_REMOVED'
    ].includes(activityType)
  ) {
    return {
      type: 'TASK',
      taskId: entityId,
      boardId: targetBoardId || undefined
    };
  }

  // 3. Board Notifications
  if (
    entityType === 'BOARD' ||
    [
      'BOARD_CREATED',
      'BOARD_MEMBER_ADDED',
      'BOARD_MEMBER_REMOVED',
      'ROLE_CHANGED'
    ].includes(activityType)
  ) {
    return {
      type: 'BOARD',
      boardId: entityId
    };
  }

  // 4. Meeting Proposals Notifications
  if (
    entityType === 'MEETING' ||
    entityType === 'PROPOSAL' ||
    [
      'MEETING_PROPOSALS_READY',
      'PROPOSALS_READY',
      'MEETING-PROPOSALS-READY'
    ].includes(activityType)
  ) {
    return {
      type: 'MEETING_PROPOSALS',
      sessionId: entityId
    };
  }

  return { type: 'UNKNOWN' };
};

export const executeNotificationNavigation = (
  destination: NotificationDestination,
  helpers: {
    navigate: (path: string) => void;
    openTaskModal: (taskId: number, options?: { commentId?: number; tab?: 'comments' | 'attachments' | 'activity' }) => void;
  }
) => {
  switch (destination.type) {
    case 'TASK':
      helpers.openTaskModal(destination.taskId, {
        commentId: destination.commentId,
        tab: 'comments'
      });
      if (destination.boardId) {
        helpers.navigate(`/board/${destination.boardId}?taskId=${destination.taskId}`);
      }
      break;
    case 'BOARD':
      helpers.navigate(`/board/${destination.boardId}`);
      break;
    case 'MEETING_PROPOSALS':
      helpers.navigate(`/meetings/${destination.sessionId}/proposals`);
      break;
    case 'NAVIGATE':
      helpers.navigate(destination.path);
      break;
    default:
      break;
  }
};
