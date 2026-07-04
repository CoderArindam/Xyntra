import React from 'react';

interface WorkspaceLogoProps {
  name?: string | null;
  logoUrl?: string | null;
  size?: 'sm' | 'md' | 'lg' | 'xl';
  className?: string;
}

const getInitials = (name: string): string => {
  if (!name) return 'W';
  
  const words = name.trim().split(/\s+/);
  if (words.length === 0) return 'W';
  if (words.length === 1) return words[0].charAt(0).toUpperCase();
  
  return (words[0].charAt(0) + words[1].charAt(0)).toUpperCase();
};

export const WorkspaceLogo: React.FC<WorkspaceLogoProps> = ({ 
  name = 'Workspace', 
  logoUrl, 
  size = 'md',
  className = '' 
}) => {
  const sizeClasses = {
    sm: 'w-6 h-6 text-xs',
    md: 'w-8 h-8 text-sm',
    lg: 'w-12 h-12 text-base',
    xl: 'w-16 h-16 text-lg'
  };

  const baseClasses = `flex-shrink-0 flex items-center justify-center rounded bg-brand-primary text-white font-semibold ${sizeClasses[size]} ${className}`;

  if (logoUrl) {
    const baseUrl = import.meta.env.VITE_API_BASE_URL ? import.meta.env.VITE_API_BASE_URL.replace('/api/v1', '') : '';
    const fullUrl = logoUrl.startsWith('http') || logoUrl.startsWith('data:') ? logoUrl : `${baseUrl}${logoUrl}`;

    return (
      <img 
        src={fullUrl} 
        alt={name || 'Workspace Logo'} 
        className={`${baseClasses} object-cover`}
        onError={(e) => {
          // Fallback to initials if image fails to load
          e.currentTarget.style.display = 'none';
          e.currentTarget.nextElementSibling?.classList.remove('hidden');
        }}
      />
    );
  }

  return (
    <div className={baseClasses}>
      {getInitials(name || 'Workspace')}
    </div>
  );
};

export default WorkspaceLogo;
