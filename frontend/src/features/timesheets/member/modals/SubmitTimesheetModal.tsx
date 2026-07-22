import React from 'react';
import { ShieldCheck, Loader2 } from 'lucide-react';
import { type EligibleApprover } from '../../../../services/timesheetAdminService';
import { Button } from '../../../../components/ui/Button';
import { Modal } from '../../../../components/common/Modal';

interface SubmitTimesheetModalProps {
  isOpen: boolean;
  onClose: () => void;
  eligibleApprovers: EligibleApprover[];
  loadingApprovers: boolean;
  selectedApproverId: string;
  onApproverChange: (id: string) => void;
  memberNote: string;
  onNoteChange: (val: string) => void;
  isActionLoading: boolean;
  onConfirm: () => void;
}

export const SubmitTimesheetModal: React.FC<SubmitTimesheetModalProps> = ({
  isOpen,
  onClose,
  eligibleApprovers,
  loadingApprovers,
  selectedApproverId,
  onApproverChange,
  memberNote,
  onNoteChange,
  isActionLoading,
  onConfirm,
}) => (
  <Modal isOpen={isOpen} onClose={onClose} title="Submit Timesheet for Review">
    <div className="space-y-4">
      <p className="text-xs text-brand-text-muted">
        Once submitted, your timesheet will be sent for review and manager approval. You can recall it anytime before approval.
      </p>

      <div className="p-3 bg-brand-surface border border-brand-border rounded-xl space-y-2.5">
        <div className="flex items-center justify-between">
          <label className="block text-xs font-semibold text-brand-text flex items-center gap-1.5">
            <ShieldCheck size={14} className="text-brand-primary" />
            Select Approver Manager
          </label>
          {loadingApprovers && (
            <span className="text-[11px] text-brand-text-muted flex items-center gap-1">
              <Loader2 size={10} className="animate-spin" /> Loading approvers...
            </span>
          )}
        </div>

        <div>
          <select
            value={selectedApproverId}
            onChange={(e) => onApproverChange(e.target.value)}
            className="w-full bg-brand-bg border border-brand-border rounded-lg p-2.5 text-xs text-brand-text focus:outline-none focus:border-brand-primary font-medium"
          >
            {eligibleApprovers.length === 0 ? (
              <option value="">No approvers configured in organization</option>
            ) : (
              eligibleApprovers.map((app) => (
                <option key={app.user_id} value={app.user_id}>
                  👤 {app.display_name} ({app.role}) — {app.email}
                </option>
              ))
            )}
          </select>
          <p className="text-[11px] text-brand-text-muted mt-1">
            Select a manager designated by your organization's Superadmin to review your timesheet.
          </p>
        </div>
      </div>

      <div>
        <label className="block text-xs font-medium text-brand-text-muted mb-1">
          Member Note (Optional)
        </label>
        <textarea
          rows={3}
          value={memberNote}
          onChange={(e) => onNoteChange(e.target.value)}
          placeholder="Add any context or comments for your reviewer..."
          className="w-full bg-brand-surface border border-brand-border rounded-lg p-2.5 text-xs text-brand-text focus:outline-none focus:border-brand-primary resize-none"
        />
      </div>

      <div className="flex justify-end gap-2 pt-2">
        <Button variant="ghost" size="sm" onClick={onClose}>
          Cancel
        </Button>
        <Button variant="primary" size="sm" onClick={onConfirm} disabled={isActionLoading}>
          {isActionLoading ? 'Submitting...' : 'Confirm Submission'}
        </Button>
      </div>
    </div>
  </Modal>
);
