import React from 'react';
import type { ExecutionPlan } from '../types/ai';
import { useAIChat } from '../hooks/useAIChat';
import { useAIStore } from '../store/aiStore';
import { CheckCircle, XCircle, AlertTriangle } from 'lucide-react';

interface ConfirmationCardProps {
  plan: ExecutionPlan;
  reason?: string;
  messageId: string;
}

export const ConfirmationCard: React.FC<ConfirmationCardProps> = ({ plan, reason, messageId }) => {
  const { sendMessage } = useAIChat();
  const { updateLastMessageMetadata, messages } = useAIStore();
  
  const currentMessage = messages.find(m => m.id === messageId);
  const isConfirmed = currentMessage?.metadata?.isConfirmed;
  const isCancelled = currentMessage?.metadata?.isCancelled;

  const handleConfirm = () => {
    updateLastMessageMetadata({ isConfirmed: true });
    sendMessage('', undefined, plan);
  };

  const handleCancel = () => {
    updateLastMessageMetadata({ isCancelled: true });
  };

  if (isConfirmed) {
    return (
      <div className="mt-4 p-3 bg-green-500/10 border border-green-500/20 rounded-xl flex items-center gap-2 text-green-500 text-sm">
        <CheckCircle className="w-4 h-4" />
        Plan execution confirmed.
      </div>
    );
  }

  if (isCancelled) {
    return (
      <div className="mt-4 p-3 bg-red-500/10 border border-red-500/20 rounded-xl flex items-center gap-2 text-red-500 text-sm">
        <XCircle className="w-4 h-4" />
        Plan execution cancelled.
      </div>
    );
  }

  return (
    <div className="mt-4 border border-brand-border rounded-xl bg-brand-surface overflow-hidden shadow-sm">
      <div className="p-3 bg-amber-500/10 border-b border-amber-500/20 flex items-start gap-2">
        <AlertTriangle className="w-5 h-5 text-amber-500 flex-shrink-0 mt-0.5" />
        <div>
          <h4 className="font-semibold text-amber-500 text-sm">Confirmation Required</h4>
          {reason && <p className="text-xs text-amber-500/80 mt-1">{reason}</p>}
        </div>
      </div>
      
      <div className="p-4">
        <h5 className="font-semibold text-sm mb-3 text-brand-text">Execution Plan</h5>
        <div className="space-y-3">
          {plan.steps.map((step, idx) => (
            <div key={step.id} className="flex gap-3 text-sm">
              <div className="flex-shrink-0 w-6 h-6 rounded-full bg-brand-bg flex items-center justify-center text-xs border border-brand-border text-brand-text-muted">
                {idx + 1}
              </div>
              <div>
                <p className="text-brand-text font-medium">{step.description}</p>
                <p className="text-brand-text-muted text-xs mt-0.5">Action: <span className="font-mono bg-brand-bg px-1 py-0.5 rounded border border-brand-border">{step.action}</span></p>
              </div>
            </div>
          ))}
        </div>
        
        <div className="mt-5 flex gap-3">
          <button 
            onClick={handleCancel}
            className="flex-1 py-2 rounded-lg border border-brand-border text-brand-text hover:bg-brand-bg transition-colors text-sm font-medium"
          >
            Cancel
          </button>
          <button 
            onClick={handleConfirm}
            className="flex-1 py-2 rounded-lg bg-brand-primary text-white hover:bg-brand-primary/90 transition-colors text-sm font-medium"
          >
            Confirm & Execute
          </button>
        </div>
      </div>
    </div>
  );
};
