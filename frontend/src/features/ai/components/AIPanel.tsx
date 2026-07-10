import React from "react";
import { X } from "lucide-react";
import { useAIStore } from "../store/aiStore";
import { ChatMessages } from "./ChatMessages";
import { ChatInput } from "./ChatInput";

export const AIPanel: React.FC = () => {
  const { isOpen, setIsOpen } = useAIStore();

  const isEnabled = import.meta.env.VITE_AI_ENABLED !== "false";
  if (!isEnabled) return null;

  return (
    <>
      {/* Backdrop for mobile */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/20 backdrop-blur-sm z-40 md:hidden animate-fade-in"
          onClick={() => setIsOpen(false)}
        />
      )}

      {/* Panel */}
      <div
        className={`fixed top-0 right-0 h-full w-full md:w-[400px] bg-brand-surface shadow-2xl z-50 transform transition-transform duration-500 ease-[cubic-bezier(0.16,1,0.3,1)] flex flex-col border-l border-brand-border
          ${isOpen ? "translate-x-0" : "translate-x-full"}`}
      >
        <div className="flex items-center justify-between p-4 border-b border-brand-border bg-brand-surface">
          <div className="flex items-center gap-2.5">
            <div className="flex-shrink-0 w-7 h-7 rounded-lg bg-gradient-to-br from-indigo-500 via-purple-500 to-brand-primary flex items-center justify-center text-white shadow-sm border border-white/10">
              <span className="font-bold text-[14px] tracking-tight font-sans">
                K
              </span>
            </div>
            <h2 className="text-[15px] font-semibold text-brand-text tracking-tight">
              KAI{" "}
              <span className="text-brand-text-muted font-normal ml-0.5">
                Workspace Intelligence
              </span>
            </h2>
          </div>
          <button
            onClick={() => setIsOpen(false)}
            className="p-1 rounded hover:bg-brand-bg text-brand-text-muted hover:text-brand-text transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="flex-1 overflow-hidden flex flex-col relative bg-brand-bg">
          <ChatMessages />
        </div>

        <div className="p-4 bg-brand-surface border-t border-brand-border">
          <ChatInput />
        </div>
      </div>
    </>
  );
};
