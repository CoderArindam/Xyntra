import React, { useState, useEffect, useCallback } from 'react';
import { UserPlus, Mail, Search, Check, Loader2, X, Shield, UserCheck } from 'lucide-react';
import { getUsers, getBoardMembers, type User, type BoardMember } from '../../../services/usersApi';
import { adminAssignUser } from '../../../services/adminApi';
import { adminInviteUser } from '../../../services/invitationsApi';

interface AddMemberModalProps {
  isOpen: boolean;
  onClose: () => void;
  boardId: number;
  onMemberAdded?: () => void;
}

export const AddMemberModal: React.FC<AddMemberModalProps> = ({
  isOpen,
  onClose,
  boardId,
  onMemberAdded,
}) => {
  const [activeTab, setActiveTab] = useState<'existing' | 'invite'>('existing');

  // Existing Users State
  const [orgUsers, setOrgUsers] = useState<User[]>([]);
  const [boardMembers, setBoardMembers] = useState<BoardMember[]>([]);
  const [search, setSearch] = useState('');
  const [selectedUserId, setSelectedUserId] = useState<number | null>(null);
  const [permission, setPermission] = useState<string>('EDITOR');

  // Invite Form State
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole] = useState('MEMBER');

  // Status States
  const [isLoadingUsers, setIsLoadingUsers] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    if (!isOpen || !boardId) return;
    setIsLoadingUsers(true);
    setErrorMessage(null);
    setSuccessMessage(null);
    try {
      const [allUsers, currentMembers] = await Promise.all([
        getUsers().catch(() => []),
        getBoardMembers(boardId).catch(() => []),
      ]);
      setOrgUsers(allUsers || []);
      setBoardMembers(currentMembers || []);
    } catch (err) {
      console.error('Failed to load user list for modal:', err);
    } finally {
      setIsLoadingUsers(false);
    }
  }, [isOpen, boardId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  if (!isOpen) return null;

  // Filter org users who are NOT yet assigned to this board
  const memberUserIds = new Set(boardMembers.map((m) => m.id));
  const availableUsers = orgUsers.filter(
    (u) =>
      !memberUserIds.has(u.id) &&
      ((u.first_name || '').toLowerCase().includes(search.toLowerCase()) ||
        (u.last_name || '').toLowerCase().includes(search.toLowerCase()) ||
        u.email.toLowerCase().includes(search.toLowerCase()))
  );

  const handleAddExistingUser = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedUserId || isSubmitting) return;

    setIsSubmitting(true);
    setErrorMessage(null);
    setSuccessMessage(null);

    try {
      await adminAssignUser(boardId, selectedUserId, permission);
      setSuccessMessage('Member successfully added to project board!');
      setSelectedUserId(null);
      await loadData();
      if (onMemberAdded) onMemberAdded();
      setTimeout(() => {
        setSuccessMessage(null);
      }, 2500);
    } catch (err: any) {
      console.error('Failed to assign user to board:', err);
      setErrorMessage(
        err.response?.data?.detail || 'Failed to add member to project board.'
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleInviteUser = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inviteEmail.trim() || isSubmitting) return;

    setIsSubmitting(true);
    setErrorMessage(null);
    setSuccessMessage(null);

    try {
      await adminInviteUser(inviteEmail.trim(), inviteRole);
      setSuccessMessage(`Invitation successfully sent to ${inviteEmail.trim()}!`);
      setInviteEmail('');
      if (onMemberAdded) onMemberAdded();
      setTimeout(() => {
        setSuccessMessage(null);
      }, 3000);
    } catch (err: any) {
      console.error('Failed to send invitation:', err);
      setErrorMessage(
        err.response?.data?.detail || 'Failed to send invitation email.'
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs animate-fade-in">
      <div
        className="w-full max-w-lg bg-brand-surface border border-brand-border rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-brand-border/80">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-brand-primary/10 border border-brand-primary/20 flex items-center justify-center text-brand-primary">
              <UserPlus className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-brand-text">Add Board Member</h2>
              <p className="text-xs text-brand-text-muted">
                Assign team members to this board or invite new users
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-2 rounded-xl text-brand-text-muted hover:text-brand-text hover:bg-brand-surface-low transition-colors cursor-pointer"
            aria-label="Close modal"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tab Selector */}
        <div className="flex border-b border-brand-border px-6 pt-2 bg-brand-surface-low/30">
          <button
            onClick={() => setActiveTab('existing')}
            className={`flex-1 py-3 text-xs font-semibold border-b-2 transition-all flex items-center justify-center gap-2 cursor-pointer ${
              activeTab === 'existing'
                ? 'border-brand-primary text-brand-primary'
                : 'border-transparent text-brand-text-muted hover:text-brand-text'
            }`}
          >
            <UserCheck className="w-4 h-4" /> Organization Users
          </button>

          <button
            onClick={() => setActiveTab('invite')}
            className={`flex-1 py-3 text-xs font-semibold border-b-2 transition-all flex items-center justify-center gap-2 cursor-pointer ${
              activeTab === 'invite'
                ? 'border-brand-primary text-brand-primary'
                : 'border-transparent text-brand-text-muted hover:text-brand-text'
            }`}
          >
            <Mail className="w-4 h-4" /> Invite via Email
          </button>
        </div>

        {/* Status Alerts */}
        {successMessage && (
          <div className="mx-6 mt-4 p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-600 dark:text-emerald-400 text-xs font-semibold flex items-center gap-2">
            <Check className="w-4 h-4 shrink-0" /> {successMessage}
          </div>
        )}

        {errorMessage && (
          <div className="mx-6 mt-4 p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-600 dark:text-red-400 text-xs font-semibold flex items-center gap-2">
            <X className="w-4 h-4 shrink-0" /> {errorMessage}
          </div>
        )}

        {/* Body Content */}
        <div className="p-6 overflow-y-auto space-y-4 flex-1">
          {activeTab === 'existing' ? (
            <form onSubmit={handleAddExistingUser} className="space-y-4">
              {/* Search Bar */}
              <div className="relative">
                <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-brand-outline" />
                <input
                  type="text"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Search org members by name or email..."
                  className="w-full pl-9 pr-4 py-2 text-xs bg-brand-surface-low border border-brand-border rounded-xl text-brand-text outline-none focus:border-brand-primary transition-colors placeholder:text-brand-text-muted"
                />
              </div>

              {/* User Selection List */}
              <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
                {isLoadingUsers ? (
                  <div className="py-8 text-center text-brand-text-muted flex justify-center">
                    <Loader2 className="w-6 h-6 animate-spin text-brand-primary opacity-60" />
                  </div>
                ) : availableUsers.length === 0 ? (
                  <div className="p-4 text-center border border-dashed border-brand-border rounded-xl text-xs text-brand-text-muted">
                    {search
                      ? 'No matching organization members found.'
                      : 'All organization members are already added to this board.'}
                  </div>
                ) : (
                  availableUsers.map((u) => {
                    const fullName = [u.first_name, u.last_name].filter(Boolean).join(' ') || u.email;
                    const isSelected = selectedUserId === u.id;
                    return (
                      <button
                        key={u.id}
                        type="button"
                        onClick={() => setSelectedUserId(u.id)}
                        className={`w-full flex items-center justify-between p-3 rounded-xl border text-left transition-all cursor-pointer ${
                          isSelected
                            ? 'bg-brand-primary/10 border-brand-primary text-brand-primary font-bold'
                            : 'bg-brand-surface-low/50 hover:bg-brand-surface-low border-brand-border text-brand-text'
                        }`}
                      >
                        <div className="min-w-0">
                          <p className="text-xs font-semibold truncate">{fullName}</p>
                          <p className="text-[11px] text-brand-text-muted truncate">{u.email}</p>
                        </div>
                        {isSelected && <Check className="w-4 h-4 text-brand-primary shrink-0" />}
                      </button>
                    );
                  })
                )}
              </div>

              {/* Permission Selector */}
              <div className="space-y-1.5 pt-2">
                <label className="text-xs font-semibold text-brand-text flex items-center gap-1.5">
                  <Shield className="w-3.5 h-3.5 text-brand-primary" /> Board Access Permission
                </label>
                <select
                  value={permission}
                  onChange={(e) => setPermission(e.target.value)}
                  className="w-full px-3 py-2 text-xs bg-brand-surface-low border border-brand-border rounded-xl text-brand-text outline-none focus:border-brand-primary"
                >
                  <option value="EDITOR">Editor (Can edit & move tasks)</option>
                  <option value="VIEWER">Viewer (Read-only view)</option>
                </select>
              </div>

              {/* Submit Button */}
              <div className="pt-2">
                <button
                  type="submit"
                  disabled={!selectedUserId || isSubmitting}
                  className="w-full py-2.5 rounded-xl bg-brand-primary hover:bg-brand-primary-hover text-white text-xs font-semibold transition-all shadow-xs flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
                >
                  {isSubmitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <UserPlus className="w-4 h-4" />}
                  Add to Board
                </button>
              </div>
            </form>
          ) : (
            <form onSubmit={handleInviteUser} className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-brand-text">User Email Address</label>
                <input
                  type="email"
                  required
                  value={inviteEmail}
                  onChange={(e) => setInviteEmail(e.target.value)}
                  placeholder="colleague@company.com"
                  className="w-full px-3 py-2 text-xs bg-brand-surface-low border border-brand-border rounded-xl text-brand-text outline-none focus:border-brand-primary transition-colors placeholder:text-brand-text-muted"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-brand-text">Organization Role</label>
                <select
                  value={inviteRole}
                  onChange={(e) => setInviteRole(e.target.value)}
                  className="w-full px-3 py-2 text-xs bg-brand-surface-low border border-brand-border rounded-xl text-brand-text outline-none focus:border-brand-primary"
                >
                  <option value="MEMBER">Member (Standard member access)</option>
                  <option value="MANAGER">Manager (Full project management access)</option>
                </select>
              </div>

              <div className="pt-2">
                <button
                  type="submit"
                  disabled={!inviteEmail.trim() || isSubmitting}
                  className="w-full py-2.5 rounded-xl bg-brand-primary hover:bg-brand-primary-hover text-white text-xs font-semibold transition-all shadow-xs flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
                >
                  {isSubmitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Mail className="w-4 h-4" />}
                  Send Invitation
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
};

export default AddMemberModal;
