import React from 'react';
import { AlertTriangle } from 'lucide-react';

interface DeleteUserModalProps {
  userToDelete: number | null;
  onClose: () => void;
  onConfirm: () => void;
}

export const DeleteUserModal: React.FC<DeleteUserModalProps> = ({
  userToDelete,
  onClose,
  onConfirm,
}) => {
  if (!userToDelete) return null;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
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
            onClick={onClose}
            className="flex-1 px-4 py-2.5 rounded-xl border border-brand-border text-sm font-medium hover:bg-brand-surface-low transition-colors cursor-pointer"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            className="flex-1 px-4 py-2.5 rounded-xl bg-red-500 hover:bg-red-600 text-white text-sm font-medium transition-colors shadow-sm cursor-pointer"
          >
            Yes, delete user
          </button>
        </div>
      </div>
    </div>
  );
};
