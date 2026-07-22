import React from 'react';
import { UserX, Loader2 } from 'lucide-react';

interface RevokeInvitationModalProps {
  invitation: { id: number; email: string } | null;
  onClose: () => void;
  onConfirm: () => void;
  isRevoking: boolean;
}

export const RevokeInvitationModal: React.FC<RevokeInvitationModalProps> = ({
  invitation,
  onClose,
  onConfirm,
  isRevoking,
}) => {
  if (!invitation) return null;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <div className="bg-brand-surface border border-brand-border rounded-2xl shadow-2xl w-full max-w-sm p-6 text-center flex flex-col items-center relative z-10 animate-in fade-in zoom-in-95 duration-200">
        <div className="w-14 h-14 rounded-full bg-red-500/10 text-red-500 flex items-center justify-center mb-5 ring-4 ring-red-500/5">
          <UserX size={28} />
        </div>
        <h2 className="text-xl font-bold text-brand-text mb-2">Revoke Invitation?</h2>
        <p className="text-sm text-brand-text-muted mb-8 leading-relaxed">
          Are you sure you want to revoke the pending invitation for <span className="font-semibold text-brand-text">{invitation.email}</span>? The invitation token will be permanently deleted and the user will not be able to activate an account with that link.
        </p>
        <div className="flex w-full gap-3">
          <button
            onClick={onClose}
            disabled={isRevoking}
            className="flex-1 px-4 py-2.5 rounded-xl border border-brand-border text-sm font-medium hover:bg-brand-surface-low transition-colors cursor-pointer"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            disabled={isRevoking}
            className="flex-1 px-4 py-2.5 rounded-xl bg-red-500 hover:bg-red-600 text-white text-sm font-semibold transition-colors shadow-sm flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
          >
            {isRevoking ? <Loader2 size={16} className="animate-spin" /> : null}
            Revoke Invitation
          </button>
        </div>
      </div>
    </div>
  );
};
