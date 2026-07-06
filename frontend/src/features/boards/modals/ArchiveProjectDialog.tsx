import React, { useState } from 'react';
import { Archive, AlertTriangle, X } from 'lucide-react';
import { useProjectSettingsStore } from '../../../store/projectSettingsStore';
import { useNavigate } from 'react-router-dom';

interface ArchiveProjectDialogProps {
  boardId: number;
  projectName: string;
  isOpen: boolean;
  onClose: () => void;
}

export const ArchiveProjectDialog: React.FC<ArchiveProjectDialogProps> = ({
  boardId,
  projectName,
  isOpen,
  onClose,
}) => {
  const [confirmText, setConfirmText] = useState("");
  const { archiveProject, isArchiving } = useProjectSettingsStore();
  const navigate = useNavigate();

  if (!isOpen) return null;

  const isConfirmed = confirmText === projectName || confirmText === "ARCHIVE";

  const handleArchive = async () => {
    if (!isConfirmed) return;
    await archiveProject(boardId);
    onClose();
    navigate("/dashboard"); // Redirect to dashboard
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-brand-surface border border-brand-border rounded-xl shadow-xl w-full max-w-md overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="px-6 py-4 border-b border-brand-border flex items-center justify-between sticky top-0 bg-brand-surface z-10">
          <div className="flex items-center gap-3 text-red-600 dark:text-red-500">
            <AlertTriangle size={20} />
            <h2 className="text-lg font-semibold">Archive Project</h2>
          </div>
          <button
            onClick={onClose}
            className="text-brand-text-muted hover:text-brand-text hover:bg-brand-surface-low p-1.5 rounded-md transition-colors cursor-pointer"
          >
            <X size={20} />
          </button>
        </div>

        {/* Body */}
        <div className="px-6 py-6 overflow-y-auto">
          <p className="text-sm text-brand-text mb-4">
            Are you sure you want to archive <strong>{projectName}</strong>?
          </p>
          <ul className="text-sm text-brand-text-muted space-y-2 list-disc list-inside mb-6">
            <li>The project will be hidden from the sidebar and dashboard.</li>
            <li>No tasks or data will be deleted.</li>
            <li>You can restore it later if needed.</li>
          </ul>

          <div className="space-y-2">
            <label className="text-sm font-medium text-brand-text">
              To confirm, type <strong>{projectName}</strong> or{" "}
              <strong>ARCHIVE</strong>:
            </label>
            <input
              type="text"
              value={confirmText}
              onChange={(e) => setConfirmText(e.target.value)}
              className="w-full bg-brand-bg border border-brand-border rounded-lg px-3 py-2 text-sm text-brand-text outline-none focus:border-red-500 focus:ring-1 focus:ring-red-500 transition-shadow"
              placeholder={projectName}
            />
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-brand-border bg-brand-surface-low flex justify-end gap-3 sticky bottom-0">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-brand-text bg-transparent border border-brand-border hover:bg-brand-surface-hover rounded-md transition-colors"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleArchive}
            disabled={!isConfirmed || isArchiving}
            className="px-4 py-2 text-sm font-medium text-white bg-red-600 hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed rounded-md transition-colors flex items-center gap-2"
          >
            <Archive size={16} />
            {isArchiving ? "Archiving..." : "Archive Project"}
          </button>
        </div>
      </div>
    </div>
  );
};
