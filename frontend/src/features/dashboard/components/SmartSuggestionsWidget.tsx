import React, { useState, useEffect, useCallback } from 'react';
import { Sparkles, Loader2 } from 'lucide-react';
import { Card, CardHeader, CardTitle } from '../../../components/ui/Card';
import type { DashboardBoardSummary } from '../../../services/dashboardApi';
import {
  listOrgProposals,
  approveProposal,
  rejectProposal,
  type TaskProposal,
} from '../../../services/taskProposals';

interface SmartSuggestionItem {
  id: string;
  proposalId?: string;
  title: string;
  description: string;
  primaryActionLabel: string;
  actionType: 'accept' | 'schedule';
  isRealProposal?: boolean;
}

interface SmartSuggestionsWidgetProps {
  summaryBoards?: DashboardBoardSummary[];
  onOpenJoinModal: () => void;
  onOpenProposalsModal: () => void;
  onProposalProcessed?: () => void;
}

export const SmartSuggestionsWidget: React.FC<SmartSuggestionsWidgetProps> = ({
  summaryBoards = [],
  onOpenJoinModal,
  onOpenProposalsModal,
  onProposalProcessed,
}) => {
  const [suggestions, setSuggestions] = useState<SmartSuggestionItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [processingId, setProcessingId] = useState<string | null>(null);

  const fetchRealProposals = useCallback(async () => {
    setIsLoading(true);
    try {
      const realProposals: TaskProposal[] = await listOrgProposals('pending');
      const items: SmartSuggestionItem[] = [];

      if (realProposals && realProposals.length > 0) {
        realProposals.slice(0, 2).forEach((prop) => {
          items.push({
            id: prop.id,
            proposalId: prop.id,
            title: `AI Proposed Task: ${prop.title}`,
            description: prop.description || prop.source_transcript_quote || `AI suggests adding task '${prop.title}' from meeting insights.`,
            primaryActionLabel: 'Accept Task',
            actionType: 'accept',
            isRealProposal: true,
          });
        });
      }

      // Fill remaining suggestions from active boards
      if (items.length < 2 && summaryBoards.length > 0) {
        const bottleneckBoard = summaryBoards.find((b) => b.overdue_count > 0 || b.completion_percentage < 50) || summaryBoards[0];
        if (bottleneckBoard && !items.some((i) => i.id.includes(bottleneckBoard.name))) {
          items.push({
            id: `opt-${bottleneckBoard.id}`,
            title: 'Optimize Task Allocation',
            description: `AI detects potential bottlenecks in '${bottleneckBoard.name}'. Reallocate resources?`,
            primaryActionLabel: 'Accept',
            actionType: 'accept',
          });
        }

        const nearDoneBoard = summaryBoards.find((b) => b.completion_percentage >= 70 && b.id !== bottleneckBoard?.id) || summaryBoards[1] || summaryBoards[0];
        if (nearDoneBoard && items.length < 2) {
          items.push({
            id: `sch-${nearDoneBoard.id}`,
            title: 'Schedule Team Review',
            description: `Project '${nearDoneBoard.name}' is nearing completion. Schedule a final review meeting?`,
            primaryActionLabel: 'Schedule',
            actionType: 'schedule',
          });
        }
      }

      setSuggestions(items);
    } catch (err) {
      console.error('Failed to load pending proposals for suggestions:', err);
    } finally {
      setIsLoading(false);
    }
  }, [summaryBoards]);

  useEffect(() => {
    fetchRealProposals();
  }, [fetchRealProposals]);

  const handleDismiss = async (item: SmartSuggestionItem) => {
    setProcessingId(item.id);
    try {
      if (item.isRealProposal && item.proposalId) {
        await rejectProposal(item.proposalId);
        if (onProposalProcessed) onProposalProcessed();
      }
      setSuggestions((prev) => prev.filter((s) => s.id !== item.id));
    } catch (err) {
      console.error('Failed to reject proposal:', err);
    } finally {
      setProcessingId(null);
    }
  };

  const handleAction = async (item: SmartSuggestionItem) => {
    if (item.actionType === 'schedule') {
      onOpenJoinModal();
      setSuggestions((prev) => prev.filter((s) => s.id !== item.id));
      return;
    }

    if (item.isRealProposal && item.proposalId) {
      setProcessingId(item.id);
      try {
        await approveProposal(item.proposalId);
        if (onProposalProcessed) onProposalProcessed();
        setSuggestions((prev) => prev.filter((s) => s.id !== item.id));
      } catch (err) {
        console.error('Failed to approve proposal:', err);
      } finally {
        setProcessingId(null);
      }
    } else {
      onOpenProposalsModal();
      setSuggestions((prev) => prev.filter((s) => s.id !== item.id));
    }
  };

  return (
    <Card variant="default" padding="md" className="space-y-4 shadow-sm">
      <CardHeader className="flex-row items-center justify-between mb-0 pb-1">
        <CardTitle className="text-base font-bold text-brand-text flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-emerald-400" aria-hidden="true" />
          <span>Smart Suggestions</span>
        </CardTitle>
      </CardHeader>

      {isLoading ? (
        <div className="py-6 flex items-center justify-center text-brand-text-muted">
          <Loader2 className="w-5 h-5 animate-spin text-emerald-500 opacity-60" />
        </div>
      ) : suggestions.length === 0 ? (
        <div className="p-4 text-center border border-dashed border-brand-border rounded-xl text-xs text-brand-text-muted">
          All suggestions handled. AI monitoring workspace in real-time.
        </div>
      ) : (
        <div className="space-y-3">
          {suggestions.map((item) => {
            const isProcessingThis = processingId === item.id;
            return (
              <div
                key={item.id}
                className="p-4 rounded-xl bg-brand-surface-low/50 border border-brand-border/60 space-y-3"
              >
                <p className="text-xs text-brand-text leading-relaxed">
                  <span className="font-bold text-brand-text">{item.title}:</span>{' '}
                  {item.description}
                </p>

                <div className="flex items-center justify-end gap-2 pt-1">
                  {item.actionType === 'accept' ? (
                    <button
                      disabled={isProcessingThis}
                      onClick={() => handleAction(item)}
                      className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-brand-primary text-white hover:bg-brand-primary-hover transition-colors shadow-2xs cursor-pointer flex items-center gap-1 disabled:opacity-50"
                    >
                      {isProcessingThis && <Loader2 className="w-3 h-3 animate-spin" />}
                      {item.primaryActionLabel}
                    </button>
                  ) : (
                    <button
                      disabled={isProcessingThis}
                      onClick={() => handleAction(item)}
                      className="px-3 py-1.5 rounded-lg text-xs font-semibold border border-brand-border bg-brand-surface text-brand-text hover:bg-brand-surface-low transition-colors shadow-2xs cursor-pointer flex items-center gap-1 disabled:opacity-50"
                    >
                      {isProcessingThis && <Loader2 className="w-3 h-3 animate-spin" />}
                      {item.primaryActionLabel}
                    </button>
                  )}

                  <button
                    disabled={isProcessingThis}
                    onClick={() => handleDismiss(item)}
                    className="px-3 py-1.5 rounded-lg text-xs font-semibold text-brand-text-muted hover:text-brand-text hover:bg-brand-surface-low transition-colors cursor-pointer disabled:opacity-50"
                  >
                    Dismiss
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </Card>
  );
};

export default SmartSuggestionsWidget;
