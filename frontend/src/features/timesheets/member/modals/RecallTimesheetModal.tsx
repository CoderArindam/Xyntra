import React from 'react';
import { Button } from '../../../../components/ui/Button';
import { Input } from '../../../../components/ui/Input';
import { Modal } from '../../../../components/common/Modal';

interface RecallTimesheetModalProps {
  isOpen: boolean;
  onClose: () => void;
  recallReason: string;
  onReasonChange: (val: string) => void;
  isActionLoading: boolean;
  onConfirm: () => void;
}

export const RecallTimesheetModal: React.FC<RecallTimesheetModalProps> = ({
  isOpen,
  onClose,
  recallReason,
  onReasonChange,
  isActionLoading,
  onConfirm,
}) => (
  <Modal isOpen={isOpen} onClose={onClose} title="Recall Timesheet to Draft">
    <div className="space-y-4">
      <p className="text-xs text-brand-text-muted">
        Recalling will revert your timesheet status to DRAFT so you can make modifications.
      </p>

      <div>
        <Input
          label="Reason for Recall *"
          placeholder="e.g. Correcting logged hours for Tuesday..."
          value={recallReason}
          onChange={(e) => onReasonChange(e.target.value)}
        />
      </div>

      <div className="flex justify-end gap-2 pt-2">
        <Button variant="ghost" size="sm" onClick={onClose}>
          Cancel
        </Button>
        <Button
          variant="danger"
          size="sm"
          onClick={onConfirm}
          disabled={isActionLoading || !recallReason.trim()}
        >
          {isActionLoading ? 'Recalling...' : 'Confirm Recall'}
        </Button>
      </div>
    </div>
  </Modal>
);
