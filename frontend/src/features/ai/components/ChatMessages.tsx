import React, { useEffect, useRef } from 'react';
import { useAIStore } from '../store/aiStore';
import { ChatMessage } from './ChatMessage';
import { SuggestedPrompts } from './SuggestedPrompts';

export const ChatMessages: React.FC = () => {
  const { messages, isGenerating } = useAIStore();
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Filter out system and tool messages
  const visibleMessages = messages.filter(m => m.role === 'user' || m.role === 'assistant');

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-4">
      {visibleMessages.length === 0 ? (
        <SuggestedPrompts />
      ) : (
        visibleMessages.map((msg) => (
          <ChatMessage key={msg.id} message={msg} />
        ))
      )}
      {isGenerating && (
        <div className="flex justify-start mb-6 animate-fade-in-up">
          <div className="flex gap-3 max-w-[90%] flex-row">
            <div className="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center shadow-sm border mt-1 bg-gradient-to-br from-indigo-500 to-purple-600 text-white border-purple-500/20">
              <div className="w-4 h-4 flex items-center justify-center">
                <span className="flex space-x-1">
                  <span className="w-1 h-1 bg-white rounded-full animate-bounce [animation-delay:-0.3s]"></span>
                  <span className="w-1 h-1 bg-white rounded-full animate-bounce [animation-delay:-0.15s]"></span>
                  <span className="w-1 h-1 bg-white rounded-full animate-bounce"></span>
                </span>
              </div>
            </div>
            <div className="relative px-5 py-3.5 text-[14px] leading-relaxed shadow-sm bg-brand-surface border border-brand-border text-brand-text rounded-2xl rounded-tl-sm flex items-center">
              <span className="text-brand-text-muted italic">Processing...</span>
            </div>
          </div>
        </div>
      )}
      <div ref={bottomRef} />
    </div>
  );
};
