import React from 'react';
import { Sparkles, ChevronRight } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardDescription } from '../../../components/ui/Card';

interface PendingProposalsWidgetProps {
  pendingPropsCount: number;
  onOpenProposalsModal: () => void;
}

export const PendingProposalsWidget: React.FC<PendingProposalsWidgetProps> = ({
  pendingPropsCount,
  onOpenProposalsModal,
}) => {
  return (
    <Card variant="default" padding="md" className="space-y-4">
      <CardHeader className="flex-row items-center justify-between mb-0">
        <div className="space-y-0.5">
          <CardTitle className="text-sm">
            <Sparkles className="w-4 h-4 text-emerald-400" /> Pending AI Proposals
          </CardTitle>
          <CardDescription>Extracted task proposals awaiting review</CardDescription>
        </div>
        {pendingPropsCount > 0 && (
          <span className="px-2 py-0.5 text-[10px] font-bold rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 animate-pulse">
            {pendingPropsCount} Pending
          </span>
        )}
      </CardHeader>

      <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20 space-y-3">
        <div className="flex items-center justify-between text-xs">
          <span className="font-semibold text-emerald-400">Action Required</span>
          <span className="text-[11px] text-brand-text-muted">Org-wide queue</span>
        </div>

        <p className="text-xs text-brand-text-muted leading-relaxed">
          {pendingPropsCount > 0
            ? `${pendingPropsCount} action item${pendingPropsCount > 1 ? 's' : ''} extracted from meeting transcripts are waiting for board assignment and manager approval.`
            : 'All extracted meeting task proposals have been reviewed and processed.'}
        </p>

        <button
          onClick={onOpenProposalsModal}
          className="w-full py-2 px-3 text-xs font-semibold bg-emerald-500 hover:bg-emerald-600 text-white rounded-lg transition-colors cursor-pointer flex items-center justify-center gap-1.5 shadow-xs"
        >
          Open Proposals Drawer ({pendingPropsCount}) <ChevronRight className="w-3.5 h-3.5" />
        </button>
      </div>
    </Card>
  );
};
