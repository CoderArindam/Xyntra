import React from 'react';
import type { Board } from '../../api/boardsApi';
import { getProjectColorClass } from '../../utils/projectIdentity';

interface ProjectIdentityProps {
  board: Partial<Board>;
  showKey?: boolean;
  className?: string;
  size?: 'sm' | 'md' | 'lg';
}

export const ProjectIdentity: React.FC<ProjectIdentityProps> = ({ board, showKey = false, className = '', size = 'md' }) => {
  const iconSize = size === 'sm' ? 'text-base' : size === 'lg' ? 'text-2xl' : 'text-xl';
  const nameSize = size === 'sm' ? 'text-sm' : size === 'lg' ? 'text-2xl font-bold' : 'text-base font-semibold';
  
  const colorClass = getProjectColorClass(board.color);

  return (
    <div className={`flex items-center gap-2 min-w-0 ${className}`}>
      {board.icon ? (
        <span className={`${iconSize} flex-shrink-0 leading-none`}>{board.icon}</span>
      ) : (
        <div 
          className={`rounded flex-shrink-0 ${colorClass} ${size === 'sm' ? 'w-3 h-3' : size === 'lg' ? 'w-6 h-6' : 'w-4 h-4'}`} 
        />
      )}
      <span className={`text-brand-text ${nameSize} truncate`}>
        {board.name || 'Unnamed Project'}
      </span>
      {showKey && board.project_key && (
        <span className="flex-shrink-0 text-xs font-mono font-medium text-brand-text-muted bg-brand-surface-low px-1.5 py-0.5 rounded">
          {board.project_key}
        </span>
      )}
    </div>
  );
};
