/**
 * useSSE - SSE 实时事件流 Hook
 * 订阅 Worker 进度、Agent 步骤等实时事件
 */
import { useEffect, useRef, useState, useCallback } from 'react';
import { EventSourcePolyfill } from 'event-source-polyfill';

const API_BASE_URL = process.env.REACT_APP_API_URL || '';

export type SSEEventType =
  | 'worker.status'
  | 'task.started'
  | 'task.completed'
  | 'task.failed'
  | 'agent.step.started'
  | 'agent.step.completed'
  | 'agent.step.failed';

export interface SSEEvent {
  type: SSEEventType;
  data: any;
  timestamp: number;
}

interface UseSSEOptions {
  onConnect?: () => void;
  onDisconnect?: () => void;
  onError?: (error: Event) => void;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
}

export function useSSE(options: UseSSEOptions = {}) {
  const {
    onConnect,
    onDisconnect,
    onError,
    reconnectInterval = 3000,
    maxReconnectAttempts = 5,
  } = options;

  const [isConnected, setIsConnected] = useState(false);
  const [lastEvent, setLastEvent] = useState<SSEEvent | null>(null);
  const [events, setEvents] = useState<SSEEvent[]>([]);

  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimerRef = useRef<NodeJS.Timeout | null>(null);

  const connect = useCallback(() => {
    if (eventSourceRef.current?.readyState === EventSource.OPEN) {
      return;
    }

    const url = `${API_BASE_URL}/api/events/stream`;

    // 获取 API Key
    const apiKey = localStorage.getItem('api_key') || '';

    const es = new EventSourcePolyfill(url, {
      headers: {
        'X-API-Key': apiKey,
      },
      heartbeatTimeout: 60000,
    });

    es.onopen = () => {
      console.log('[SSE] Connected');
      setIsConnected(true);
      reconnectAttemptsRef.current = 0;
      onConnect?.();
    };

    es.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        const sseEvent: SSEEvent = {
          type: data.type || event.type,
          data: data.data || data,
          timestamp: Date.now(),
        };

        setLastEvent(sseEvent);
        setEvents(prev => [...prev.slice(-99), sseEvent]); // 保留最近100条
      } catch (err) {
        console.error('[SSE] Parse error:', err);
      }
    };

    es.onerror = (error) => {
      console.error('[SSE] Error:', error);
      setIsConnected(false);
      onError?.(error as Event);

      es.close();

      // 自动重连
      if (reconnectAttemptsRef.current < maxReconnectAttempts) {
        reconnectAttemptsRef.current++;
        console.log(`[SSE] Reconnecting... (${reconnectAttemptsRef.current}/${maxReconnectAttempts})`);

        reconnectTimerRef.current = setTimeout(() => {
          connect();
        }, reconnectInterval);
      } else {
        console.error('[SSE] Max reconnect attempts reached');
      }
    };

    eventSourceRef.current = es as unknown as EventSource;
  }, [onConnect, onError, reconnectInterval, maxReconnectAttempts]);

  const disconnect = useCallback(() => {
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }

    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }

    setIsConnected(false);
    onDisconnect?.();
  }, [onDisconnect]);

  const clearEvents = useCallback(() => {
    setEvents([]);
    setLastEvent(null);
  }, []);

  useEffect(() => {
    connect();

    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  return {
    isConnected,
    lastEvent,
    events,
    connect,
    disconnect,
    clearEvents,
  };
}

/**
 * 使用特定事件类型的 Hook
 */
export function useSSEEvent<T = any>(
  eventType: SSEEventType | SSEEventType[],
  handler: (data: T) => void
) {
  const { lastEvent } = useSSE();
  const handlerRef = useRef(handler);

  // 保持 handler 引用最新
  useEffect(() => {
    handlerRef.current = handler;
  }, [handler]);

  useEffect(() => {
    if (!lastEvent) return;

    const types = Array.isArray(eventType) ? eventType : [eventType];

    if (types.includes(lastEvent.type)) {
      handlerRef.current(lastEvent.data);
    }
  }, [lastEvent, eventType]);
}
