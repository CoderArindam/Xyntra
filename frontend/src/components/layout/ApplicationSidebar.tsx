import React, { useState, useEffect } from 'react';
import { NavLink, useLocation, Link } from 'react-router-dom';
import { 
  LayoutDashboard, 
  CheckSquare, 
  Settings, 
  Bell, 
  ShieldAlert, 
  Search, 
  ChevronLeft,
  ChevronRight,
  Menu,
  X
} from 'lucide-react';
import { useAuthStore } from '../../store/authStore';
import { useBoardStore, useActiveBoards } from '../../store/boardStore';
import { useNotificationStore } from '../../store/notificationStore';
import { useUiStore } from '../../store/uiStore';
import WorkspaceSwitcher from '../common/WorkspaceSwitcher';
import { ProjectIdentity } from '../common/ProjectIdentity';
import UserAvatarDropdown from './UserAvatarDropdown';
import { formatUserName } from '../../utils/userHelpers';

export const ApplicationSidebar: React.FC = () => {
  const location = useLocation();
  const { user } = useAuthStore();
  const activeBoards = useActiveBoards();
  const { fetchBoards } = useBoardStore();
  const { unreadCount, fetchNotifications } = useNotificationStore();
  const { isSidebarCollapsed, toggleSidebar } = useUiStore();
  
  const [projectSearch, setProjectSearch] = useState('');
  const [isMobileOpen, setIsMobileOpen] = useState(false);

  useEffect(() => {
    fetchBoards();
    fetchNotifications();
  }, [fetchBoards, fetchNotifications]);

  // Handle global keyboard shortcut (Ctrl+B)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'b') {
        e.preventDefault();
        toggleSidebar();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [toggleSidebar]);

  // Close mobile drawer on navigation
  useEffect(() => {
    setIsMobileOpen(false);
  }, [location.pathname]);

  const filteredBoards = activeBoards.filter(board => 
    board.name.toLowerCase().includes(projectSearch.toLowerCase())
  );

  const NavItem = ({ to, icon: Icon, label, badge, isExact = false }: { to: string, icon: any, label: string, badge?: number, isExact?: boolean }) => {
    const isActive = isExact 
      ? location.pathname === to 
      : location.pathname.startsWith(to);

    return (
      <Link
        to={to}
        className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
          isActive 
            ? 'bg-brand-surface-hover text-brand-primary' 
            : 'text-brand-text hover:bg-brand-surface-low'
        }`}
        title={isSidebarCollapsed ? label : undefined}
      >
        <Icon size={18} className={isActive ? 'text-brand-primary' : 'text-brand-text-muted'} />
        {!isSidebarCollapsed && (
          <span className="flex-1 truncate">{label}</span>
        )}
        {!isSidebarCollapsed && badge !== undefined && badge > 0 && (
          <span className="bg-brand-primary text-white text-[10px] font-bold px-1.5 py-0.5 rounded-full min-w-[18px] text-center">
            {badge > 99 ? '99+' : badge}
          </span>
        )}
      </Link>
    );
  };

  const sidebarContent = (
    <div className="flex flex-col h-full bg-brand-surface border-r border-brand-border transition-all duration-300">
      
      {/* Header / Workspace */}
      <div className={`p-4 border-b border-brand-border flex items-center ${isSidebarCollapsed ? 'justify-center' : 'justify-between'} shrink-0 min-h-[64px]`}>
        {!isSidebarCollapsed ? (
          <div className="flex-1 min-w-0">
            <WorkspaceSwitcher />
          </div>
        ) : (
          <WorkspaceSwitcher isCollapsed />
        )}
      </div>

      {/* Scrollable Area */}
      <div className="flex-1 overflow-y-auto py-4 overflow-x-hidden">
        
        {/* Main Section */}
        <div className="px-3 mb-6">
          {!isSidebarCollapsed && <h3 className="px-3 text-xs font-bold text-brand-text-muted uppercase tracking-wider mb-2">Main</h3>}
          <div className="space-y-1">
            <NavItem to="/dashboard" icon={LayoutDashboard} label="Dashboard" isExact />
            <NavItem to="/my-work" icon={CheckSquare} label="My Work" />
          </div>
        </div>

        {/* Projects Section */}
        <div className="px-3 mb-6">
          {!isSidebarCollapsed && (
            <div className="px-3 mb-2 flex items-center justify-between">
              <h3 className="text-xs font-bold text-brand-text-muted uppercase tracking-wider">Projects</h3>
            </div>
          )}
          
          {!isSidebarCollapsed && (
            <div className="px-3 mb-3">
              <div className="relative">
                <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-brand-text-muted" />
                <input 
                  type="text" 
                  value={projectSearch}
                  onChange={(e) => setProjectSearch(e.target.value)}
                  placeholder="Filter projects..."
                  className="w-full bg-brand-bg border border-brand-border rounded-md pl-8 pr-3 py-1.5 text-xs text-brand-text outline-none focus:border-brand-primary transition-colors"
                />
              </div>
            </div>
          )}

          <div className="space-y-1">
            {filteredBoards.map(board => {
              const isActive = location.pathname.startsWith(`/board/${board.id}`);
              return (
                <Link
                  key={board.id}
                  to={`/board/${board.id}`}
                  className={`flex items-center gap-3 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors group ${
                    isActive 
                      ? 'bg-brand-surface-hover text-brand-primary' 
                      : 'text-brand-text hover:bg-brand-surface-low'
                  }`}
                  title={isSidebarCollapsed ? board.name : undefined}
                >
                  <ProjectIdentity 
                    board={board} 
                    size="sm" 
                    className={`transition-transform group-hover:scale-105 ${isSidebarCollapsed ? 'mx-auto' : ''}`} 
                  />
                </Link>
              );
            })}
            
            {filteredBoards.length === 0 && !isSidebarCollapsed && (
              <div className="px-3 py-2 text-xs text-brand-text-muted">No projects found.</div>
            )}
          </div>
        </div>

        {/* Administration Section */}
        {user?.role === 'SUPER_ADMIN' && (
          <div className="px-3 mb-6">
            {!isSidebarCollapsed && <h3 className="px-3 text-xs font-bold text-brand-text-muted uppercase tracking-wider mb-2">Administration</h3>}
            <div className="space-y-1">
              <NavItem to="/admin" icon={ShieldAlert} label="Admin Panel" />
            </div>
          </div>
        )}
      </div>

      {/* Footer / Personal */}
      <div className="p-3 border-t border-brand-border shrink-0">
        <div className="space-y-1 mb-4">
          <NavItem to="/notifications" icon={Bell} label="Notifications" badge={unreadCount} />
          <NavItem to="/settings/account" icon={Settings} label="Settings" />
        </div>
        
        <div className={`flex items-center ${isSidebarCollapsed ? 'justify-center' : 'px-3 gap-3'}`}>
          <UserAvatarDropdown isSidebarCollapsed={isSidebarCollapsed} />
          {!isSidebarCollapsed && (
            <div className="flex-1 min-w-0 flex flex-col">
              <span className="text-sm font-medium text-brand-text truncate">{formatUserName(user)}</span>
              <span className="text-xs text-brand-text-muted truncate">{user?.email}</span>
            </div>
          )}
        </div>
      </div>
      
    </div>
  );

  return (
    <>
      {/* Mobile Hamburger (visible only on small screens) */}
      <div className="md:hidden fixed top-0 left-0 right-0 h-16 bg-brand-surface border-b border-brand-border flex items-center justify-between px-4 z-40">
        <div className="flex items-center gap-3">
          <button 
            onClick={() => setIsMobileOpen(true)}
            className="p-2 -ml-2 rounded-lg text-brand-text-muted hover:bg-brand-surface-low"
          >
            <Menu size={20} />
          </button>
          <span className="font-bold text-brand-text">ProSync</span>
        </div>
      </div>

      {/* Mobile Drawer Overlay */}
      {isMobileOpen && (
        <div 
          className="md:hidden fixed inset-0 bg-black/50 z-50 animate-in fade-in"
          onClick={() => setIsMobileOpen(false)}
        />
      )}

      {/* Sidebar Container */}
      <aside 
        className={`
          fixed md:relative inset-y-0 left-0 z-50 
          transform transition-all duration-300 ease-in-out
          ${isMobileOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}
          ${isSidebarCollapsed ? 'w-16' : 'w-64'}
          bg-brand-surface
        `}
      >
        {/* Mobile Close Button */}
        <button 
          className="md:hidden absolute top-4 right-4 p-2 rounded-lg text-brand-text-muted hover:bg-brand-surface-low z-50"
          onClick={() => setIsMobileOpen(false)}
        >
          <X size={20} />
        </button>

        {sidebarContent}

        {/* Desktop Collapse Toggle */}
        <button
          onClick={toggleSidebar}
          className="hidden md:flex absolute -right-3 top-20 w-6 h-6 bg-brand-surface border border-brand-border rounded-full items-center justify-center text-brand-text-muted hover:text-brand-primary hover:border-brand-primary shadow-sm transition-colors z-50"
          title={isSidebarCollapsed ? "Expand Sidebar (Ctrl+B)" : "Collapse Sidebar (Ctrl+B)"}
        >
          {isSidebarCollapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
        </button>
      </aside>
    </>
  );
};

export default ApplicationSidebar;
