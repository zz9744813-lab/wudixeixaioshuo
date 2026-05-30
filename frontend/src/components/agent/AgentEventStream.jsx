import React, { useEffect, useState } from 'react';
import api from '../../services/api';

function AgentEventStream({ runId }) {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!runId) return;
    fetchEvents();
    const timer = setInterval(fetchEvents, 3000);
    return () => clearInterval(timer);
  }, [runId]);

  const fetchEvents = async () => {
    if (!runId) return;
    try {
      const res = await api.get(`/agent-runs/${runId}/events`);
      setEvents(res.data || []);
    } catch (err) {
      console.error(err);
    }
  };

  const formatTime = (ts) => {
    if (!ts) return '';
    return new Date(ts).toLocaleTimeString();
  };

  const getEventColor = (event) => {
    if (event.includes('failed')) return '#b42318';
    if (event.includes('succeeded') || event.includes('finished')) return '#027a48';
    if (event.includes('started') || event.includes('running')) return '#b54708';
    return '#667085';
  };

  return (
    <div style={{
      maxHeight: 300, overflow: 'auto', fontFamily: 'monospace', fontSize: 12,
      background: '#1e1e1e', color: '#d4d4d4', borderRadius: 10, padding: 12,
    }}>
      {events.length === 0 ? (
        <p style={{ color: '#667085' }}>等待事件...</p>
      ) : events.map((ev, idx) => (
        <div key={idx} style={{ marginBottom: 4 }}>
          <span style={{ color: '#667085' }}>[{formatTime(ev.timestamp)}]</span>{' '}
          <span style={{ color: getEventColor(ev.event) }}>{ev.event}</span>
          {ev.title && <span style={{ color: '#a0aec0' }}> — {ev.title}</span>}
          {ev.error_message && <span style={{ color: '#fc8181' }}> ({ev.error_message})</span>}
        </div>
      ))}
    </div>
  );
}

export default AgentEventStream;
