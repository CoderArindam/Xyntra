import React from 'react';
import { type LucideIcon } from 'lucide-react';

interface ActivityIconProps {
  icon: LucideIcon;
  accentColor: string;
}

const ActivityIcon: React.FC<ActivityIconProps> = ({ icon: Icon, accentColor }) => {
  return (
    <div className={`w-6 h-6 rounded-full flex items-center justify-center border ${accentColor}`}>
      <Icon size={12} className="opacity-80" />
    </div>
  );
};

export default ActivityIcon;
