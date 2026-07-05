import React from 'react';
import { Loader2 } from 'lucide-react';
import WorkspaceLogo from './WorkspaceLogo';

interface WorkspaceLoaderProps {
  name?: string | null;
  logoUrl?: string | null;
}

export const WorkspaceLoader: React.FC<WorkspaceLoaderProps> = ({ name, logoUrl }) => {
  return (
    <div className="flex h-screen w-full flex-col items-center justify-center bg-brand-bg text-brand-text animate-in fade-in duration-300">
      <div className="flex flex-col items-center max-w-sm text-center">
        <WorkspaceLogo 
          name={name} 
          logoUrl={logoUrl} 
          size="xl" 
          variant="rounded" 
          className="mb-6 shadow-sm" 
        />
        <h1 className="text-2xl font-bold tracking-tight text-brand-text mb-2">
          {name || 'ProSync Workspace'}
        </h1>
        <div className="flex items-center justify-center gap-2 text-sm text-brand-text-muted mt-4 bg-brand-surface border border-brand-border px-4 py-2 rounded-full shadow-sm">
          <Loader2 className="animate-spin" size={16} />
          <span>Loading...</span>
        </div>
      </div>
    </div>
  );
};

export default WorkspaceLoader;
