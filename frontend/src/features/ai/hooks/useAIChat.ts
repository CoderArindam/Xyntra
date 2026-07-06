import { useState, useRef, useCallback } from 'react';
import { v4 as uuidv4 } from 'uuid';
import { useAIStore } from '../store/aiStore';
import type { ChatMessage, UIContext } from '../types/ai';

import api from '../../../lib/axios';

export function useAIChat() {
  const { messages, addMessage, updateLastMessage, updateLastMessageMetadata, conversationId } = useAIStore();
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const sendMessage = useCallback(async (content: string, uiContext?: UIContext, confirmedPlan?: any) => {
    if (!content.trim() && !confirmedPlan) return;

    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    abortControllerRef.current = new AbortController();
    
    // Only add user message if it's a new request, not a confirmation
    if (content.trim()) {
      const userMessage: ChatMessage = {
        id: uuidv4(),
        conversation_id: conversationId,
        role: 'user',
        content,
        timestamp: new Date().toISOString()
      };
      addMessage(userMessage);
    }

    setIsGenerating(true);
    setError(null);

    const assistantMessageId = uuidv4();
    const assistantMessage: ChatMessage = {
      id: assistantMessageId,
      conversation_id: conversationId,
      role: 'assistant',
      content: '',
      timestamp: new Date().toISOString(),
      metadata: {
        events: [] // To store the timeline events
      }
    };
    addMessage(assistantMessage);

    try {
      const payload = {
        conversation_id: conversationId,
        messages: content.trim() ? [...messages, {
            id: uuidv4(),
            conversation_id: conversationId,
            role: 'user',
            content,
            timestamp: new Date().toISOString()
          }] : messages,
        ui_context: uiContext,
        confirmed_plan: confirmedPlan
      };

      const response = await api.post('/ai/chat', payload, {
        responseType: 'stream',
        adapter: 'fetch',
        signal: abortControllerRef.current.signal
      });

      const reader = response.data?.getReader();
      const decoder = new TextDecoder('utf-8');

      if (!reader) throw new Error('No reader available');

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        
        const lines = chunk.split('\n');
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const dataStr = line.substring(6);
            if (dataStr === '[DONE]') break;
            
            try {
              const data = JSON.parse(dataStr);
              if (data.error || data.type === 'error' || data.type === 'execution_failed') {
                setError(data.error || 'Execution failed');
              }
              
              // Handle execution content
              if (data.content && (data.type === undefined || data.type === 'content' || data.type === 'assistant_message_chunk')) {
                updateLastMessage(data.content);
              }
              
              // Save event to metadata for rendering the timeline/confirmation
              if (data.v && data.type) {
                updateLastMessageMetadata({
                   latestEvent: data,
                   events: [...(useAIStore.getState().messages.find(m => m.id === assistantMessageId)?.metadata?.events || []), data]
                });
              }
            } catch (e) {
              // Gracefully ignore parse errors
            }
          }
        }
      }

    } catch (err: any) {
      if (err.name === 'AbortError') {
        console.log('Stream aborted');
      } else {
        setError(err.message || 'An error occurred.');
      }
    } finally {
      setIsGenerating(false);
      abortControllerRef.current = null;
    }

  }, [messages, addMessage, updateLastMessage, updateLastMessageMetadata, conversationId]);

  const stopGenerating = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      setIsGenerating(false);
    }
  }, []);

  return {
    sendMessage,
    stopGenerating,
    isGenerating,
    error
  };
}
