import { useCallback, useEffect, useRef, useState } from 'react';

const DEFAULT_TIMEOUT_MS = 30000;

export function useEventSource(url, { token, auto = true, timeout = DEFAULT_TIMEOUT_MS } = {}) {
  const [events, setEvents] = useState([]);
  const [connected, setConnected] = useState(false);
  const esRef = useRef(null);
  const timerRef = useRef(null);
  const retryRef = useRef(0);

  const clearTimers = useCallback(() => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const connect = useCallback(() => {
    if (!url) return;
    clearTimers();
    try {
      if (esRef.current) {
        try { esRef.current.close(); } catch (_e) { /* ignore */ }
      }
      const src = buildSSEUrl(url, token);
      const es = new EventSource(src);
      esRef.current = es;
      setConnected(true);

      const keepAlive = () => {
        clearTimers();
        timerRef.current = setTimeout(() => {
          if (esRef.current && esRef.current.readyState !== EventSource.CLOSED) {
            setConnected((c) => c);
          }
        }, timeout);
      };

      es.onopen = keepAlive;
      es.onerror = () => {
        setConnected(false);
      };
      es.onmessage = (msg) => {
        try {
          const data = typeof msg.data === 'string' ? JSON.parse(msg.data) : msg.data;
          const ev = data?.event ? data : { event: 'message', data };
          setEvents((prev) => [...prev.slice(0), { ...ev, _ts: Date.now() }]);
        } catch (_e) {
          setEvents((prev) => [...prev.slice(0), { event: 'message', data: msg.data, _ts: Date.now() }]);
        }
        keepAlive();
      };
      // support browser's addEventListener style in case custom events override
      es.addEventListener('*', (msg) => {
        try {
          const data = typeof msg.data === 'string' ? JSON.parse(msg.data) : msg.data;
          const ev = data?.event ? data : { event: 'message', data };
          setEvents((prev) => [...prev.slice(0), { ...ev, _ts: Date.now() }]);
        } catch (_e) {
          setEvents((prev) => [...prev.slice(0), { event: 'message', data: msg.data, _ts: Date.now() }]);
        }
        keepAlive();
      });
      retryRef.current = 0;
    } catch (_e) {
      setConnected(false);
    }
  }, [clearTimers, token, url, timeout]);

  useEffect(() => {
    if (!auto) return;
    if (!url) return;
    connect();
    return () => {
      clearTimers();
      if (esRef.current && esRef.current.readyState === EventSource.OPEN) {
        esRef.current.close();
      }
    };
  }, [auto, url, connect, clearTimers]);

  const reconnect = useCallback(() => {
    retryRef.current = 0;
    connect();
  }, [connect]);

  const disconnect = useCallback(() => {
    clearTimers();
    if (esRef.current && esRef.current.readyState === EventSource.OPEN) {
      esRef.current.close();
    }
    setConnected(false);
  }, [clearTimers]);

  return { events, connected, reconnect, disconnect };
}

function buildSSEUrl(url, token) {
  try {
    const u = new URL(url, window.location.origin);
    if (!u.protocol) {
      if (url.startsWith('http')) return url;
      return new URL(url, window.location.origin).toString();
    }
    if (token) {
      u.searchParams.set('api_key', token);
    }
    return u.toString();
  } catch (_e) {
    const sep = url.includes('?') ? '&' : '?';
    return token ? `${url}${sep}api_key=${encodeURIComponent(token)}` : url;
  }
}
export default useEventSource;
