import React, { useEffect, useState } from 'react';
import { useAdminStore } from '../../store/adminStore';
import { useAuthStore } from '../../store/authStore';
import { Trash2, Loader2, Users, Mail, UserX } from 'lucide-react';
import { UserAvatar } from '../../components/common/UserAvatar';
import { formatUserName } from '../../utils/userHelpers';
import { usePageTitle } from '../../hooks/usePageTitle';
import { useOrganizationStore } from '../../store/organizationStore';
import { InviteUserModal } from './modals/InviteUserModal';
import { RevokeInvitationModal } from './modals/RevokeInvitationModal';
import { DeleteUserModal } from './modals/DeleteUserModal';

const UsersManagement: React.FC = () => {
  const { 
    users, 
    invitations,
    fetchUsers, 
    fetchInvitations,
    isFetchingUsers, 
    isFetchingInvitations,
    inviteUser, 
    revokeInvitation,
    isInvitingUser, 
    isRevokingInvitation,
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
  const [invitationToRevoke, setInvitationToRevoke] = useState<{ id: number; email: string } | null>(null);

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

  const confirmRevokeInvitation = async () => {
    if (!invitationToRevoke) return;
    await revokeInvitation(invitationToRevoke.id);
    setInvitationToRevoke(null);
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
          className="bg-brand-primary hover:bg-brand-primary-hover text-white px-4 py-2 rounded-lg font-medium text-sm flex items-center gap-2 transition cursor-pointer"
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
                            className="p-2 text-brand-text-muted hover:text-red-500 hover:bg-red-500/10 rounded-lg transition-colors disabled:opacity-30 disabled:hover:bg-transparent disabled:hover:text-brand-text-muted cursor-pointer"
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
                  <th className="px-6 py-4 text-center">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-brand-border">
                {isFetchingInvitations ? (
                  <tr>
                    <td colSpan={5} className="p-12 text-center text-brand-text-muted">
                      <Loader2 className="animate-spin mx-auto mb-2" size={24} />
                      <p className="text-sm">Loading invitations...</p>
                    </td>
                  </tr>
                ) : invitations.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="p-12 text-center text-brand-text-muted">
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
                            Expired / Revoked
                          </span>
                        )}
                      </td>
                      <td className="px-6 py-4 text-brand-text-muted text-sm">
                        {new Date(inv.created_at).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })}
                      </td>
                      <td className="px-6 py-4 text-center">
                        {inv.is_pending ? (
                          <button
                            onClick={() => setInvitationToRevoke({ id: inv.id, email: inv.email })}
                            className="px-3 py-1.5 text-xs font-semibold rounded-lg bg-red-500/10 text-red-500 hover:bg-red-500/20 border border-red-500/20 transition-colors cursor-pointer flex items-center gap-1 mx-auto"
                            title="Revoke invitation link"
                          >
                            <UserX size={14} /> Revoke
                          </button>
                        ) : (
                          <span className="text-xs text-brand-text-muted italic">—</span>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <InviteUserModal
        isOpen={isInviteModalOpen}
        onClose={closeInviteModal}
        onSubmit={handleInviteUser}
        email={newEmail}
        onEmailChange={setNewEmail}
        role={newRole}
        onRoleChange={setNewRole}
        inviteError={inviteError}
        isInvitingUser={isInvitingUser}
        profileName={profile?.name}
        profileLogoUrl={profile?.logo_url}
      />

      <RevokeInvitationModal
        invitation={invitationToRevoke}
        onClose={() => setInvitationToRevoke(null)}
        onConfirm={confirmRevokeInvitation}
        isRevoking={isRevokingInvitation}
      />

      <DeleteUserModal
        userToDelete={userToDelete}
        onClose={() => setUserToDelete(null)}
        onConfirm={confirmDelete}
      />
    </div>
  );
};

export default UsersManagement;

