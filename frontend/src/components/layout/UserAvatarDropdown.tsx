import React, { useState, useRef, useEffect } from 'react';

import { useAuthStore } from '../../store/authStore';
import { UserAvatar } from '../common/UserAvatar';
import {
  
  
  LogOut,
  
  
  
} from 'lucide-react';
import { formatUserName } from '../../utils/userHelpers';

interface UserAvatarDropdownProps {
  isSidebarCollapsed?: boolean;
}

export const UserAvatarDropdown: React.FC<UserAvatarDropdownProps> = ({
  isSidebarCollapsed = false,
}) => {
  const { user, logout } = useAuthStore();
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    };

    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setIsOpen(false);
    };

    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
      document.addEventListener("keydown", handleEscape);
    }

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleEscape);
    };
  }, [isOpen]);

  const toggleDropdown = () => setIsOpen((prev) => !prev);
  const closeDropdown = () => setIsOpen(false);

  return (
    <div className="relative" ref={dropdownRef}>
      <UserAvatar
        user={user}
        size={isSidebarCollapsed ? "sm" : "md"}
        onClick={toggleDropdown}
      />

      {isOpen && (
        <div className="absolute left-0 bottom-full mb-2 w-64 bg-brand-surface rounded-xl shadow-xl border border-brand-border z-50 overflow-hidden animate-in fade-in slide-in-from-bottom-2 duration-150">
          {/* Header Info */}
          <div className="px-4 py-3 border-b border-brand-border bg-brand-surface-low">
            <p className="text-sm font-semibold text-brand-text truncate">
              {formatUserName(user)}
            </p>
            <p className="text-xs text-brand-text-muted truncate mt-0.5">
              {user?.email}
            </p>
          </div>

          <div>
            {/* <Link
              to="/settings/account"
              onClick={closeDropdown}
              className="flex items-center gap-3 px-4 py-2 text-sm text-brand-text hover:bg-brand-surface-low transition-colors"
            >
              <User size={16} className="text-brand-text-muted" />
              Profile
            </Link> */}
            {/* <Link
              to="/settings/account"
              onClick={closeDropdown}
              className="flex items-center gap-3 px-4 py-2 text-sm text-brand-text hover:bg-brand-surface-low transition-colors"
            >
              <Settings size={16} className="text-brand-text-muted" />
              Settings
            </Link> */}

            {/* {user?.role === 'SUPER_ADMIN' && (
              <Link 
                to="/settings/organization" 
                onClick={closeDropdown}
                className="flex items-center gap-3 px-4 py-2 text-sm text-brand-text hover:bg-brand-surface-low transition-colors"
              >
                <Building2 size={16} className="text-brand-text-muted" />
                My Organization
              </Link>
            )} */}
          </div>
          {/* 
          <div className="py-2 border-t border-brand-border">
            <Link 
              to="/settings/keyboard-shortcuts" 
              onClick={closeDropdown}
              className="flex items-center gap-3 px-4 py-2 text-sm text-brand-text hover:bg-brand-surface-low transition-colors"
            >
              <Command size={16} className="text-brand-text-muted" />
              Keyboard Shortcuts
            </Link>
            <a 
              href="#"
              onClick={(e) => { e.preventDefault(); closeDropdown(); }}
              className="flex items-center gap-3 px-4 py-2 text-sm text-brand-text hover:bg-brand-surface-low transition-colors"
            >
              <HelpCircle size={16} className="text-brand-text-muted" />
              Help
            </a>
          </div> */}

          <div className="py-2 border-t border-brand-border">
            <button
              onClick={() => {
                closeDropdown();
                logout();
              }}
              className="w-full flex items-center gap-3 px-4 py-2 text-sm text-brand-primary hover:bg-brand-surface-low transition-colors cursor-pointer"
            >
              <LogOut size={16} />
              Sign Out
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default UserAvatarDropdown;
