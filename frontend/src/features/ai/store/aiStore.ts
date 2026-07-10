import { create } from 'zustand';
import { v4 as uuidv4 } from 'uuid';
import type { ChatMessage } from '../types/ai';

interface AIStore {
  isOpen: boolean;
  setIsOpen: (isOpen: boolean) => void;
  toggleOpen: () => void;

  isGenerating: boolean;
  setIsGenerating: (isGenerating: boolean) => void;

  conversationId: string;
  messages: ChatMessage[];
  
  addMessage: (message: ChatMessage) => void;
  updateLastMessage: (content: string) => void;
  updateLastMessageMetadata: (metadata: Record<string, any>) => void;
  clearConversation: () => void;
}

export const useAIStore = create<AIStore>((set) => ({
  isOpen: false,
  setIsOpen: (isOpen) => set({ isOpen }),
  toggleOpen: () => set((state) => ({ isOpen: !state.isOpen })),

  isGenerating: false,
  setIsGenerating: (isGenerating) => set({ isGenerating }),

  conversationId: uuidv4(),
  messages: [],

  addMessage: (message) => 
    set((state) => {
      // Deduplicate to prevent double-renders of the same message (e.g. strict mode or double-click)
      if (state.messages.some(m => m.id === message.id)) {
        return state;
      }
      return { messages: [...state.messages, message] };
    }),
    
  updateLastMessage: (content) =>
    set((state) => {
      if (state.messages.length === 0) return state;
      const messages = [...state.messages];
      const lastIndex = messages.length - 1;
      messages[lastIndex] = {
        ...messages[lastIndex],
        content: messages[lastIndex].content + content
      };
      return { messages };
    }),

  updateLastMessageMetadata: (metadata) =>
    set((state) => {
      if (state.messages.length === 0) return state;
      const messages = [...state.messages];
      const lastIndex = messages.length - 1;
      const currentMeta = messages[lastIndex].metadata || {};
      messages[lastIndex] = {
        ...messages[lastIndex],
        metadata: { ...currentMeta, ...metadata }
      };
      return { messages };
    }),

  clearConversation: () => 
    set({ messages: [], conversationId: uuidv4() })
}));
