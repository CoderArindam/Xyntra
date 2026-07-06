import React from 'react';
import { Outlet, NavLink, useParams, Link } from 'react-router-dom';
import { Settings, Users, GitMerge, Tag, Zap, Puzzle, ChevronRight, LayoutDashboard } from 'lucide-react';
import { usePageTitle } from '../../hooks/usePageTitle';
import { useProjectSettingsStore } from '../../store/projectSettingsStore';

const SETTINGS_NAV = [
  { name: 'General', path: '', icon: Settings, activeExact: true },
  { name: 'Members', path: 'members', icon: Users },
  { name: 'Workflow', path: 'workflow', icon: GitMerge },
  { name: 'Labels', path: 'labels', icon: Tag },
  { name: 'Automation', path: 'automation', icon: Zap },
  { name: 'Integrations', path: 'integrations', icon: Puzzle },
];

export const ProjectSettingsLayout: React.FC = () => {
  const { boardId } = useParams<{ boardId: string }>();
  const { currentSettings, fetchSettings, isLoading } = useProjectSettingsStore();

  React.useEffect(() => {
    if (boardId) {
      fetchSettings(parseInt(boardId, 10));
    }
  }, [boardId, fetchSettings]);

  usePageTitle(currentSettings?.settings ? `Settings - ${currentSettings.settings.icon || ''} ${currentSettings.settings.name}`.trim() : 'Project Settings');

  if (isLoading && !currentSettings) {
    return (
      <div className="flex-1 p-6 lg:p-10 max-w-[1400px] mx-auto w-full animate-pulse flex flex-col gap-8">
        <div className="h-8 bg-brand-surface-low rounded w-64"></div>
        <div className="flex gap-8">
          <div className="w-64 h-96 bg-brand-surface-low rounded"></div>
          <div className="flex-1 h-96 bg-brand-surface-low rounded"></div>
        </div>
      </div>
    );
  }

  if (!currentSettings || currentSettings.settings.archived_at) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <p className="text-brand-text-muted">Project not found or archived.</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col flex-1 bg-brand-bg overflow-hidden relative">
      <div className="flex-1 overflow-y-auto p-6 lg:p-10 max-w-[1400px] mx-auto w-full">
        
        {/* Breadcrumbs */}
        <div className="flex items-center gap-2 text-sm text-brand-text-muted mb-8">
          <Link to="/dashboard" className="hover:text-brand-primary flex items-center gap-1 transition-colors">
            <LayoutDashboard size={14} />
            <span>Organization</span>
          </Link>
          <ChevronRight size={14} />
          <Link to={`/board/${boardId}`} className="hover:text-brand-primary transition-colors font-medium text-brand-text flex items-center gap-1.5">
            {currentSettings.settings.icon && <span>{currentSettings.settings.icon}</span>}
            {currentSettings.settings.name}
          </Link>
          <ChevronRight size={14} />
          <span className="text-brand-text">Project Settings</span>
        </div>

        <div className="flex flex-col lg:flex-row gap-8">
          
          {/* Settings Sidebar */}
          <aside className="w-full lg:w-64 flex-shrink-0">
            <nav className="space-y-1 sticky top-6">
              {SETTINGS_NAV.map((item) => (
                <NavLink
                  key={item.name}
                  to={`/boards/${boardId}/settings/${item.path}`}
                  end={item.activeExact}
                  className={({ isActive }) =>
                    `flex items-center gap-3 px-3 py-2 text-sm font-medium rounded-lg transition-colors ${
                      isActive
                        ? 'bg-brand-primary/10 text-brand-primary'
                        : 'text-brand-text hover:bg-brand-surface-hover'
                    }`
                  }
                >
                  <item.icon size={18} className="flex-shrink-0" />
                  {item.name}
                  {item.path !== '' && (
                    <span className="ml-auto text-[10px] uppercase font-bold tracking-wider bg-brand-surface-low px-1.5 py-0.5 rounded text-brand-text-muted">Soon</span>
                  )}
                </NavLink>
              ))}
            </nav>
          </aside>

          {/* Settings Content */}
          <div className="flex-1 min-w-0">
            <Outlet />
          </div>
          
        </div>
      </div>
    </div>
  );
};
