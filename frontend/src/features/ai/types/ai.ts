export interface ToolCall {
  id: string;
  name: string;
  arguments: Record<string, any>;
}

export interface ChatMessage {
  id: string;
  conversation_id: string;
  role: 'user' | 'assistant' | 'system' | 'tool';
  content: string;
  timestamp: string;
  metadata?: Record<string, any>;
  tool_calls?: ToolCall[];
}

export interface UIContext {
  current_page?: string;
  board_id?: number;
  task_id?: number;
  selected_task_ids?: number[];
  organization_id?: number;
}

export interface PlanStep {
  id: string;
  description: string;
  action: string;
  arguments: Record<string, any>;
  expected_result: string;
}

export interface ExecutionPlan {
  goal: string;
  steps: PlanStep[];
  estimated_duration: string;
}

export interface AIChatRequest {
  conversation_id: string;
  messages: ChatMessage[];
  ui_context?: UIContext;
  confirmed_plan?: ExecutionPlan;
}

// SSE Event types
export type AIEventType = 
  | 'content'
  | 'planning_started'
  | 'planning_completed'
  | 'execution_started'
  | 'step_started'
  | 'step_completed'
  | 'confirmation_required'
  | 'execution_completed'
  | 'execution_failed'
  | 'execution_cancelled'
  | 'error';

export interface AIEvent {
  v: string;
  execution_id?: string;
  type: AIEventType;
  timestamp: number;
  content?: string;
  plan?: ExecutionPlan;
  step_id?: string;
  description?: string;
  goal?: string;
  total_steps?: number;
  result?: any;
  error?: string;
  reason?: string;
}
