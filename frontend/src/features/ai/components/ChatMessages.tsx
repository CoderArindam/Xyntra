import React, { useEffect, useRef } from 'react';
import { useAIStore } from '../store/aiStore';
import { ChatMessage } from './ChatMessage';
import { SuggestedPrompts } from './SuggestedPrompts';

export const ChatMessages: React.FC = () => {
  const { messages } = useAIStore();
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
      <div ref={bottomRef} />
    </div>
  );
};
