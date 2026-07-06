import React, { useState } from 'react';
import CommentsTab from './tabs/CommentsTab';
import AttachmentsTab from './tabs/AttachmentsTab';
import ActivityTab from './tabs/ActivityTab';
import { type Task } from '../../../../services/tasksApi';
import { type User } from '../../../../services/usersApi';

interface TaskTabsProps {
  task: Task;
  currentUserId: number | null;
  users: User[];
}

type TabType = 'comments' | 'attachments' | 'activity';

const TaskTabs: React.FC<TaskTabsProps> = ({ task, currentUserId, users }) => {
  const [activeTab, setActiveTab] = useState<TabType>('comments');

  return (
    <div className="mt-8">
      <div className="flex border-b border-brand-border gap-6">
        <button
          onClick={() => setActiveTab('comments')}
          className={`pb-3 text-sm font-medium transition-colors border-b-2 ${
            activeTab === 'comments' 
              ? 'border-brand-primary text-brand-primary' 
              : 'border-transparent text-brand-text-muted hover:text-brand-text'
          }`}
        >
          Comments
        </button>
        <button
          onClick={() => setActiveTab('attachments')}
          className={`pb-3 text-sm font-medium transition-colors border-b-2 ${
            activeTab === 'attachments' 
              ? 'border-brand-primary text-brand-primary' 
              : 'border-transparent text-brand-text-muted hover:text-brand-text'
          }`}
        >
          Attachments
        </button>
        <button
          onClick={() => setActiveTab('activity')}
          className={`pb-3 text-sm font-medium transition-colors border-b-2 ${
            activeTab === 'activity' 
              ? 'border-brand-primary text-brand-primary' 
              : 'border-transparent text-brand-text-muted hover:text-brand-text'
          }`}
        >
          Activity
        </button>
      </div>

      <div className="pt-6">
        {activeTab === 'comments' && <CommentsTab task={task} currentUserId={currentUserId} users={users} />}
        {activeTab === 'attachments' && <AttachmentsTab task={task} />}
        {activeTab === 'activity' && <ActivityTab task={task} />}
      </div>
    </div>
  );
};

export default TaskTabs;
