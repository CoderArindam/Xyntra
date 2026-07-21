import React, { useEffect, useState } from 'react';
import { useAdminStore } from '../../store/adminStore';
import { useAuthStore } from '../../store/authStore';
import { Trash2, Loader2, X, AlertTriangle, Users, Mail } from 'lucide-react';
import { UserAvatar } from '../../components/common/UserAvatar';
import { formatUserName } from '../../utils/userHelpers';
import { usePageTitle } from '../../hooks/usePageTitle';
import WorkspaceLogo from '../../components/common/WorkspaceLogo';
import { useOrganizationStore } from '../../store/organizationStore';

const UsersManagement: React.FC = () => {
  const { 
    users, 
    invitations,
    fetchUsers, 
    fetchInvitations,
    isFetchingUsers, 
    isFetchingInvitations,
    inviteUser, 
    isInvitingUser, 
    updateUserRole, 
    deleteUser 
  } = useAdminStore();
  
  const { user: currentUser } = useAuthStore();
  const { profile } = useOrganizationStore();

  usePageTitle("Users & Invitations");

  const [isInviteModalOpen, setIsInviteModalOpen] = useState(false);
  const [newEmail, setNewEmail] = useState('');
  const [newRole, setNewRole] = useState('MEMBER');
  const [inviteError, setInviteError] = useState<string | null>(null);
  
  const [userToDelete, setUserToDelete] = useState<number | null>(null);

  useEffect(() => {
    fetchUsers();
    fetchInvitations();
  }, [fetchUsers, fetchInvitations]);

  const closeInviteModal = () => {
    setIsInviteModalOpen(false);
    setInviteError(null);
  };

  const handleInviteUser = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newEmail) return;
    setInviteError(null);
    try {
      await inviteUser(newEmail, newRole);
      closeInviteModal();
      setNewEmail('');
      setNewRole('MEMBER');
    } catch (error: any) {
      setInviteError(error?.message || 'Failed to invite user');
    }
  };

  const handleRoleChange = async (userId: number, newRole: string) => {
    await updateUserRole(userId, newRole);
  };

  const confirmDelete = async () => {
    if (!userToDelete) return;
    await deleteUser(userToDelete);
    setUserToDelete(null);
  };

  return (
    <div className="flex flex-col h-full gap-6 overflow-y-auto pb-8">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-brand-text">Users & Invitations</h1>
          <p className="text-brand-text-muted text-sm mt-1">Manage platform users and pending invitations.</p>
        </div>
        <button
          onClick={() => setIsInviteModalOpen(true)}
          className="bg-brand-primary hover:bg-brand-primary-hover text-white px-4 py-2 rounded-lg font-medium text-sm flex items-center gap-2 transition"
        >
          <Mail size={16} />
          Invite User
        </button>
      </header>

      {/* Active Users Table */}
      <div>
        <h2 className="text-lg font-semibold text-brand-text mb-3">Active Users</h2>
        <div className="bg-brand-bg border border-brand-border rounded-2xl overflow-hidden flex flex-col shadow-sm">
          <div className="overflow-x-auto flex-1">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-brand-border bg-brand-surface text-brand-text-muted text-xs uppercase tracking-wider font-semibold">
                  <th className="px-6 py-4">User</th>
                  <th className="px-6 py-4">Role</th>
                  <th className="px-6 py-4">Joined</th>
                  <th className="px-6 py-4 text-center">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-brand-border">
                {isFetchingUsers ? (
                  <tr>
                    <td colSpan={4} className="p-12 text-center text-brand-text-muted">
                      <Loader2 className="animate-spin mx-auto mb-2" size={24} />
                      <p className="text-sm">Loading users...</p>
                    </td>
                  </tr>
                ) : users.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="p-12 text-center text-brand-text-muted">
                      <Users className="mx-auto mb-3 opacity-20" size={48} />
                      <p>No active users found.</p>
                    </td>
                  </tr>
                ) : (
                  users.map(u => (
                    <tr key={u.id} className="hover:bg-brand-surface/50 transition-colors group">
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-3">
                          <UserAvatar user={u} size="md" />
                          <div className="font-medium text-brand-text text-sm">{formatUserName(u)}</div>
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <select
                          value={u.role}
                          onChange={(e) => handleRoleChange(u.id, e.target.value)}
                          disabled={u.id === currentUser?.id}
                          className={`text-xs font-semibold px-3 py-1.5 rounded-full border outline-none cursor-pointer disabled:opacity-50 transition-colors appearance-none ${
                            u.role === 'SUPER_ADMIN' 
                              ? 'bg-purple-500/10 text-purple-500 border-purple-500/20 hover:border-purple-500/50' 
                              : 'bg-brand-surface text-brand-text-muted border-brand-border hover:border-brand-text-muted'
                          }`}
                        >
                          <option value="MEMBER" className="text-black">MEMBER</option>
                          <option value="MANAGER" className="text-black">MANAGER</option>
                          <option value="SUPER_ADMIN" className="text-black">SUPER_ADMIN</option>
                        </select>
                      </td>
                      <td className="px-6 py-4 text-brand-text-muted text-sm">
                        {new Date(u.created_at).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })}
                      </td>
                      <td className="px-6 py-4 text-center">
                        <div className="flex justify-center">
                          <button
                            onClick={() => setUserToDelete(u.id)}
                            disabled={u.id === currentUser?.id}
                            className="p-2 text-brand-text-muted hover:text-red-500 hover:bg-red-500/10 rounded-lg transition-colors disabled:opacity-30 disabled:hover:bg-transparent disabled:hover:text-brand-text-muted"
                            title={u.id === currentUser?.id ? "Cannot delete yourself" : "Delete user"}
                          >
                            <Trash2 size={18} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Invitations Table */}
      <div>
        <h2 className="text-lg font-semibold text-brand-text mb-3">Pending Invitations</h2>
        <div className="bg-brand-bg border border-brand-border rounded-2xl overflow-hidden flex flex-col shadow-sm">
          <div className="overflow-x-auto flex-1">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-brand-border bg-brand-surface text-brand-text-muted text-xs uppercase tracking-wider font-semibold">
                  <th className="px-6 py-4">Email</th>
                  <th className="px-6 py-4">Role</th>
                  <th className="px-6 py-4">Status</th>
                  <th className="px-6 py-4">Sent At</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-brand-border">
                {isFetchingInvitations ? (
                  <tr>
                    <td colSpan={4} className="p-12 text-center text-brand-text-muted">
                      <Loader2 className="animate-spin mx-auto mb-2" size={24} />
                      <p className="text-sm">Loading invitations...</p>
                    </td>
                  </tr>
                ) : invitations.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="p-12 text-center text-brand-text-muted">
                      <Mail className="mx-auto mb-3 opacity-20" size={48} />
                      <p>No invitations found.</p>
                    </td>
                  </tr>
                ) : (
                  invitations.map(inv => (
                    <tr key={inv.id} className="hover:bg-brand-surface/50 transition-colors group">
                      <td className="px-6 py-4">
                        <div className="font-medium text-brand-text text-sm">{inv.email}</div>
                      </td>
                      <td className="px-6 py-4">
                        <span className="text-xs font-semibold px-3 py-1.5 rounded-full border bg-brand-surface text-brand-text-muted border-brand-border">
                          {inv.role}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        {inv.is_pending ? (
                          <span className="text-xs font-semibold px-3 py-1.5 rounded-full border bg-yellow-500/10 text-yellow-500 border-yellow-500/20">
                            Pending
                          </span>
                        ) : inv.accepted_at ? (
                          <span className="text-xs font-semibold px-3 py-1.5 rounded-full border bg-green-500/10 text-green-500 border-green-500/20">
                            Accepted
                          </span>
                        ) : (
                          <span className="text-xs font-semibold px-3 py-1.5 rounded-full border bg-red-500/10 text-red-500 border-red-500/20">
                            Expired
                          </span>
                        )}
                      </td>
                      <td className="px-6 py-4 text-brand-text-muted text-sm">
                        {new Date(inv.created_at).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Invite Modal */}
      {isInviteModalOpen && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={closeInviteModal} />
          <div className="bg-brand-surface border border-brand-border rounded-2xl shadow-2xl w-full max-w-md overflow-hidden relative z-10 animate-in fade-in zoom-in-95 duration-200">
            <div className="flex items-center justify-between p-6 border-b border-brand-border">
              <h2 className="text-xl font-bold text-brand-text">Invite User</h2>
              <button 
                onClick={closeInviteModal}
                className="text-brand-text-muted hover:text-brand-text bg-brand-surface-low hover:bg-brand-border p-2 rounded-full transition-colors"
              >
                <X size={20} />
              </button>
            </div>
            
            <form onSubmit={handleInviteUser} className="p-6 flex flex-col gap-5">
              <div className="flex flex-col items-center text-center mb-2">
                <WorkspaceLogo name={profile?.name} logoUrl={profile?.logo_url} size="xl" variant="rounded" className="mb-3 shadow-sm" />
                <h3 className="text-lg font-semibold text-brand-text">{profile?.name || 'Workspace'}</h3>
                {newEmail ? (
                  <p className="text-sm text-brand-text-muted mt-1">
                    You're inviting <span className="font-medium text-brand-text">{newEmail}</span> to {profile?.name || 'Workspace'} as <span className="font-medium text-brand-text capitalize">{newRole.toLowerCase()}</span>
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
                  value={newEmail}
                  onChange={(e) => setNewEmail(e.target.value)}
                  placeholder="user@example.com"
                  className="bg-brand-bg border border-brand-border rounded-xl px-4 py-3 text-brand-text text-sm outline-none focus:border-brand-primary focus:ring-1 focus:ring-brand-primary transition-shadow"
                  required
                />
              </div>
              <div className="flex flex-col gap-2">
                <label className="text-sm font-semibold text-brand-text">Role</label>
                <select
                  value={newRole}
                  onChange={(e) => setNewRole(e.target.value)}
                  className="bg-brand-bg border border-brand-border rounded-xl px-4 py-3 text-brand-text text-sm outline-none focus:border-brand-primary focus:ring-1 focus:ring-brand-primary transition-shadow appearance-none"
                >
                  <option value="MEMBER" className="text-black">Member</option>
                  <option value="MANAGER" className="text-black">Manager</option>
                </select>
                
                <div className="mt-2 p-3 bg-brand-surface-low border border-brand-border rounded-lg text-sm text-brand-text-muted">
                  <p className="font-medium text-brand-text mb-1">Permissions Preview</p>
                  {newRole === 'MANAGER' ? (
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
                  onClick={closeInviteModal}
                  className="px-5 py-2.5 rounded-xl text-sm font-medium text-brand-text-muted hover:text-brand-text hover:bg-brand-surface-low transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isInvitingUser || !newEmail}
                  className="px-5 py-2.5 rounded-xl text-sm font-medium bg-brand-primary hover:bg-brand-primary-hover text-white transition-colors flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed shadow-sm"
                >
                  {isInvitingUser ? <Loader2 size={16} className="animate-spin" /> : null}
                  Send Invitation
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete Confirmation */}
      {userToDelete && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={() => setUserToDelete(null)} />
          <div className="bg-brand-surface border border-brand-border rounded-2xl shadow-2xl w-full max-w-sm p-6 text-center flex flex-col items-center relative z-10 animate-in fade-in zoom-in-95 duration-200">
            <div className="w-14 h-14 rounded-full bg-red-500/10 text-red-500 flex items-center justify-center mb-5 ring-4 ring-red-500/5">
              <AlertTriangle size={28} />
            </div>
            <h2 className="text-xl font-bold text-brand-text mb-2">Delete User?</h2>
            <p className="text-sm text-brand-text-muted mb-8 leading-relaxed">
              This action cannot be undone. This will permanently delete the user and their associated data from the platform.
            </p>
            <div className="flex w-full gap-3">
              <button
                onClick={() => setUserToDelete(null)}
                className="flex-1 px-4 py-2.5 rounded-xl border border-brand-border text-sm font-medium hover:bg-brand-surface-low transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={confirmDelete}
                className="flex-1 px-4 py-2.5 rounded-xl bg-red-500 hover:bg-red-600 text-white text-sm font-medium transition-colors shadow-sm"
              >
                Yes, delete user
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default UsersManagement;
