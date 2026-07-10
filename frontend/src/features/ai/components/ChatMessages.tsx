import React, { useEffect, useRef, useState, useCallback } from 'react';
import { useAIStore } from '../store/aiStore';
import { ChatMessage } from './ChatMessage';
import { SuggestedPrompts } from './SuggestedPrompts';
import { ArrowDown } from 'lucide-react';

export const ChatMessages: React.FC = () => {
  const { messages } = useAIStore();
  const bottomRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [isAutoScrollPaused, setIsAutoScrollPaused] = useState(false);

  const scrollToBottom = useCallback((smooth = true) => {
    if (bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: smooth ? 'smooth' : 'auto' });
      setIsAutoScrollPaused(false);
    }
  }, []);

  const handleScroll = useCallback(() => {
    if (!containerRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = containerRef.current;
    const isNearBottom = scrollHeight - scrollTop - clientHeight < 100;
    
    if (!isNearBottom && !isAutoScrollPaused) {
      setIsAutoScrollPaused(true);
    } else if (isNearBottom && isAutoScrollPaused) {
      setIsAutoScrollPaused(false);
    }
  }, [isAutoScrollPaused]);

  useEffect(() => {
    if (!isAutoScrollPaused) {
      scrollToBottom();
    }
  }, [messages, isAutoScrollPaused, scrollToBottom]);

  // Filter out system and tool messages
  const visibleMessages = messages.filter(m => m.role === 'user' || m.role === 'assistant');

  return (
    <div className="relative flex-1 flex flex-col overflow-hidden">
      <div 
        ref={containerRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto p-4 space-y-4 scroll-smooth"
      >
        {visibleMessages.length === 0 ? (
          <SuggestedPrompts />
        ) : (
          visibleMessages.map((msg) => (
            <ChatMessage key={msg.id} message={msg} />
          ))
        )}
        <div ref={bottomRef} className="h-4" />
      </div>

      {isAutoScrollPaused && (
        <button
          onClick={() => scrollToBottom()}
          className="absolute bottom-4 left-1/2 -translate-x-1/2 bg-brand-surface border border-brand-border shadow-lg rounded-full p-2 text-brand-text hover:text-brand-primary transition-all hover:scale-110 z-10 animate-fade-in-up"
          aria-label="Scroll to bottom"
        >
          <ArrowDown className="w-4 h-4" />
        </button>
      )}
    </div>
  );
};

