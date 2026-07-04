import React, { useEffect } from 'react';
import { useAdminStore } from '../../store/adminStore';
import { Users, FolderKanban } from 'lucide-react';
import { Link } from 'react-router-dom';

const AdminDashboard: React.FC = () => {
  const { users, boards, fetchUsers, fetchBoards, isFetchingUsers, isFetchingBoards } = useAdminStore();

  useEffect(() => {
    fetchUsers();
    fetchBoards();
  }, [fetchUsers, fetchBoards]);

  return (
    <div className="flex flex-col gap-8 h-full max-w-5xl mx-auto">
      <header className="flex flex-col gap-2">
        <h1 className="text-3xl font-bold tracking-tight text-brand-text">Platform Overview</h1>
        <p className="text-brand-text-muted">Manage users, roles, and board access levels across the platform.</p>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {/* Users Card */}
        <div className="bg-brand-bg border border-brand-border rounded-2xl p-6 shadow-sm flex flex-col gap-6 hover:shadow-md hover:border-brand-primary/30 transition-all duration-300 group">
          <div className="flex items-center gap-4">
            <div className="bg-brand-primary/10 p-4 rounded-xl text-brand-primary group-hover:scale-110 group-hover:bg-brand-primary/20 transition-all duration-300">
              <Users size={28} />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-brand-text">Total Users</h2>
              <p className="text-brand-text-muted text-sm">Registered accounts</p>
            </div>
          </div>
          <div className="text-5xl font-bold text-brand-text tracking-tight">
            {isFetchingUsers ? (
              <div className="h-12 w-20 bg-brand-surface-low animate-pulse rounded-lg"></div>
            ) : (
              users.length
            )}
          </div>
          <div className="mt-auto pt-4 border-t border-brand-border">
            <Link 
              to="/admin/users" 
              className="text-sm font-medium text-brand-primary hover:text-brand-primary-hover flex items-center gap-1 group/link"
            >
              Manage Users 
              <span className="group-hover/link:translate-x-1 transition-transform">&rarr;</span>
            </Link>
          </div>
        </div>

        {/* Boards Card */}
        <div className="bg-brand-bg border border-brand-border rounded-2xl p-6 shadow-sm flex flex-col gap-6 hover:shadow-md hover:border-purple-500/30 transition-all duration-300 group">
          <div className="flex items-center gap-4">
            <div className="bg-purple-500/10 p-4 rounded-xl text-purple-500 group-hover:scale-110 group-hover:bg-purple-500/20 transition-all duration-300">
              <FolderKanban size={28} />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-brand-text">Total Boards</h2>
              <p className="text-brand-text-muted text-sm">Active projects</p>
            </div>
          </div>
          <div className="text-5xl font-bold text-brand-text tracking-tight">
            {isFetchingBoards ? (
              <div className="h-12 w-20 bg-brand-surface-low animate-pulse rounded-lg"></div>
            ) : (
              boards.length
            )}
          </div>
          <div className="mt-auto pt-4 border-t border-brand-border">
            <Link 
              to="/admin/boards" 
              className="text-sm font-medium text-purple-500 hover:text-purple-600 flex items-center gap-1 group/link"
            >
              Manage Permissions 
              <span className="group-hover/link:translate-x-1 transition-transform">&rarr;</span>
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AdminDashboard;
