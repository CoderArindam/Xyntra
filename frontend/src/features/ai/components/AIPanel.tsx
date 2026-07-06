import React, { useEffect } from 'react';
import { X } from 'lucide-react';
import { useAIStore } from '../store/aiStore';
import { ChatMessages } from './ChatMessages';
import { ChatInput } from './ChatInput';

export const AIPanel: React.FC = () => {
  const { isOpen, setIsOpen } = useAIStore();

  const isEnabled = import.meta.env.VITE_AI_ENABLED !== 'false';
  if (!isEnabled) return null;

  return (
    <>
      {/* Backdrop for mobile */}
      {isOpen && (
        <div 
          className="fixed inset-0 bg-black/20 z-40 md:hidden"
          onClick={() => setIsOpen(false)}
        />
      )}
      
      {/* Panel */}
      <div 
        className={`fixed top-0 right-0 h-full w-full md:w-[400px] bg-brand-surface shadow-2xl z-50 transform transition-transform duration-300 ease-in-out flex flex-col border-l border-brand-border
          ${isOpen ? 'translate-x-0' : 'translate-x-full'}`}
      >
        <div className="flex items-center justify-between p-4 border-b border-brand-border bg-brand-surface">
          <h2 className="text-lg font-semibold text-brand-text flex items-center gap-2">
            Workspace Assistant
          </h2>
          <button 
            onClick={() => setIsOpen(false)}
            className="p-1 rounded hover:bg-brand-bg text-brand-text-muted hover:text-brand-text transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="flex-1 overflow-hidden flex flex-col relative bg-brand-bg">
          <ChatMessages />
        </div>

        <div className="p-4 bg-brand-surface border-t border-brand-border">
          <ChatInput />
        </div>
      </div>
    </>
  );
};
