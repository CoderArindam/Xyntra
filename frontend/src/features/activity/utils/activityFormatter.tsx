import React from 'react';
import { 
  Plus, 
  Edit3, 
  ArrowRight, 
  CalendarDays, 
  UserRound, 
  MessageCircle, 
  Paperclip, 
  Trash2, 
  Clock3,
  type LucideIcon
} from 'lucide-react';
import type { CanonicalActivity as Activity } from '../../../services/activityApi';
import { ACTIVITY_TYPES } from '../../../constants/activityTypes';
import { formatUserName } from '../../../utils/userHelpers';
import { useTaskStore } from '../../../store/taskStore';

export interface FormattedActivity {
  icon: LucideIcon;
  title: string;
  description: React.ReactNode;
  accentColor: string;
}

const getAssigneeDisplayName = (assignedToId: number | null | undefined, nameInPayload?: string | null): string | null => {
  if (!assignedToId) return null;
  if (nameInPayload && nameInPayload.trim()) return nameInPayload.trim();
  
  const user = useTaskStore.getState().entities.users[assignedToId] || useTaskStore.getState().entities.boardMembers[assignedToId];
  if (user) {
    return formatUserName(user);
  }
  return `User #${assignedToId}`;
};

const getColumnDisplayName = (columnId: number | null | undefined, nameInPayload?: string | null): string | null => {
  if (nameInPayload && nameInPayload.trim()) return nameInPayload.trim();
  if (!columnId) return null;
  
  const col = useTaskStore.getState().entities.columns[columnId];
  if (col) {
    return col.name;
  }
  return null;
};

