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
    set((state) => ({ messages: [...state.messages, message] })),
    
  updateLastMessage: (content) =>
    set((state) => {
      const messages = [...state.messages];
      if (messages.length > 0) {
        messages[messages.length - 1].content += content;
      }
      return { messages };
    }),

  updateLastMessageMetadata: (metadata) =>
    set((state) => {
      const messages = [...state.messages];
      if (messages.length > 0) {
        const currentMeta = messages[messages.length - 1].metadata || {};
        messages[messages.length - 1].metadata = { ...currentMeta, ...metadata };
      }
      return { messages };
    }),

  clearConversation: () => 
    set({ messages: [], conversationId: uuidv4() })
}));
