import { useState, useRef, useCallback } from 'react';
import { v4 as uuidv4 } from 'uuid';
import { useAIStore } from '../store/aiStore';
import type { ChatMessage, UIContext } from '../types/ai';

import api from '../../../lib/axios';

export function useAIChat() {
  const { messages, addMessage, updateLastMessage, updateLastMessageMetadata, conversationId, isGenerating, setIsGenerating } = useAIStore();
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

      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        
        while (buffer.includes('\n\n')) {
          const splitIndex = buffer.indexOf('\n\n');
          const eventStr = buffer.slice(0, splitIndex);
          buffer = buffer.slice(splitIndex + 2);
          
          const lines = eventStr.split('\n');
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const dataStr = line.substring(6);
              if (dataStr === '[DONE]') break;
              
              try {
                const data = JSON.parse(dataStr);
                if (data.error || data.type === 'error') {
                  setError(data.error || 'Execution failed');
                }
                
                // Handle execution content
                if (data.content && (data.type === undefined || data.type === 'content' || data.type === 'assistant_message_chunk')) {
                  updateLastMessage(data.content);
                }
                
                // Save event to metadata for rendering the timeline/confirmation
                if (data.v && data.type) {
                  const prevMetadata = useAIStore.getState().messages.find(m => m.id === assistantMessageId)?.metadata || {};
                  
                  let executionStatus = prevMetadata.executionStatus || 'CREATED';
                  
                  if (data.type === 'execution_result' && data.result?.status) {
                      executionStatus = data.result.status;
                  } else if (data.type === 'error' || data.type === 'execution_failed') {
                      executionStatus = 'FAILED';
                  } else if (data.type === 'execution_cancelled') {
                      executionStatus = 'CANCELLED';
                  } else if (data.type === 'confirmation_required') {
                      executionStatus = 'WAITING_FOR_CONFIRMATION';
                  }
                  
                  updateLastMessageMetadata({
                     latestEvent: data,
                     events: [...(prevMetadata.events || []), data],
                     executionStatus: executionStatus
                  });
                }
              } catch (e) {
                // Gracefully ignore parse errors
              }
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
