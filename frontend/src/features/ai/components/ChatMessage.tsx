import React, { memo } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { User, Loader2, XCircle, AlertTriangle, CheckCircle2 } from "lucide-react";
import type { ChatMessage as ChatMessageType } from "../types/ai";
import { ExecutionTimeline } from "./ExecutionTimeline";
import { ConfirmationCard } from "./ConfirmationCard";

interface ChatMessageProps {
  message: ChatMessageType;
}

export const ChatMessage: React.FC<ChatMessageProps> = memo(({ message }) => {
  const isUser = message.role === "user";
  const isSystem = message.role === "system";
  const isTool = message.role === "tool";

  if (isSystem || isTool) return null;

  const isEmptyAssistant = !isUser && !message.content && (!message.metadata?.events || message.metadata.events.length === 0);

  const getErrorCard = () => {
    // Determine error type based on content or latest event
    const errText = message.metadata?.latestEvent?.error?.toLowerCase() || '';
    if (errText.includes('permission') || errText.includes('unauthorized')) {
      return { title: 'Permission Denied', icon: <AlertTriangle className="w-4 h-4" />, msg: "You don't have permission to perform this action." };
    }
    if (errText.includes('validation') || errText.includes('missing')) {
      return { title: 'Validation Error', icon: <AlertTriangle className="w-4 h-4" />, msg: "Please provide all required information." };
    }
    return { title: 'Execution Failed', icon: <XCircle className="w-4 h-4" />, msg: "The action could not be completed. Please try again." };
  };

  const errorCard = getErrorCard();

  return (
    <div
      className={`flex w-full mb-6 ${isUser ? "justify-end" : "justify-start"} group animate-fade-in-up`}
    >
      <div
        className={`flex gap-3 max-w-[90%] ${isUser ? "flex-row-reverse" : "flex-row"}`}
      >
        {/* Avatar */}
        <div
          className={`flex-shrink-0 w-8 h-8 rounded-xl flex items-center justify-center shadow-sm border mt-1 ${
            isUser
              ? "bg-brand-primary text-white border-brand-primary/20"
              : "bg-gradient-to-br from-indigo-500 via-purple-500 to-brand-primary text-white border-white/10"
          }`}
        >
          {isUser ? (
            <User className="w-4 h-4" />
          ) : (
            <div className="font-bold text-[15px] tracking-tight font-sans">K</div>
          )}
        </div>

        {/* Message Bubble */}
        <div
          className={`relative px-5 py-3.5 text-[14px] leading-relaxed shadow-sm min-h-[44px] transition-all duration-200 ${
            isUser
              ? "bg-brand-primary text-white rounded-2xl rounded-tr-sm"
              : "bg-brand-surface border border-brand-border text-brand-text rounded-2xl rounded-tl-sm"
          }`}
        >
          {!isUser && (
            <div className="absolute inset-0 bg-gradient-to-b from-white/5 to-transparent rounded-2xl rounded-tl-sm pointer-events-none"></div>
          )}

          <div
            className={`relative z-10 prose prose-sm max-w-none ${isUser ? "prose-invert text-white/90" : "dark:prose-invert text-brand-text"} 
              prose-p:leading-relaxed prose-pre:bg-brand-bg prose-pre:border prose-pre:border-brand-border prose-pre:text-brand-text prose-a:text-brand-primary
              prose-headings:font-semibold prose-strong:font-semibold
              [&>*:first-child]:mt-0 [&>*:last-child]:mb-0`}
          >
            {/* Timeline */}
            {!isUser && message.metadata?.events && (
              <ExecutionTimeline events={message.metadata.events} />
            )}
            
            {/* Thinking State */}
            {isEmptyAssistant && (
              <div className="flex items-center gap-2 py-1 px-1 text-brand-text-muted">
                <Loader2 className="w-4 h-4 animate-spin" />
                <span className="text-sm font-medium animate-pulse">Thinking...</span>
              </div>
            )}

            {/* Content */}
            {message.content && (
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {message.content}
              </ReactMarkdown>
            )}

            {/* Confirmation Card */}
            {!isUser &&
              message.metadata?.executionStatus ===
                "WAITING_FOR_CONFIRMATION" &&
              message.metadata?.latestEvent?.plan && (
                <ConfirmationCard
                  plan={message.metadata.latestEvent.plan}
                  reason={message.metadata.latestEvent.reason}
                  messageId={message.id}
                />
              )}

            {/* Cancelled State */}
            {!isUser && message.metadata?.executionStatus === "CANCELLED" && !message.content && (
              <div className="mt-3 overflow-hidden rounded-xl border border-brand-border bg-brand-surface shadow-sm">
                <div className="p-3 bg-brand-bg flex items-center gap-2 text-brand-text text-sm font-medium border-b border-brand-border">
                  <XCircle className="w-4 h-4 text-brand-text-muted" />
                  Execution Cancelled
                </div>
              </div>
            )}

            {/* Partially Completed State */}
            {!isUser &&
              message.metadata?.executionStatus === "PARTIALLY_COMPLETED" && (
              <div className="mt-3 overflow-hidden rounded-xl border border-brand-border bg-brand-surface shadow-sm">
                <div className="p-3 bg-brand-bg flex items-center gap-2 text-brand-text text-sm font-medium border-b border-brand-border">
                  <AlertTriangle className="w-4 h-4 text-orange-500" />
                  Execution Partially Completed
                </div>
                <div className="p-3 text-sm text-brand-text-muted bg-brand-surface">
                  <p>Some steps failed or were skipped.</p>
                </div>
              </div>
              )}

            {/* Failed State */}
            {!isUser && message.metadata?.executionStatus === "FAILED" && (
              <div className="mt-3 overflow-hidden rounded-xl border border-brand-border bg-brand-surface shadow-sm">
                <div className="p-3 bg-brand-bg flex items-center gap-2 text-brand-text text-sm font-medium border-b border-brand-border">
                  <span className="text-red-500">{errorCard.icon}</span>
                  {errorCard.title}
                </div>
                <div className="p-3 text-sm text-brand-text-muted bg-brand-surface">
                  <p>{errorCard.msg}</p>
                </div>
              </div>
            )}
            
            {/* Success Tool Card (if result exists and content is raw) */}
            {!isUser && message.metadata?.executionStatus === "COMPLETED" && message.metadata?.latestEvent?.result && (
              <div className="mt-3 overflow-hidden rounded-xl border border-brand-border bg-brand-surface shadow-sm">
                <div className="p-3 bg-brand-surface flex items-center gap-2 text-brand-text text-sm font-medium">
                  <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                  Action Successful
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
});
