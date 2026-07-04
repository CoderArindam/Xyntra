import React from 'react';
import Modal from '../Modal/Modal';
import { AlertTriangle } from 'lucide-react';

interface ConfirmDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  description: string;
  confirmText?: string;
  cancelText?: string;
  isDestructive?: boolean;
  isLoading?: boolean;
}

export const ConfirmDialog: React.FC<ConfirmDialogProps> = ({
  isOpen,
  onClose,
  onConfirm,
  title,
  description,
  confirmText = 'Confirm',
  cancelText = 'Cancel',
  isDestructive = false,
  isLoading = false
}) => {
  return (
    <Modal isOpen={isOpen} onClose={onClose} title={title} width="max-w-sm">
      <div className="flex items-start mb-6">
        {isDestructive && (
          <div className="flex-shrink-0 mr-4 text-brand-error bg-brand-error/10 p-2 rounded-full">
            <AlertTriangle size={24} />
          </div>
        )}
        <div className="text-brand-text-muted mt-1">
          {description}
        </div>
      </div>
      
      <div className="flex justify-end gap-3 pt-4 border-t border-brand-border mt-auto">
        <button
          onClick={onClose}
          disabled={isLoading}
          className="px-4 py-2 text-sm font-medium text-brand-text hover:bg-brand-surface-low rounded transition-colors"
        >
          {cancelText}
        </button>
        <button
          onClick={onConfirm}
          disabled={isLoading}
          className={`px-4 py-2 text-sm font-medium text-white rounded transition-colors flex items-center justify-center min-w-[80px] ${
            isDestructive 
              ? 'bg-brand-error hover:bg-red-700' 
              : 'bg-brand-primary hover:bg-brand-primary-hover'
          }`}
        >
          {isLoading ? (
            <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
          ) : (
            confirmText
          )}
        </button>
      </div>
    </Modal>
  );
};

export default ConfirmDialog;
