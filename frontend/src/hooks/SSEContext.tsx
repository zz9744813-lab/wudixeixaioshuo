/**
 * SSEContext - SSE 全局状态管理
 * 整个应用共享 SSE 连接
 */
import React, { createContext, useContext, ReactNode } from 'react';
import { useSSE, SSEEvent } from './useSSE';

interface SSEContextValue {
  isConnected: boolean;
  lastEvent: SSEEvent | null;
  events: SSEEvent[];
  connect: () => void;
  disconnect: () => void;
  clearEvents: () => void;
}

const SSEContext = createContext<SSEContextValue | null>(null);

export function SSEProvider({ children }: { children: ReactNode }) {
  const sse = useSSE({
    onConnect: () => console.log('[SSE] Context connected'),
    onDisconnect: () => console.log('[SSE] Context disconnected'),
    onError: (err) => console.error('[SSE] Context error:', err),
  });

  return (
    <SSEContext.Provider value={sse}>
      {children}
    </SSEContext.Provider>
  );
}

export function useSSEContext() {
  const context = useContext(SSEContext);
  if (!context) {
    throw new Error('useSSEContext must be used within SSEProvider');
  }
  return context;
}
