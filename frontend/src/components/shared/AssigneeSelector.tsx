import React, { useState, useEffect, useRef } from 'react';
import { UserRound, Search, ChevronDown, Check, UserX } from 'lucide-react';
import { type User } from '../../services/usersApi';
import { formatUserName } from '../../utils/userHelpers';
import { UserAvatar } from '../common/UserAvatar';

interface AssigneeSelectorProps {
  assigneeId: number | null | undefined;
  users: User[];
  onChange: (newAssigneeId: number | null) => void;
  disabled?: boolean;
}

const AssigneeSelector: React.FC<AssigneeSelectorProps> = ({ assigneeId, users = [], onChange, disabled }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState('');
  const containerRef = useRef<HTMLDivElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);

  const selectedUser = users.find((u) => u.id === assigneeId);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  useEffect(() => {
    if (isOpen && searchInputRef.current) {
      searchInputRef.current.focus();
    }
  }, [isOpen]);

  const filteredUsers = users.filter((u) => {
    if (!query.trim()) return true;
    const name = formatUserName(u).toLowerCase();
    const email = (u.email || '').toLowerCase();
    const search = query.toLowerCase().trim();
    return name.includes(search) || email.includes(search);
  });

  const handleSelect = (userId: number | null) => {
    onChange(userId);
    setIsOpen(false);
    setQuery('');
  };

  return (
    <div className="relative w-full" ref={containerRef}>
      {/* Trigger Button */}
      <button
        type="button"
        disabled={disabled}
        onClick={() => setIsOpen((prev) => !prev)}
        className={`flex items-center justify-between w-full px-3 py-2 text-sm bg-brand-surface border border-brand-border rounded-lg text-brand-text transition-all ${
          isOpen ? 'border-brand-primary ring-2 ring-brand-primary/20' : 'hover:border-brand-border-highlight'
        } ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
      >
        <div className="flex items-center gap-2 min-w-0">
          {selectedUser ? (
            <UserAvatar user={selectedUser} size="sm" />
          ) : (
            <UserRound size={16} className="text-brand-text-muted shrink-0" />
          )}

          <span className="truncate text-sm font-medium text-brand-text">
            {selectedUser ? formatUserName(selectedUser) : 'Unassigned'}
          </span>
        </div>

        <ChevronDown size={14} className={`text-brand-text-muted shrink-0 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {/* Dropdown Menu - 100% Solid Opacity */}
      {isOpen && !disabled && (
        <div className="absolute z-50 left-0 right-0 mt-1 max-h-72 overflow-y-auto rounded-lg border border-brand-border bg-brand-surface text-brand-text shadow-2xl p-1.5 flex flex-col gap-1 opacity-100">
          {/* Search Input Box */}
          <div className="relative p-1 border-b border-brand-border/60 mb-1">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-brand-text-muted" />
            <input
              ref={searchInputRef}
              type="text"
              className="w-full pl-8 pr-3 py-1.5 bg-brand-surface border border-brand-border rounded-md text-xs text-brand-text placeholder:text-brand-text-muted outline-none focus:border-brand-primary"
              placeholder="Search assignee by name or email..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </div>

          {/* Unassigned Option */}
          <div
            onClick={() => handleSelect(null)}
            className={`flex items-center justify-between p-2 rounded-md cursor-pointer text-xs transition-colors ${
              !assigneeId
                ? 'bg-brand-primary/10 text-brand-primary font-medium'
                : 'hover:bg-brand-surface-highlight text-brand-text'
            }`}
          >
            <div className="flex items-center gap-2">
              <UserX size={16} className="text-brand-text-muted" />
              <span>Unassigned</span>
            </div>
            {!assigneeId && <Check size={14} className="text-brand-primary" />}
          </div>

          {/* User List */}
          {filteredUsers.length === 0 ? (
            <div className="p-3 text-center text-xs text-brand-text-muted">No users match "{query}"</div>
          ) : (
            filteredUsers.map((u) => {
              const isSelected = u.id === assigneeId;
              return (
                <div
                  key={u.id}
                  onClick={() => handleSelect(u.id)}
                  className={`flex items-center justify-between p-2 rounded-md cursor-pointer text-xs transition-colors ${
                    isSelected
                      ? 'bg-brand-primary/10 text-brand-text font-medium border border-brand-primary/30'
                      : 'hover:bg-brand-surface-highlight text-brand-text'
                  }`}
                >
                  <div className="flex items-center gap-2.5 min-w-0">
                    <UserAvatar user={u} size="sm" />
                    <div className="flex flex-col min-w-0">
                      <span className="truncate font-medium text-brand-text">{formatUserName(u)}</span>
                      {u.email && <span className="truncate text-[10px] text-brand-text-muted">{u.email}</span>}
                    </div>
                  </div>

                  {isSelected && <Check size={14} className="text-brand-primary shrink-0 ml-2" />}
                </div>
              );
            })
          )}
        </div>
      )}
    </div>
  );
};

export default AssigneeSelector;
