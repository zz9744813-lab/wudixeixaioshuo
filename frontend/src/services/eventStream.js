/**
 * EventStream Service - SSE 实时事件流客户端
 * 使用 @microsoft/fetch-event-source 支持自定义 headers（鉴权）
 */

import { fetchEventSource } from '@microsoft/fetch-event-source';
import { API_BASE_URL } from './api';

const getApiKey = () =>
  process.env.REACT_APP_API_KEY || localStorage.getItem('APP_API_KEY') || '';

class EventStreamService {
  constructor() {
    this.abortController = null;
    this.listeners = new Map();
    this.isConnected = false;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.reconnectDelay = 3000; // 3秒
  }

  /**
   * 连接到 SSE 事件流
   */
  connect() {
    if (this.abortController) {
      console.log('[EventStream] 已连接，跳过重复连接');
      return;
    }

    const apiKey = getApiKey();
    if (!apiKey) {
      console.error('[EventStream] 未找到API Key，无法连接SSE');
      this._emit('connection.status', { status: 'error', error: 'Missing API Key' });
      return;
    }

    console.log('[EventStream] 正在连接到:', `${API_BASE_URL}/events/stream`);

    this.abortController = new AbortController();

    fetchEventSource(`${API_BASE_URL}/events/stream`, {
      signal: this.abortController.signal,
      headers: {
        'X-API-Key': apiKey,
        'Accept': 'text/event-stream',
      },
      onopen: async (response) => {
        if (!response.ok) {
          if (response.status === 401) {
            throw new Error('SSE connect failed: 401 Unauthorized');
          }
          throw new Error(`SSE connect failed: ${response.status}`);
        }
        console.log('[EventStream] 连接已建立');
        this.isConnected = true;
        this.reconnectAttempts = 0;
        this._emit('connection.status', { status: 'connected' });
      },
      onmessage: (event) => {
        try {
          const data = JSON.parse(event.data);
          console.log(`[EventStream] 收到 ${event.event || 'message'}:`, data);
          this._handleEvent(data, event.event);
        } catch (err) {
          console.error('[EventStream] 解析消息失败:', err, event.data);
        }
      },
      onclose: () => {
        console.log('[EventStream] 连接关闭');
        this.isConnected = false;
        this._emit('connection.status', { status: 'disconnected' });
        this._attemptReconnect();
      },
      onerror: (err) => {
        console.error('[EventStream] 连接错误:', err);
        this.isConnected = false;
        this._emit('connection.status', { status: 'error', error: err.message });
        // 不在这里重连，由 onclose 处理
        throw err; // 必须抛出错误才能触发重连
      },
    });
  }

  /**
   * 断开 SSE 连接
   */
  disconnect() {
    if (this.abortController) {
      console.log('[EventStream] 断开连接');
      this.abortController.abort();
      this.abortController = null;
    }
    this.isConnected = false;
    this.reconnectAttempts = 0;
    this._emit('connection.status', { status: 'disconnected' });
  }

  /**
   * 订阅事件
   * @param {string} eventType - 事件类型
   * @param {function} callback - 回调函数
   * @returns {function} 取消订阅函数
   */
  subscribe(eventType, callback) {
    if (!this.listeners.has(eventType)) {
      this.listeners.set(eventType, new Set());
    }
    this.listeners.get(eventType).add(callback);

    return () => {
      const callbacks = this.listeners.get(eventType);
      if (callbacks) {
        callbacks.delete(callback);
      }
    };
  }

  /**
   * 订阅所有事件 (通配符)
   */
  subscribeAll(callback) {
    return this.subscribe('*', callback);
  }

  /**
   * 订阅 Agent 步骤事件
   */
  subscribeAgentSteps(callback) {
    const unsubStarted = this.subscribe('agent.step.started', callback);
    const unsubCompleted = this.subscribe('agent.step.completed', callback);
    const unsubFailed = this.subscribe('agent.step.failed', callback);

    return () => {
      unsubStarted();
      unsubCompleted();
      unsubFailed();
    };
  }

  /**
   * 订阅任务事件
   */
  subscribeTaskEvents(callback) {
    const unsubStarted = this.subscribe('task.started', callback);
    const unsubCompleted = this.subscribe('task.completed', callback);
    const unsubFailed = this.subscribe('task.failed', callback);

    return () => {
      unsubStarted();
      unsubCompleted();
      unsubFailed();
    };
  }

  /**
   * 订阅 Worker 状态事件
   */
  subscribeWorkerStatus(callback) {
    return this.subscribe('worker.status', callback);
  }

  /**
   * 内部: 处理收到的事件
   */
  _handleEvent(data, eventType) {
    // 触发特定类型监听器
    const specificListeners = this.listeners.get(eventType);
    if (specificListeners) {
      specificListeners.forEach(callback => {
        try {
          callback(data, eventType);
        } catch (err) {
          console.error(`[EventStream] 回调执行失败 (${eventType}):`, err);
        }
      });
    }

    // 触发通配符监听器
    const wildcardListeners = this.listeners.get('*');
    if (wildcardListeners) {
      wildcardListeners.forEach(callback => {
        try {
          callback(data, eventType);
        } catch (err) {
          console.error('[EventStream] 通配符回调执行失败:', err);
        }
      });
    }
  }

  /**
   * 内部: 触发事件
   */
  _emit(eventType, data) {
    const listeners = this.listeners.get(eventType);
    if (listeners) {
      listeners.forEach(callback => {
        try {
          callback(data, eventType);
        } catch (err) {
          console.error(`[EventStream] 内部事件回调失败 (${eventType}):`, err);
        }
      });
    }
  }

  /**
   * 内部: 尝试重连
   */
  _attemptReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('[EventStream] 达到最大重连次数，放弃重连');
      this._emit('connection.status', {
        status: 'failed',
        message: '达到最大重连次数'
      });
      return;
    }

    this.reconnectAttempts++;
    const delay = this.reconnectDelay * this.reconnectAttempts;
    console.log(`[EventStream] ${delay}ms 后尝试第 ${this.reconnectAttempts} 次重连...`);

    setTimeout(() => {
      if (!this.isConnected) {
        this.abortController = null;
        this.connect();
      }
    }, delay);
  }

  /**
   * 获取连接状态
   */
  getStatus() {
    return {
      isConnected: this.isConnected,
      reconnectAttempts: this.reconnectAttempts,
    };
  }
}

// 导出单例实例
export const eventStream = new EventStreamService();

// 导出便捷函数
export const connectEventStream = () => eventStream.connect();
export const disconnectEventStream = () => eventStream.disconnect();
export const subscribeToEvents = (eventType, callback) => eventStream.subscribe(eventType, callback);
export const subscribeToAgentSteps = (callback) => eventStream.subscribeAgentSteps(callback);
export const subscribeToTaskEvents = (callback) => eventStream.subscribeTaskEvents(callback);
export const subscribeToWorkerStatus = (callback) => eventStream.subscribeWorkerStatus(callback);
