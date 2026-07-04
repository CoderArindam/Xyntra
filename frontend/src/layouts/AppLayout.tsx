import React from 'react';
import { Outlet, Link, useLocation } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';

import NotificationBell from '../components/layout/NotificationBell';
import UserAvatarDropdown from '../components/layout/UserAvatarDropdown';
import { useOrganizationStore } from '../store/organizationStore';
import WorkspaceLogo from '../components/common/WorkspaceLogo';

export const AppLayout: React.FC = () => {
  const { user } = useAuthStore();
  const { profile } = useOrganizationStore();
  const location = useLocation();

  return (
    <div className="min-h-screen bg-brand-bg text-brand-text flex flex-col">
      <header className="h-16 bg-brand-surface border-b border-brand-border flex items-center justify-between px-8 sticky top-0 z-50">
        <div className="flex items-center gap-8">
          <Link to="/dashboard" className="flex items-center gap-3 hover:opacity-80 transition">
            <WorkspaceLogo name={profile?.name} logoUrl={profile?.logo_url} size="md" />
            <div className="flex flex-col">
              <span className="text-sm font-bold leading-tight">{profile?.name || 'ProSync'}</span>
              <span className="text-[10px] text-brand-text-muted leading-tight uppercase tracking-wide">ProSync Workspace</span>
            </div>
          </Link>

          <nav className="flex bg-brand-surface-low rounded-full p-1 gap-1">
            <Link 
              to="/dashboard" 
              className={`px-4 py-1.5 text-sm rounded-full font-medium transition-colors ${
                location.pathname === '/dashboard' || location.pathname.startsWith('/boards')
                  ? 'bg-brand-surface text-brand-primary shadow-sm' 
                  : 'hover:bg-brand-surface text-brand-text'
              }`}
            >
              Projects
            </Link>
            <Link 
              to="/my-work" 
              className={`px-4 py-1.5 text-sm rounded-full font-medium transition-colors ${
                location.pathname.startsWith('/my-work')
                  ? 'bg-brand-surface text-brand-primary shadow-sm' 
                  : 'hover:bg-brand-surface text-brand-text'
              }`}
            >
              My Work
            </Link>
            {user?.role === 'SUPER_ADMIN' && (
              <Link 
                to="/admin" 
                className={`px-4 py-1.5 text-sm rounded-full font-medium transition-colors ${
                  location.pathname.startsWith('/admin')
                    ? 'bg-brand-surface text-brand-primary shadow-sm' 
                    : 'hover:bg-brand-surface text-brand-text'
                }`}
              >
                Admin
              </Link>
            )}
          </nav>
        </div>

        <div className="flex items-center gap-4">
          <NotificationBell />
          <UserAvatarDropdown />
        </div>
      </header>

      <main className="flex-1 flex flex-col relative overflow-hidden">
        <Outlet />
      </main>
    </div>
  );
};

export default AppLayout;
