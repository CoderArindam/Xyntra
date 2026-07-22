import React from 'react';
import { type Board } from '../../../../services/boardsApi';
import { Button } from '../../../../components/ui/Button';
import { Modal } from '../../../../components/common/Modal';

interface AddBoardModalProps {
  isOpen: boolean;
  onClose: () => void;
  accessibleBoards: Board[];
  onSelectBoard: (boardId: string, boardName: string) => void;
}

export const AddBoardModal: React.FC<AddBoardModalProps> = ({
  isOpen,
  onClose,
  accessibleBoards,
  onSelectBoard,
}) => (
  <Modal isOpen={isOpen} onClose={onClose} title="Add Board to Timesheet">
    <div className="space-y-4">
      <p className="text-xs text-brand-text-muted">
        Select an accessible project board to log time against.
      </p>

      <div className="max-h-60 overflow-y-auto space-y-1.5 border border-brand-border rounded-lg p-2">
        {accessibleBoards.map((b) => (
          <div
            key={b.id}
            onClick={() => {
              onSelectBoard(String(b.id), b.name);
              onClose();
            }}
            className="flex items-center justify-between p-2.5 rounded-lg hover:bg-brand-surface-low cursor-pointer transition-colors"
          >
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-brand-primary" />
              <span className="text-sm font-medium text-brand-text">{b.name}</span>
            </div>
            <span className="text-xs text-brand-text-muted">{b.project_key}</span>
          </div>
        ))}
      </div>

      <div className="flex justify-end gap-2 pt-2">
        <Button variant="ghost" size="sm" onClick={onClose}>
          Cancel
        </Button>
      </div>
    </div>
  </Modal>
);
