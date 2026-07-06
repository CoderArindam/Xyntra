import React from 'react';
import type { AIEvent } from '../types/ai';
import { Loader2, CheckCircle2, XCircle, PlayCircle, Search, Settings } from 'lucide-react';

interface ExecutionTimelineProps {
  events: AIEvent[];
}

export const ExecutionTimeline: React.FC<ExecutionTimelineProps> = ({ events }) => {
  if (!events || events.length === 0) return null;

  const renderIcon = (type: string, status?: string) => {
    switch (type) {
      case 'planning_started': return <Search className="w-4 h-4 text-brand-primary animate-pulse" />;
      case 'planning_completed': return <CheckCircle2 className="w-4 h-4 text-brand-primary" />;
      case 'execution_started': return <PlayCircle className="w-4 h-4 text-purple-500" />;
      case 'step_started': return <Loader2 className="w-4 h-4 text-brand-text-muted animate-spin" />;
      case 'step_completed': return <CheckCircle2 className="w-4 h-4 text-green-500" />;
      case 'execution_failed': 
      case 'error': return <XCircle className="w-4 h-4 text-red-500" />;
      case 'execution_completed': return <CheckCircle2 className="w-5 h-5 text-green-500" />;
      default: return <Settings className="w-4 h-4 text-brand-text-muted" />;
    }
  };

  const renderMessage = (event: AIEvent) => {
    switch (event.type) {
      case 'planning_started': return 'Analyzing request and creating execution plan...';
      case 'planning_completed': return 'Plan created successfully.';
      case 'execution_started': return `Executing plan: ${event.goal || 'Starting'}`;
      case 'step_started': return `Running step: ${event.description || event.step_id}`;
      case 'step_completed': return `Completed step: ${event.step_id}`;
      case 'execution_failed': return `Failed: ${event.error}`;
      case 'execution_completed': return 'Execution completed successfully.';
      case 'confirmation_required': return 'Waiting for confirmation...';
      case 'error': return `Error: ${event.error}`;
      default: return null;
    }
  };

  // Only show the most recent "step_started" or "planning_started" if they are the latest,
  // or show completed ones with dimmed styling.
  
  return (
    <div className="my-3 space-y-2">
      {events.map((event, idx) => {
        const msg = renderMessage(event);
        if (!msg) return null;
        
        // Hide interim step_started if step_completed exists for it
        if (event.type === 'step_started') {
            const hasCompleted = events.some(e => 
                (e.type === 'step_completed' || e.type === 'execution_failed') && e.step_id === event.step_id
            );
            if (hasCompleted) return null;
        }
        
        if (event.type === 'planning_started') {
             const hasCompleted = events.some(e => e.type === 'planning_completed');
             if (hasCompleted) return null;
        }

        const isLatest = idx === events.length - 1;

        return (
          <div key={idx} className={`flex items-start gap-3 text-sm ${isLatest ? 'text-brand-text font-medium' : 'text-brand-text-muted'}`}>
            <div className="mt-0.5">{renderIcon(event.type)}</div>
            <div>{msg}</div>
          </div>
        );
      })}
    </div>
  );
};
