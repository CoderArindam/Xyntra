import React from 'react';
import { Bot } from 'lucide-react';
import { useAIStore } from '../store/aiStore';

export const AIButton: React.FC = () => {
  const { toggleOpen, isOpen } = useAIStore();
  
  // Conditionally rendered in AppLayout if AI_ENABLED, 
  // but we can also check ENV here if available.
  const isEnabled = import.meta.env.VITE_AI_ENABLED !== 'false';
  if (!isEnabled) return null;

  return (
    <button
      onClick={toggleOpen}
      className={`fixed bottom-6 right-6 p-4 rounded-full shadow-lg transition-all z-50 flex items-center justify-center 
        ${isOpen ? 'bg-brand-primary text-white rotate-12 scale-95' : 'bg-brand-surface text-brand-text hover:bg-brand-primary hover:text-white hover:scale-105'}`}
      title="Open KAI"
    >
      <Bot className="w-6 h-6" />
    </button>
  );
};
