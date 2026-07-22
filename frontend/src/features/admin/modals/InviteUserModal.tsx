import React from 'react';
import { X, AlertTriangle, Loader2 } from 'lucide-react';
import WorkspaceLogo from '../../../components/common/WorkspaceLogo';

interface InviteUserModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (e: React.FormEvent) => void;
  email: string;
  onEmailChange: (val: string) => void;
  role: string;
  onRoleChange: (val: string) => void;
  inviteError: string | null;
  isInvitingUser: boolean;
  profileName?: string;
  profileLogoUrl?: string | null;
}

export const InviteUserModal: React.FC<InviteUserModalProps> = ({
  isOpen,
  onClose,
  onSubmit,
  email,
  onEmailChange,
  role,
  onRoleChange,
  inviteError,
  isInvitingUser,
  profileName,
  profileLogoUrl,
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <div className="bg-brand-surface border border-brand-border rounded-2xl shadow-2xl w-full max-w-md overflow-hidden relative z-10 animate-in fade-in zoom-in-95 duration-200">
        <div className="flex items-center justify-between p-6 border-b border-brand-border">
          <h2 className="text-xl font-bold text-brand-text">Invite User</h2>
          <button 
            onClick={onClose}
            className="text-brand-text-muted hover:text-brand-text bg-brand-surface-low hover:bg-brand-border p-2 rounded-full transition-colors cursor-pointer"
          >
            <X size={20} />
          </button>
        </div>
        
        <form onSubmit={onSubmit} className="p-6 flex flex-col gap-5">
          <div className="flex flex-col items-center text-center mb-2">
            <WorkspaceLogo name={profileName} logoUrl={profileLogoUrl} size="xl" variant="rounded" className="mb-3 shadow-sm" />
            <h3 className="text-lg font-semibold text-brand-text">{profileName || 'Workspace'}</h3>
            {email ? (
              <p className="text-sm text-brand-text-muted mt-1">
                You're inviting <span className="font-medium text-brand-text">{email}</span> to {profileName || 'Workspace'} as <span className="font-medium text-brand-text capitalize">{role.toLowerCase()}</span>
              </p>
            ) : (
              <p className="text-sm text-brand-text-muted mt-1">Invite a new member to join your workspace</p>
            )}
          </div>

          {inviteError && (
            <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-xl text-sm text-red-500 flex items-center gap-2">
              <AlertTriangle size={16} className="shrink-0" />
              <span>{inviteError}</span>
            </div>
          )}

          <div className="flex flex-col gap-2">
            <label className="text-sm font-semibold text-brand-text">Email Address</label>
            <input
              type="email"
              value={email}
              onChange={(e) => onEmailChange(e.target.value)}
              placeholder="user@example.com"
              className="bg-brand-bg border border-brand-border rounded-xl px-4 py-3 text-brand-text text-sm outline-none focus:border-brand-primary focus:ring-1 focus:ring-brand-primary transition-shadow"
              required
            />
          </div>
          <div className="flex flex-col gap-2">
            <label className="text-sm font-semibold text-brand-text">Role</label>
            <select
              value={role}
              onChange={(e) => onRoleChange(e.target.value)}
              className="bg-brand-bg border border-brand-border rounded-xl px-4 py-3 text-brand-text text-sm outline-none focus:border-brand-primary focus:ring-1 focus:ring-brand-primary transition-shadow appearance-none cursor-pointer"
            >
              <option value="MEMBER" className="text-black">Member</option>
              <option value="MANAGER" className="text-black">Manager</option>
            </select>
            
            <div className="mt-2 p-3 bg-brand-surface-low border border-brand-border rounded-lg text-sm text-brand-text-muted">
              <p className="font-medium text-brand-text mb-1">Permissions Preview</p>
              {role === 'MANAGER' ? (
                <ul className="list-disc list-inside space-y-1">
                  <li>Can create projects</li>
                  <li>Can invite members</li>
                  <li>Can edit tasks</li>
                </ul>
              ) : (
                <ul className="list-disc list-inside space-y-1">
                  <li>Can view assigned projects</li>
                  <li>Can update assigned tasks</li>
                  <li>Cannot invite members</li>
                </ul>
              )}
            </div>
          </div>

          <div className="mt-2 flex gap-3 justify-end">
            <button
              type="button"
              onClick={onClose}
              className="px-5 py-2.5 rounded-xl text-sm font-medium text-brand-text-muted hover:text-brand-text hover:bg-brand-surface-low transition-colors cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isInvitingUser || !email}
              className="px-5 py-2.5 rounded-xl text-sm font-medium bg-brand-primary hover:bg-brand-primary-hover text-white transition-colors flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed shadow-sm cursor-pointer"
            >
              {isInvitingUser ? <Loader2 size={16} className="animate-spin" /> : null}
              Send Invitation
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
