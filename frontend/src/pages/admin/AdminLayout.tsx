import React from 'react';
import { Navigate, Outlet, Link, useLocation } from 'react-router-dom';
import { useAuthStore } from '../../store/authStore';
import { ShieldCheck, Users, FolderKanban, ArrowLeft } from 'lucide-react';
import { UserAvatar } from '../../components/common/UserAvatar';
import { formatUserName } from '../../utils/userHelpers';

const AdminLayout: React.FC = () => {
  const { user } = useAuthStore();
  const location = useLocation();

  if (!user || user.role !== 'SUPER_ADMIN') {
    return <Navigate to="/dashboard" replace />;
  }

  const navItems = [
    { name: 'Overview', path: '/admin', icon: ShieldCheck, exact: true },
    { name: 'Users', path: '/admin/users', icon: Users, exact: false },
    { name: 'Boards', path: '/admin/boards', icon: FolderKanban, exact: false },
  ];

  return (
    <div className="min-h-screen bg-brand-bg text-brand-text flex flex-col">
      {/* Admin Top Header */}
      <header className="h-16 bg-brand-surface border-b border-brand-border flex items-center justify-between px-8 sticky top-0 z-50 shadow-sm">
        <div className="flex items-center gap-6">
          <Link 
            to="/dashboard" 
            className="flex items-center gap-2 text-sm font-medium text-brand-text-muted hover:text-brand-text transition-colors"
          >
            <ArrowLeft size={16} />
            Back to App
          </Link>
          <div className="h-4 w-px bg-brand-border"></div>
          <div className="flex items-center gap-2">
            <ShieldCheck size={20} className="text-brand-primary" />
            <h1 className="text-lg font-semibold tracking-tight text-brand-text">Admin Settings</h1>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex flex-col items-end">
            <div className="flex items-center gap-3 bg-brand-surface border border-brand-border px-3 py-1.5 rounded-full shadow-sm">
              <UserAvatar user={user} size="sm" />
              <span className="text-sm font-medium text-brand-text pr-1">{formatUserName(user)}</span>
            </div>
          </div>
        </div>
      </header>

      {/* Admin Content Area */}
      <div className="flex-1 max-w-7xl mx-auto w-full p-8 flex flex-col md:flex-row gap-8">
        
        {/* Admin Navigation */}
        <aside className="w-full md:w-56 shrink-0">
          <nav className="flex md:flex-col gap-1 overflow-x-auto pb-2 md:pb-0">
            {navItems.map((item) => {
              const isActive = item.exact 
                ? location.pathname === item.path
                : location.pathname.startsWith(item.path);
                
              const Icon = item.icon;
              return (
                <Link
                  key={item.name}
                  to={item.path}
                  className={`flex items-center gap-3 px-4 py-2.5 rounded-xl font-medium text-sm transition-all duration-200 whitespace-nowrap ${
                    isActive 
                      ? 'bg-brand-primary/10 text-brand-primary shadow-sm ring-1 ring-brand-primary/20' 
                      : 'text-brand-text-muted hover:text-brand-text hover:bg-brand-surface-low'
                  }`}
                >
                  <Icon size={18} className={isActive ? 'text-brand-primary' : 'opacity-70'} />
                  {item.name}
                </Link>
              );
            })}
          </nav>
        </aside>

        {/* Main Content */}
        <main className="flex-1 min-w-0 bg-brand-surface border border-brand-border rounded-2xl shadow-xl overflow-hidden flex flex-col">
          <div className="p-8 flex-1 overflow-y-auto">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
};

export default AdminLayout;
