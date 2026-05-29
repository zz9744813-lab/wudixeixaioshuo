/**
 * EventStream Service - SSE 实时事件流客户端
 * 用于接收 Worker 和 Agent 的实时进度推送
 */

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

class EventStreamService {
  constructor() {
    this.eventSource = null;
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
    if (this.eventSource) {
      console.log('[EventStream] 已连接，跳过重复连接');
      return;
    }

    const streamUrl = `${API_BASE_URL}/api/events/stream`;
    console.log('[EventStream] 正在连接到:', streamUrl);

    try {
      this.eventSource = new EventSource(streamUrl);

      this.eventSource.onopen = () => {
        console.log('[EventStream] 连接已建立');
        this.isConnected = true;
        this.reconnectAttempts = 0;
        this._emit('connection.status', { status: 'connected' });
      };

      // 使用具名事件监听 (SSE 命名事件)
      const eventTypes = [
        'worker.status',
        'task.started',
        'task.completed',
        'task.failed',
        'agent.step.started',
        'agent.step.completed',
        'agent.step.failed'
      ];

      eventTypes.forEach((type) => {
        this.eventSource.addEventListener(type, (event) => {
          try {
            const data = JSON.parse(event.data);
            console.log(`[EventStream] 收到 ${type}:`, data);
            this._emit(type, data);
            this._emit('*', { type, data });
          } catch (err) {
            console.error(`[EventStream] 解析 ${type} 失败:`, err, event.data);
          }
        });
      });

      // onmessage 作为兜底，处理非命名消息
      this.eventSource.onmessage = (event) => {
        console.log('[EventStream] 收到未命名消息:', event.data);
        try {
          const data = JSON.parse(event.data);
          this._handleEvent(data);
        } catch (err) {
          console.error('[EventStream] 解析消息失败:', err, event.data);
        }
      };

      this.eventSource.onerror = (error) => {
        console.error('[EventStream] 连接错误:', error);
        this.isConnected = false;
        this._emit('connection.status', { status: 'error', error });
        this._attemptReconnect();
      };
    } catch (err) {
      console.error('[EventStream] 创建连接失败:', err);
      this._attemptReconnect();
    }
  }

  /**
   * 断开 SSE 连接
   */
  disconnect() {
    if (this.eventSource) {
      console.log('[EventStream] 断开连接');
      this.eventSource.close();
      this.eventSource = null;
      this.isConnected = false;
      this._emit('connection.status', { status: 'disconnected' });
    }
  }

  /**
   * 订阅事件
   * @param {string} eventType - 事件类型 (如: 'agent.step.started', 'task.completed')
   * @param {function} callback - 回调函数
   * @returns {function} 取消订阅函数
   */
  subscribe(eventType, callback) {
    if (!this.listeners.has(eventType)) {
      this.listeners.set(eventType, new Set());
    }
    this.listeners.get(eventType).add(callback);

    // 返回取消订阅函数
    return () => {
      const callbacks = this.listeners.get(eventType);
      if (callbacks) {
        callbacks.delete(callback);
      }
    };
  }

  /**
   * 订阅所有事件 (通配符)
   * @param {function} callback - 回调函数
   * @returns {function} 取消订阅函数
   */
  subscribeAll(callback) {
    return this.subscribe('*', callback);
  }

  /**
   * 订阅 Agent 步骤事件
   * @param {function} callback - 回调函数
   * @returns {function} 取消订阅函数
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
   * @param {function} callback - 回调函数
   * @returns {function} 取消订阅函数
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
   * @param {function} callback - 回调函数
   * @returns {function} 取消订阅函数
   */
  subscribeWorkerStatus(callback) {
    return this.subscribe('worker.status', callback);
  }

  /**
   * 内部: 处理收到的事件
   */
  _handleEvent(event) {
    const { type, data } = event;

    // 触发特定类型监听器
    const specificListeners = this.listeners.get(type);
    if (specificListeners) {
      specificListeners.forEach(callback => {
        try {
          callback(data, type);
        } catch (err) {
          console.error(`[EventStream] 回调执行失败 (${type}):`, err);
        }
      });
    }

    // 触发通配符监听器
    const wildcardListeners = this.listeners.get('*');
    if (wildcardListeners) {
      wildcardListeners.forEach(callback => {
        try {
          callback(data, type);
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
        this.eventSource = null;
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
