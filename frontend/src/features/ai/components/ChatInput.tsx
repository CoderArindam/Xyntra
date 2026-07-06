import React, { useState } from 'react';
import { Send, Square } from 'lucide-react';
import { useAIChat } from '../hooks/useAIChat';

export const ChatInput: React.FC = () => {
  const [input, setInput] = useState('');
  const { sendMessage, stopGenerating, isGenerating } = useAIChat();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (input.trim() && !isGenerating) {
      // Pass basic UI Context (can be expanded later via hooks)
      const uiContext = {
        current_page: window.location.pathname
      };
      
      sendMessage(input, uiContext);
      setInput('');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <div className="flex flex-col gap-2">
      {isGenerating && (
        <div className="flex justify-center mb-2">
          <button
            onClick={stopGenerating}
            className="flex items-center gap-2 px-3 py-1.5 text-xs font-medium text-brand-text-muted hover:text-brand-text bg-brand-bg rounded border border-brand-border hover:border-brand-text-muted transition-colors"
          >
            <Square className="w-3 h-3 fill-current" />
            Stop generating
          </button>
        </div>
      )}

      <form onSubmit={handleSubmit} className="relative flex items-end w-full">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask me anything..."
          className="w-full min-h-[44px] max-h-32 py-3 pl-4 pr-12 bg-brand-bg border border-brand-border rounded-lg text-sm text-brand-text placeholder:text-brand-text-muted focus:outline-none focus:border-brand-primary focus:ring-1 focus:ring-brand-primary resize-none transition-all"
          rows={1}
          disabled={isGenerating}
        />
        <button
          type="submit"
          disabled={!input.trim() || isGenerating}
          className="absolute right-2 bottom-2 p-1.5 rounded-md text-brand-primary hover:bg-brand-primary hover:text-white disabled:opacity-40 disabled:hover:bg-transparent disabled:hover:text-brand-primary transition-colors"
        >
          <Send className="w-4 h-4" />
        </button>
      </form>
      <div className="text-[10px] text-center text-brand-text-muted mt-1">
        AI can make mistakes. Verify important information.
      </div>
    </div>
  );
};
