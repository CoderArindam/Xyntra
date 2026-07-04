import React, { useState, useRef, useEffect } from "react";
import type { BoardMember } from "../api/usersApi";

interface AssigneeFilterProps {
  users: BoardMember[];
  selectedAssigneeId: number | null;
  onChange: (userId: number | null) => void;
  maxVisible?: number;
}

import { UserAvatar } from './common/UserAvatar';
import { formatUserName } from '../utils/userHelpers';



const AssigneeFilter: React.FC<AssigneeFilterProps> = ({
  users,
  selectedAssigneeId,
  onChange,
  maxVisible = 5,
}) => {
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const visible = users.slice(0, maxVisible);
  const overflow = users.slice(maxVisible);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setDropdownOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  return (
    <div className="flex items-center gap-2 px-8 py-2 border-b border-brand-border shrink-0 min-h-[44px]">
      <span className="text-xs text-brand-text-muted font-medium shrink-0 select-none mr-2">
        Assignee:
      </span>

      <div className="flex items-center gap-1.5">
        {/* "ALL" option */}
        <button
          onClick={() => onChange(null)}
          title="All Assignees"
          className={`w-8 h-8 rounded-full text-[10px] font-bold flex items-center justify-center shrink-0 transition-all duration-150 select-none border ${
            selectedAssigneeId === null
              ? "text-brand-primary border-transparent ring-2 ring-offset-1 ring-brand-primary bg-brand-primary/10 scale-105"
              : "text-brand-text-muted border-dashed border-brand-border bg-transparent hover:border-brand-primary hover:text-brand-primary"
          }`}
        >
          ALL
        </button>

        {/* Visible member avatars */}
        {visible.map((member) => {
          const active = selectedAssigneeId === member.id;
          return (
            <div
              key={member.id}
              title={formatUserName(member)}
              onClick={() => onChange(member.id)}
              className={`rounded-full transition-all duration-150 cursor-pointer ${
                active
                  ? "ring-2 ring-offset-1 ring-brand-primary scale-105 opacity-100"
                  : "opacity-60 hover:opacity-100"
              }`}
            >
              <UserAvatar user={member} size="md" className="border border-brand-border" />
            </div>
          );
        })}

        {/* +N overflow — opens dropdown with board-only members */}
        {overflow.length > 0 && (
          <div className="relative" ref={dropdownRef}>
            <button
              onClick={() => setDropdownOpen((o) => !o)}
              className={`w-8 h-8 rounded-full text-xs font-semibold border transition-all duration-150 select-none flex items-center justify-center ${
                dropdownOpen
                  ? "bg-brand-primary text-white border-brand-primary"
                  : "bg-brand-surface text-brand-text-muted border-brand-border hover:border-brand-primary hover:text-brand-text"
              }`}
            >
              +{overflow.length}
            </button>

            {dropdownOpen && (
              <div className="absolute top-10 left-0 z-50 w-52 bg-brand-surface border border-brand-border rounded-xl shadow-2xl py-1 overflow-hidden">
                {overflow.map((member) => {
                  const active = selectedAssigneeId === member.id;
                  return (
                    <button
                      key={member.id}
                      onClick={() => {
                        onChange(member.id);
                        setDropdownOpen(false);
                      }}
                      className={`w-full flex items-center gap-3 px-4 py-2.5 text-sm transition-colors hover:bg-brand-surface-low ${
                        active ? "text-brand-primary font-semibold" : "text-brand-text"
                      }`}
                    >
                      <UserAvatar user={member} size="sm" />
                      <span className="truncate flex-1 text-left">{formatUserName(member)}</span>
                      {active && <span className="text-brand-primary text-xs">✓</span>}
                    </button>
                  );
                })}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default AssigneeFilter;
