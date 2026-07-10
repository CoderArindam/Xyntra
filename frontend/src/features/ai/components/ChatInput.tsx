import React, { useState, useRef, useEffect } from 'react';
import { Send, Square } from 'lucide-react';
import { useAIChat } from '../hooks/useAIChat';

export const ChatInput: React.FC = () => {
  const [input, setInput] = useState('');
  const { sendMessage, stopGenerating, isGenerating } = useAIChat();
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (input.trim() && !isGenerating) {
      const uiContext = {
        current_page: window.location.pathname
      };
      sendMessage(input, uiContext);
      setInput('');
      if (textareaRef.current) {
        textareaRef.current.style.height = '44px';
      }
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    if (textareaRef.current) {
      textareaRef.current.style.height = '44px'; // Reset first
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 128)}px`;
    }
  };

  useEffect(() => {
    if (!isGenerating && textareaRef.current) {
      // Small timeout ensures the DOM is ready for focus after disabled state changes
      setTimeout(() => {
        textareaRef.current?.focus();
      }, 50);
    }
  }, [isGenerating]);

  return (
    <div className="flex flex-col gap-2">
      {isGenerating && (
        <div className="flex justify-center mb-2">
          <button
            onClick={stopGenerating}
            className="flex items-center gap-2 px-3 py-1.5 text-xs font-medium text-brand-text-muted hover:text-brand-text bg-brand-bg rounded border border-brand-border hover:border-brand-text-muted transition-colors shadow-sm"
          >
            <Square className="w-3 h-3 fill-current" />
            Stop generating
          </button>
        </div>
      )}

      <form onSubmit={handleSubmit} className="relative flex items-end w-full group">
        <textarea
          ref={textareaRef}
          value={input}
          onChange={handleInput}
          onKeyDown={handleKeyDown}
          placeholder="Ask me anything..."
          className="w-full min-h-[44px] max-h-32 py-3 pl-4 pr-12 bg-brand-bg border border-brand-border rounded-xl text-sm text-brand-text placeholder:text-brand-text-muted/60 focus:outline-none focus:border-brand-primary/50 focus:ring-2 focus:ring-brand-primary/20 focus:bg-brand-surface resize-none transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          rows={1}
          disabled={isGenerating}
        />
        <button
          type="submit"
          disabled={!input.trim() || isGenerating}
          className="absolute right-2 bottom-2 p-1.5 rounded-lg text-brand-text-muted hover:text-brand-primary hover:bg-brand-primary/10 disabled:opacity-40 disabled:hover:bg-transparent disabled:hover:text-brand-text-muted transition-colors"
        >
          <Send className="w-4 h-4" />
        </button>
      </form>
      <div className="text-[10px] text-center text-brand-text-muted/60 mt-1">
        AI can make mistakes. Verify important information.
      </div>
    </div>
  );
};