export const formatActivity = (
  activity: Activity,
  recipientUserId?: number | null
): FormattedActivity => {
  const actorName = formatUserName({
    first_name: activity.actor_first_name,
    last_name: activity.actor_last_name,
    email: activity.actor_email
  });

  switch (activity.activity_type) {
    case ACTIVITY_TYPES.TASK_CREATED:
      return {
        icon: Plus,
        title: 'Task created',
        description: `${actorName} created this task`,
        accentColor: 'text-green-500 bg-green-500/10 border-green-500/20'
      };
      
    case ACTIVITY_TYPES.STATUS_CHANGED: {
      const oldStatus = getColumnDisplayName(activity.old_value?.column_id, activity.old_value?.column_name || activity.old_value?.status);
      const newStatus = getColumnDisplayName(activity.new_value?.column_id, activity.new_value?.column_name || activity.new_value?.status);
      return {
        icon: ArrowRight,
        title: 'Status changed',
        description: (
          <span>
            {actorName} moved task {oldStatus && newStatus ? <>from <del className="text-brand-text-muted">{oldStatus}</del> to <strong className="text-brand-text-primary">{newStatus}</strong></> : newStatus ? <>to <strong className="text-brand-text-primary">{newStatus}</strong></> : 'to a new status'}
          </span>
        ),
        accentColor: 'text-blue-500 bg-blue-500/10 border-blue-500/20'
      };
    }
      
    case ACTIVITY_TYPES.TITLE_CHANGED: {
      const oldTitle = activity.old_value?.title;
      const newTitle = activity.new_value?.title;
      return {
        icon: Edit3,
        title: 'Title changed',
        description: (
          <span>
            {actorName} {oldTitle && newTitle ? <>changed title from <del className="text-brand-text-muted">{oldTitle}</del> to <strong className="text-brand-text-primary">{newTitle}</strong></> : newTitle ? <>changed title to <strong className="text-brand-text-primary">{newTitle}</strong></> : 'updated the task title'}
          </span>
        ),
        accentColor: 'text-brand-primary bg-brand-primary/10 border-brand-primary/20'
      };
    }
      
    case ACTIVITY_TYPES.DESCRIPTION_CHANGED: {
      return {
        icon: Edit3,
        title: 'Description updated',
        description: `${actorName} updated the task description`,
        accentColor: 'text-brand-primary bg-brand-primary/10 border-brand-primary/20'
      };
    }

    case ACTIVITY_TYPES.PRIORITY_CHANGED: {
      const oldPriority = activity.old_value?.priority;
      const newPriority = activity.new_value?.priority;
      return {
        icon: ArrowRight,
        title: 'Priority changed',
        description: (
          <span>
            {actorName} {oldPriority && newPriority ? <>changed priority from <del className="text-brand-text-muted">{oldPriority}</del> to <strong className="text-brand-text-primary">{newPriority}</strong></> : newPriority ? <>changed priority to <strong className="text-brand-text-primary">{newPriority}</strong></> : 'updated priority'}
          </span>
        ),
        accentColor: 'text-orange-500 bg-orange-500/10 border-orange-500/20'
      };
    }

    case ACTIVITY_TYPES.DUE_DATE_CHANGED: {
      const oldDateVal = activity.old_value?.due_date;
      const newDateVal = activity.new_value?.due_date;
      const oldDateStr = oldDateVal ? new Date(oldDateVal).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : null;
      const newDateStr = newDateVal ? new Date(newDateVal).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : null;
      return {
        icon: CalendarDays,
        title: 'Due date changed',
        description: (
          <span>
            {actorName} {oldDateStr && newDateStr ? <>changed due date from <del className="text-brand-text-muted">{oldDateStr}</del> to <strong className="text-brand-text-primary">{newDateStr}</strong></> : newDateStr ? <>changed due date to <strong className="text-brand-text-primary">{newDateStr}</strong></> : 'removed the due date'}
          </span>
        ),
        accentColor: 'text-purple-500 bg-purple-500/10 border-purple-500/20'
      };
    }

    case ACTIVITY_TYPES.ASSIGNEE_CHANGED: {
      const isUnassigned = activity.new_value?.assigned_to === null || activity.new_value?.assigned_to === undefined;
      const oldAssigneeName = getAssigneeDisplayName(activity.old_value?.assigned_to, activity.old_value?.assignee_name);
      const newAssigneeName = getAssigneeDisplayName(activity.new_value?.assigned_to, activity.new_value?.assignee_name);
      const isRecipientNewAssignee = recipientUserId && activity.new_value?.assigned_to === recipientUserId;
      const isRecipientOldAssignee = recipientUserId && activity.old_value?.assigned_to === recipientUserId;

      let descriptionNode: React.ReactNode;
      if (isUnassigned) {
        if (isRecipientOldAssignee) {
          descriptionNode = `${actorName} unassigned you from this task`;
        } else if (oldAssigneeName) {
          descriptionNode = (
            <span>
              {actorName} unassigned <strong className="text-brand-text-primary">{oldAssigneeName}</strong> from this task
            </span>
          );
        } else {
          descriptionNode = `${actorName} unassigned this task`;
        }
      } else if (isRecipientNewAssignee) {
        descriptionNode = (
          <span>
            {actorName} assigned <strong className="text-brand-text-primary">you</strong> to this task
          </span>
        );
      } else if (oldAssigneeName && newAssigneeName && oldAssigneeName !== newAssigneeName) {
        if (isRecipientOldAssignee) {
          descriptionNode = (
            <span>
              {actorName} reassigned this task from <strong className="text-brand-text-primary">you</strong> to <strong className="text-brand-text-primary">{newAssigneeName}</strong>
            </span>
          );
        } else {
          descriptionNode = (
            <span>
              {actorName} reassigned this task from <del className="text-brand-text-muted">{oldAssigneeName}</del> to <strong className="text-brand-text-primary">{newAssigneeName}</strong>
            </span>
          );
        }
      } else {
        descriptionNode = (
          <span>
            {actorName} assigned this task to <strong className="text-brand-text-primary">{newAssigneeName || 'a member'}</strong>
          </span>
        );
      }

      return {
        icon: UserRound,
        title: 'Assignee changed',
        description: descriptionNode,
        accentColor: 'text-indigo-500 bg-indigo-500/10 border-indigo-500/20'
      };
    }

    case ACTIVITY_TYPES.COMMENT_ADDED:
      return {
        icon: MessageCircle,
        title: 'Comment added',
        description: `${actorName} left a comment`,
        accentColor: 'text-brand-primary bg-brand-primary/10 border-brand-primary/20'
      };

    case ACTIVITY_TYPES.COMMENT_DELETED:
      return {
        icon: Trash2,
        title: 'Comment deleted',
        description: `${actorName} deleted a comment`,
        accentColor: 'text-brand-text-muted bg-brand-surface-low border-brand-border'
      };

    case ACTIVITY_TYPES.ATTACHMENT_ADDED:
      return {
        icon: Paperclip,
        title: 'Attachment added',
        description: (
          <span>
            {actorName} attached <strong>{activity.new_value?.file_name}</strong>
          </span>
        ),
        accentColor: 'text-blue-500 bg-blue-500/10 border-blue-500/20'
      };

    default:
      return {
        icon: Clock3,
        title: 'Task updated',
        description: `${actorName} updated the task`,
        accentColor: 'text-brand-text-muted bg-brand-surface-low border-brand-border'
      };
  }
};
