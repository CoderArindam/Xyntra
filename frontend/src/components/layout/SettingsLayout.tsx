import React from 'react';
import { NavLink, Outlet, useLocation } from 'react-router-dom';
import { useAuthStore } from '../../store/authStore';
import { User, Building2, Palette, Bell, Shield, Key, CreditCard, Keyboard, Boxes } from 'lucide-react';

const SETTINGS_TABS = [
  { path: '/settings/account', label: 'My Account', icon: User, showFor: 'ALL' },
  { path: '/settings/organization', label: 'Workspace', icon: Building2, showFor: 'SUPER_ADMIN' },
  { path: '/settings/appearance', label: 'Appearance', icon: Palette, showFor: 'ALL' },
  { path: '/settings/notifications', label: 'Notifications', icon: Bell, showFor: 'ALL' },
  { path: '/settings/security', label: 'Security', icon: Shield, showFor: 'ALL' },
  { path: '/settings/integrations', label: 'Integrations', icon: Boxes, showFor: 'ALL' },
  { path: '/settings/keyboard-shortcuts', label: 'Keyboard Shortcuts', icon: Keyboard, showFor: 'ALL' },
  { path: '/settings/api-keys', label: 'API Keys', icon: Key, showFor: 'ALL' },
  { path: '/settings/billing', label: 'Billing', icon: CreditCard, showFor: 'SUPER_ADMIN' },
];

export const SettingsLayout: React.FC = () => {
  const { user } = useAuthStore();
  const location = useLocation();

  const visibleTabs = SETTINGS_TABS.filter(tab => 
    tab.showFor === 'ALL' || (tab.showFor === 'SUPER_ADMIN' && user?.role === 'SUPER_ADMIN')
  );

  return (
    <div className="flex-1 flex overflow-hidden bg-brand-bg text-brand-text">
      {/* Sidebar Navigation */}
      <div className="w-64 border-r overflow-y-auto" style={{ backgroundColor: 'var(--color-sidebar-bg)', borderColor: 'var(--color-sidebar-border)' }}>
        <div className="p-6">
          <h2 className="text-xl font-bold tracking-tight mb-6" style={{ color: 'var(--color-sidebar-text)' }}>Settings</h2>
          
          <nav className="space-y-1">
            {visibleTabs.map((tab) => {
              const isActive = location.pathname.startsWith(tab.path);
              return (
                <NavLink
                  key={tab.path}
                  to={tab.path}
                  className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors`}
                  style={{
                    backgroundColor: isActive ? 'var(--color-sidebar-active)' : 'transparent',
                    color: isActive ? 'var(--color-sidebar-text)' : 'var(--color-sidebar-text-muted)'
                  }}
                  onMouseEnter={(e) => {
                    if (!isActive) e.currentTarget.style.backgroundColor = 'var(--color-sidebar-active)';
                    if (!isActive) e.currentTarget.style.color = 'var(--color-sidebar-text)';
                  }}
                  onMouseLeave={(e) => {
                    if (!isActive) e.currentTarget.style.backgroundColor = 'transparent';
                    if (!isActive) e.currentTarget.style.color = 'var(--color-sidebar-text-muted)';
                  }}
                >
                  <tab.icon size={18} style={{ color: isActive ? 'var(--color-sidebar-text)' : 'var(--color-sidebar-text-muted)' }} />
                  {tab.label}
                </NavLink>
              );
            })}
          </nav>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 overflow-y-auto bg-brand-bg relative">
        <div className="max-w-4xl mx-auto px-10 py-10 pb-24">
          <Outlet />
        </div>
      </div>
    </div>
  );
};

export default SettingsLayout;
