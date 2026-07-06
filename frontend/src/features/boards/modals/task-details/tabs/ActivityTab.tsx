import React from 'react';
import { type Task } from '../../../../../services/tasksApi';
import ActivityTimeline from '../../../../activity/components/ActivityTimeline';

interface ActivityTabProps {
  task: Task;
}

const ActivityTab: React.FC<ActivityTabProps> = ({ task }) => {
  return (
    <div className="py-2">
      <ActivityTimeline taskId={task.id} />
    </div>
  );
};

export default ActivityTab;
