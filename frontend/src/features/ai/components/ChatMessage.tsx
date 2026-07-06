import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { User, Sparkles } from 'lucide-react';
import type { ChatMessage as ChatMessageType } from '../types/ai';
import { ExecutionTimeline } from './ExecutionTimeline';
import { ConfirmationCard } from './ConfirmationCard';

interface ChatMessageProps {
  message: ChatMessageType;
}

export const ChatMessage: React.FC<ChatMessageProps> = ({ message }) => {
  const isUser = message.role === 'user';
  const isSystem = message.role === 'system';
  const isTool = message.role === 'tool';

  if (isSystem || isTool) return null;

  return (
    <div className={`flex w-full mb-6 ${isUser ? 'justify-end' : 'justify-start'} group animate-fade-in-up`}>
      <div className={`flex gap-3 max-w-[90%] ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
        
        {/* Avatar */}
        <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center shadow-sm border mt-1 ${
          isUser 
            ? 'bg-brand-primary text-white border-brand-primary/20' 
            : 'bg-gradient-to-br from-indigo-500 to-purple-600 text-white border-purple-500/20'
        }`}>
          {isUser ? <User className="w-4 h-4" /> : <Sparkles className="w-4 h-4" />}
        </div>

        {/* Message Bubble */}
        <div 
          className={`relative px-5 py-3.5 text-[14px] leading-relaxed shadow-sm ${
            isUser 
              ? 'bg-brand-primary text-white rounded-2xl rounded-tr-sm' 
              : 'bg-brand-surface border border-brand-border text-brand-text rounded-2xl rounded-tl-sm'
          }`}
        >
          {!isUser && (
            <div className="absolute inset-0 bg-gradient-to-b from-white/5 to-transparent rounded-2xl rounded-tl-sm pointer-events-none"></div>
          )}
          
          <div className={`relative z-10 prose prose-sm max-w-none ${isUser ? 'prose-invert text-white/90' : 'dark:prose-invert text-brand-text'} 
              prose-p:leading-relaxed prose-pre:bg-brand-bg prose-pre:border prose-pre:border-brand-border prose-pre:text-brand-text prose-a:text-brand-primary
              prose-headings:font-semibold prose-strong:font-semibold
              [&>*:first-child]:mt-0 [&>*:last-child]:mb-0`}>
            
            {/* Timeline */}
            {!isUser && message.metadata?.events && (
              <ExecutionTimeline events={message.metadata.events} />
            )}
            
            {message.content && (
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {message.content}
              </ReactMarkdown>
            )}
            
            {/* Confirmation Card */}
            {!isUser && message.metadata?.executionStatus === 'WAITING_FOR_CONFIRMATION' && message.metadata?.latestEvent?.plan && (
              <ConfirmationCard 
                plan={message.metadata.latestEvent.plan} 
                reason={message.metadata.latestEvent.reason} 
                messageId={message.id}
              />
            )}
            
            {/* Cancelled State */}
            {!isUser && message.metadata?.executionStatus === 'CANCELLED' && (
              <div className="mt-3 text-yellow-700 text-sm font-medium border border-yellow-200 bg-yellow-50/50 p-3 rounded-lg flex items-center gap-2">
                ⚠️ Execution was cancelled.
              </div>
            )}
            
            {/* Partially Completed State */}
            {!isUser && message.metadata?.executionStatus === 'PARTIALLY_COMPLETED' && (
              <div className="mt-3 text-orange-700 text-sm font-medium border border-orange-200 bg-orange-50/50 p-3 rounded-lg flex items-center gap-2">
                ⚠️ Execution completed partially. Some steps failed or were skipped.
              </div>
            )}
            
            {/* Failed State */}
            {!isUser && message.metadata?.executionStatus === 'FAILED' && (
              <div className="mt-3 text-red-700 text-sm font-medium border border-red-200 bg-red-50/50 p-3 rounded-lg flex items-center gap-2">
                ❌ Execution failed to complete.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
