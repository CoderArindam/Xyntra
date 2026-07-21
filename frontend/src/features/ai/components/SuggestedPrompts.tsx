import React from 'react';
import { useAIChat } from '../hooks/useAIChat';
import { ArrowRight, Layout, ListTodo, BrainCircuit, Settings } from 'lucide-react';

const SUGGESTIONS = [
  { text: "What am I working on?", icon: <ListTodo className="w-4 h-4" /> },
  { text: "Summarize this project.", icon: <Layout className="w-4 h-4" /> },
  { text: "Switch to Dark Mode.", icon: <Settings className="w-4 h-4" /> }
];

export const SuggestedPrompts: React.FC = () => {
  const { sendMessage, isGenerating } = useAIChat();

  return (
    <div className="flex flex-col items-center justify-center h-full text-center px-6 opacity-0 animate-fade-in pt-8 pb-12 w-full max-w-md mx-auto">
      
      {/* Dynamic Header */}
      <div className="relative mb-8">
        <div className="absolute -inset-4 bg-gradient-to-r from-brand-primary/20 via-purple-500/20 to-brand-primary/20 rounded-full blur-xl opacity-70 transition-opacity duration-1000"></div>
        <div className="relative w-16 h-16 bg-gradient-to-br from-brand-surface to-brand-bg rounded-2xl flex items-center justify-center border border-brand-border/50 shadow-md overflow-hidden group transition-all duration-300">
          <BrainCircuit className="w-8 h-8 text-brand-primary/80" />
        </div>
      </div>
      
      <div className="space-y-3 mb-10 w-full">
        <h3 className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-brand-text via-brand-text to-brand-text-muted">
          Welcome to KAI
        </h3>
        <p className="text-sm text-brand-text-muted max-w-[280px] mx-auto leading-relaxed">
          Your personal workspace assistant. I can help you manage tasks, analyze boards, and brainstorm ideas.
        </p>
      </div>

      <div className="flex flex-col gap-3 w-full">
        {SUGGESTIONS.map((suggestion, index) => (
          <button
            key={index}
            disabled={isGenerating}
            onClick={() => sendMessage(suggestion.text)}
            className="group relative w-full flex items-center justify-between p-4 rounded-xl border border-brand-border bg-brand-surface hover:border-brand-primary/50 transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed shadow-sm hover:shadow-md hover:-translate-y-0.5 overflow-hidden text-left"
          >
            <div className="absolute inset-0 bg-gradient-to-r from-brand-primary/0 via-brand-primary/5 to-brand-primary/0 opacity-0 group-hover:opacity-100 transition-opacity duration-500"></div>
            <div className="relative flex items-center gap-3 text-brand-text-muted group-hover:text-brand-text transition-colors">
              <div className="p-2 rounded-lg bg-brand-bg text-brand-primary group-hover:bg-brand-primary group-hover:text-white transition-colors duration-300">
                {suggestion.icon}
              </div>
              <span className="text-sm font-medium">{suggestion.text}</span>
            </div>
            <ArrowRight className="relative w-4 h-4 text-brand-text-muted opacity-0 -translate-x-2 group-hover:opacity-100 group-hover:translate-x-0 transition-all duration-300" />
          </button>
        ))}
      </div>
    </div>
  );
};
