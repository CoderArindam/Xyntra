import React, { useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import { X } from 'lucide-react';

export interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  children: React.ReactNode;
  width?: string;
  hideCloseButton?: boolean;
  noPadding?: boolean;
}

export const Modal: React.FC<ModalProps> = ({
  isOpen,
  onClose,
  title,
  children,
  width = 'max-w-md',
  hideCloseButton = false,
  noPadding = false
}) => {
  const modalRef = useRef<HTMLDivElement>(null);

  // Handle escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  // Handle body scroll locking
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  // Handle focus trapping
  useEffect(() => {
    if (isOpen && modalRef.current) {
      const focusableElements = modalRef.current.querySelectorAll(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      );
      const firstElement = focusableElements[0] as HTMLElement;
      const lastElement = focusableElements[focusableElements.length - 1] as HTMLElement;

      const handleTabKey = (e: KeyboardEvent) => {
        if (e.key !== 'Tab') return;

        if (e.shiftKey) {
          if (document.activeElement === firstElement) {
            e.preventDefault();
            lastElement?.focus();
          }
        } else {
          if (document.activeElement === lastElement) {
            e.preventDefault();
            firstElement?.focus();
          }
        }
      };

      document.addEventListener('keydown', handleTabKey);
      
      // Auto focus first element (or modal itself if none)
      if (firstElement) {
        firstElement.focus();
      } else {
        modalRef.current.focus();
      }

      return () => document.removeEventListener('keydown', handleTabKey);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  return createPortal(
    <div 
      className="fixed inset-0 flex items-center justify-center bg-black/50 p-4 transition-opacity z-[var(--z-overlay)]"
      onClick={onClose}
    >
      <div 
        ref={modalRef}
        className={`bg-brand-surface rounded-lg shadow-xl overflow-hidden w-full ${width} z-[var(--z-modal)] animate-in fade-in zoom-in-95 duration-200 outline-none flex flex-col max-h-[90vh]`}
        onClick={(e) => e.stopPropagation()}
        tabIndex={-1}
        role="dialog"
        aria-modal="true"
        aria-labelledby={title ? "modal-title" : undefined}
      >
        {title && (
          <div className="px-6 py-4 border-b border-brand-border flex items-center justify-between shrink-0">
            <h2 id="modal-title" className="text-lg font-semibold text-brand-text">
              {title}
            </h2>
            {!hideCloseButton && (
              <button 
                onClick={onClose}
                className="text-brand-text-muted hover:text-brand-text transition-colors p-1 rounded hover:bg-brand-surface-low"
                aria-label="Close modal"
              >
                <X size={20} />
              </button>
            )}
          </div>
        )}
        <div className={`overflow-y-auto ${noPadding ? '' : 'p-6'}`}>
          {children}
        </div>
      </div>
    </div>,
    document.body
  );
};

export default Modal;
