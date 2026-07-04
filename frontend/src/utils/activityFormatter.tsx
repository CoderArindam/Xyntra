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
import type { CanonicalActivity as Activity } from '../api/activityApi';
import { ACTIVITY_TYPES } from '../constants/activityTypes';

export interface FormattedActivity {
  icon: LucideIcon;
  title: string;
  description: React.ReactNode;
  accentColor: string;
}

import { formatUserName } from './userHelpers';

export const formatActivity = (activity: Activity): FormattedActivity => {
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
      
    case ACTIVITY_TYPES.STATUS_CHANGED:
      return {
        icon: ArrowRight,
        title: 'Status changed',
        description: (
          <span>
            {actorName} moved task to a new status
          </span>
        ),
        accentColor: 'text-blue-500 bg-blue-500/10 border-blue-500/20'
      };
      
    case ACTIVITY_TYPES.TITLE_CHANGED:
      return {
        icon: Edit3,
        title: 'Title changed',
        description: (
          <span>
            {actorName} changed the title from <del className="text-brand-text-muted">{activity.old_value?.title}</del> to <strong className="text-brand-text-primary">{activity.new_value?.title}</strong>
          </span>
        ),
        accentColor: 'text-brand-primary bg-brand-primary/10 border-brand-primary/20'
      };
      
    case ACTIVITY_TYPES.DESCRIPTION_CHANGED:
      return {
        icon: Edit3,
        title: 'Description updated',
        description: `${actorName} updated the task description`,
        accentColor: 'text-brand-primary bg-brand-primary/10 border-brand-primary/20'
      };

    case ACTIVITY_TYPES.PRIORITY_CHANGED:
      return {
        icon: ArrowRight,
        title: 'Priority changed',
        description: (
          <span>
            {actorName} changed priority from <del className="text-brand-text-muted">{activity.old_value?.priority}</del> to <strong className="text-brand-text-primary">{activity.new_value?.priority}</strong>
          </span>
        ),
        accentColor: 'text-orange-500 bg-orange-500/10 border-orange-500/20'
      };

    case ACTIVITY_TYPES.DUE_DATE_CHANGED:
      const oldDate = activity.old_value?.due_date ? new Date(activity.old_value.due_date).toLocaleDateString() : 'None';
      const newDate = activity.new_value?.due_date ? new Date(activity.new_value.due_date).toLocaleDateString() : 'None';
      return {
        icon: CalendarDays,
        title: 'Due date changed',
        description: (
          <span>
            {actorName} changed due date from <del className="text-brand-text-muted">{oldDate}</del> to <strong className="text-brand-text-primary">{newDate}</strong>
          </span>
        ),
        accentColor: 'text-purple-500 bg-purple-500/10 border-purple-500/20'
      };

    case ACTIVITY_TYPES.ASSIGNEE_CHANGED:
      return {
        icon: UserRound,
        title: 'Assignee changed',
        description: `${actorName} reassigned this task`,
        accentColor: 'text-indigo-500 bg-indigo-500/10 border-indigo-500/20'
      };

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
