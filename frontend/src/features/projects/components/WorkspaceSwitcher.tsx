import React from 'react';
import { ChevronDown } from 'lucide-react';
import WorkspaceLogo from '../../../components/common/WorkspaceLogo';
import { useOrganizationStore } from '../../../store/organizationStore';

interface WorkspaceSwitcherProps {
  isCollapsed?: boolean;
}

export const WorkspaceSwitcher: React.FC<WorkspaceSwitcherProps> = ({ isCollapsed = false }) => {
  const { profile } = useOrganizationStore();
  const [isOpen, setIsOpen] = React.useState(false);
  const dropdownRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const displayName = profile?.name || 'Workspace';

  return (
    <div className="relative" ref={dropdownRef}>
      <button 
        onClick={() => setIsOpen(!isOpen)}
        className={`flex items-center hover:bg-brand-surface-low rounded-lg transition-colors ${isCollapsed ? 'p-1' : 'gap-3 px-2 py-1.5'}`}
        title={isCollapsed ? displayName : undefined}
      >
        <WorkspaceLogo name={displayName} logoUrl={profile?.logo_url} size={isCollapsed ? "sm" : "md"} variant="rounded" />
        {!isCollapsed && (
          <>
            <div className="flex flex-col items-start hidden sm:flex">
              <span className="text-sm font-bold leading-tight text-brand-text truncate max-w-[150px]">{displayName}</span>
              <span className="text-[10px] text-brand-text-muted leading-tight uppercase tracking-wide">ProSync Workspace</span>
            </div>
            <ChevronDown size={14} className="text-brand-text-muted ml-1" />
          </>
        )}
      </button>

      {isOpen && (
        <div className="absolute top-full left-0 mt-2 w-64 bg-brand-surface border border-brand-border rounded-xl shadow-xl z-50 overflow-hidden animate-in fade-in zoom-in-95 duration-100">
          <div className="p-3 bg-brand-surface-low border-b border-brand-border">
            <span className="text-xs font-semibold text-brand-text-muted uppercase tracking-wider mb-2 block">Current Workspace</span>
            <div className="flex items-center gap-3">
              <WorkspaceLogo name={displayName} logoUrl={profile?.logo_url} size="md" variant="rounded" />
              <div className="flex flex-col truncate">
                <span className="text-sm font-bold text-brand-text truncate">{displayName}</span>
              </div>
            </div>
          </div>
          
          <div className="p-3">
            <div className="flex items-center justify-between opacity-50 cursor-not-allowed px-2 py-2 rounded-lg bg-brand-bg border border-dashed border-brand-border">
              <span className="text-sm font-medium text-brand-text">Switch Workspace</span>
              <span className="text-[10px] bg-brand-surface-high px-2 py-0.5 rounded text-brand-text-muted uppercase font-bold">Coming Soon</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default WorkspaceSwitcher;
