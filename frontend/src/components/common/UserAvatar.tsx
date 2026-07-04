import React, { useState } from 'react';
import { getInitials, type BaseUser } from '../../utils/userHelpers';

interface UserAvatarProps {
  user: BaseUser | null | undefined;
  size?: 'sm' | 'md' | 'lg' | 'xl' | 'xxl';
  className?: string;
  onClick?: () => void;
}

const sizeClasses = {
  sm: 'w-6 h-6 text-[10px]',
  md: 'w-8 h-8 text-xs',
  lg: 'w-10 h-10 text-sm',
  xl: 'w-16 h-16 text-xl',
  xxl: 'w-24 h-24 text-2xl',
};

const AVATAR_COLORS = [
  '#2563EB', // Blue
  '#059669', // Emerald
  '#D97706', // Amber
  '#DC2626', // Red
  '#7C3AED', // Violet
  '#DB2777', // Pink
  '#0891B2', // Cyan
  '#EA580C', // Orange
];

const getColorForUser = (user: BaseUser | null | undefined): string => {
  if (!user) return '#6B7280'; // Gray for null users
  const identifier = user.email || (user as any).id?.toString() || user.first_name || 'default';
  let hash = 0;
  for (let i = 0; i < identifier.length; i++) {
    hash = identifier.charCodeAt(i) + ((hash << 5) - hash);
  }
  const index = Math.abs(hash) % AVATAR_COLORS.length;
  return AVATAR_COLORS[index];
};

export const UserAvatar: React.FC<UserAvatarProps> = ({ 
  user, 
  size = 'md', 
  className = '',
  onClick
}) => {
  const [imageError, setImageError] = useState(false);
  const initials = getInitials(user);
  
  const bgColor = getColorForUser(user);

  const containerClasses = `
    relative flex items-center justify-center shrink-0
    font-medium rounded-full overflow-hidden
    ${sizeClasses[size]}
    ${onClick ? 'cursor-pointer hover:ring-2 ring-brand-primary/50 transition-all' : ''}
    ${className}
  `;

  const avatarUrl = (user as any)?.avatar_url;

  if (avatarUrl && !imageError) {
    const baseUrl = import.meta.env.VITE_API_BASE_URL ? import.meta.env.VITE_API_BASE_URL.replace('/api/v1', '') : '';
    const fullUrl = avatarUrl.startsWith('http') ? avatarUrl : `${baseUrl}${avatarUrl}`;

    return (
      <div className={containerClasses} onClick={onClick}>
        <img 
          src={fullUrl} 
          alt={initials}
          className="w-full h-full object-cover"
          onError={() => setImageError(true)}
        />
      </div>
    );
  }

  return (
    <div 
      className={containerClasses} 
      onClick={onClick}
      style={{ backgroundColor: bgColor, color: '#ffffff' }}
    >
      {initials}
    </div>
  );
};

export default UserAvatar;
