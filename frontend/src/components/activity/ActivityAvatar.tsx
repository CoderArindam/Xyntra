import React from 'react';
import type { Activity } from '../../api/activityApi';

interface ActivityAvatarProps {
  activity: Activity;
}

import { UserAvatar } from '../common/UserAvatar';

const ActivityAvatar: React.FC<ActivityAvatarProps> = ({ activity }) => {
  const activityUser = {
    first_name: activity.actor_first_name,
    last_name: activity.actor_last_name,
    email: activity.actor_email,
    avatar_url: activity.actor_avatar_url
  };

  return <UserAvatar user={activityUser} size="md" />;
};

export default ActivityAvatar;
