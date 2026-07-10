import React, { useMemo } from 'react';
import type { AIEvent } from '../types/ai';
import { Loader2, CheckCircle2, XCircle, Search, Zap, Check } from 'lucide-react';

interface ExecutionTimelineProps {
  events: AIEvent[];
}

type PhaseStatus = 'pending' | 'running' | 'completed' | 'failed';

interface TimelinePhase {
  id: string;
  label: string;
  status: PhaseStatus;
  icon: React.ReactNode;
}

export const ExecutionTimeline: React.FC<ExecutionTimelineProps> = React.memo(({ events }) => {
  const phases = useMemo(() => {
    if (!events || events.length === 0) return [];
    
    let hasPlanning = false;
    let planningDone = false;
    let hasExecution = false;
    let executionDone = false;
    let hasFailed = false;
    let hasCompleted = false;

    events.forEach(event => {
      if (event.type === 'planning_started') hasPlanning = true;
      if (event.type === 'planning_completed') {
        hasPlanning = true;
        planningDone = true;
      }
      if (event.type === 'execution_started' || event.type === 'step_started') hasExecution = true;
      if (event.type === 'execution_completed') {
        hasExecution = true;
        executionDone = true;
        hasCompleted = true;
      }
      if (event.type === 'execution_failed' || event.type === 'error') hasFailed = true;
    });

    const timeline: TimelinePhase[] = [];

    // Phase 1: Planning
    if (hasPlanning) {
      timeline.push({
        id: 'planning',
        label: 'Understanding request',
        status: hasFailed && !planningDone ? 'failed' : planningDone ? 'completed' : 'running',
        icon: <Search className="w-3.5 h-3.5" />
      });
    }

    // Phase 2: Executing
    if (hasExecution || (planningDone && !hasFailed && !hasCompleted)) {
      timeline.push({
        id: 'executing',
        label: 'Executing actions',
        status: hasFailed && !executionDone ? 'failed' : executionDone ? 'completed' : 'running',
        icon: <Zap className="w-3.5 h-3.5" />
      });
    }

    // Phase 3: Done
    if (hasCompleted || hasFailed) {
      timeline.push({
        id: 'done',
        label: hasFailed ? 'Execution failed' : 'Completed successfully',
        status: hasFailed ? 'failed' : 'completed',
        icon: hasFailed ? <XCircle className="w-3.5 h-3.5" /> : <Check className="w-3.5 h-3.5" />
      });
    }

    return timeline;
  }, [events]);

  if (phases.length === 0) return null;

  const renderIcon = (status: PhaseStatus, defaultIcon: React.ReactNode) => {
    if (status === 'running') return <Loader2 className="w-3.5 h-3.5 animate-spin text-brand-primary" />;
    if (status === 'completed') return <Check className="w-3.5 h-3.5 text-emerald-500" />;
    if (status === 'failed') return <XCircle className="w-3.5 h-3.5 text-red-500" />;
    return <span className="text-brand-text-muted">{defaultIcon}</span>;
  };

  return (
    <div className="my-4 flex flex-col gap-2">
      {phases.map((phase) => (
        <div key={phase.id} className="flex items-center gap-3 text-[13px] animate-fade-in-up">
          <div className="flex-shrink-0 w-6 h-6 flex items-center justify-center rounded-full bg-brand-surface border border-brand-border shadow-sm">
            {renderIcon(phase.status, phase.icon)}
          </div>
          <span className={`font-medium transition-colors ${
            phase.status === 'failed' ? 'text-red-500' :
            phase.status === 'running' ? 'text-brand-text animate-pulse' :
            phase.status === 'completed' ? 'text-brand-text' : 'text-brand-text-muted'
          }`}>
            {phase.label}
          </span>
        </div>
      ))}
    </div>
  );
});
