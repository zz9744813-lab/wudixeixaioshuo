/**
 * WorkerService - Worker API 服务
 */
import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || '';

interface WorkerControlRequest {
  action: 'start' | 'stop' | 'pause' | 'resume';
}

interface WorkerStatus {
  status: string;
  current_task?: any;
  daily_stats: {
    words_written: number;
    chapters_completed: number;
    tokens_used: number;
    cost: number;
  };
}

interface QueueAddRequest {
  project_id: number;
  chapter_ids?: number[];
}

interface QueueStatus {
  total: number;
  pending: number;
  running: number;
  completed: number;
  failed: number;
  items: any[];
}

interface WorkerStats {
  worker: WorkerStatus;
  queue: QueueStatus;
  overall_progress: any;
}

class WorkerService {
  private getHeaders() {
    const apiKey = localStorage.getItem('api_key') || '';
    return {
      'X-API-Key': apiKey,
    };
  }

  async controlWorker(action: WorkerControlRequest['action']) {
    const response = await axios.post(
      `${API_BASE_URL}/api/worker/control`,
      { action },
      { headers: this.getHeaders() }
    );
    return response.data;
  }

  async getWorkerStatus(): Promise<WorkerStatus> {
    const response = await axios.get(
      `${API_BASE_URL}/api/worker/status`,
      { headers: this.getHeaders() }
    );
    return response.data;
  }

  async getWorkerStats(): Promise<WorkerStats> {
    const response = await axios.get(
      `${API_BASE_URL}/api/worker/stats`,
      { headers: this.getHeaders() }
    );
    return response.data;
  }

  async resetDailyStats() {
    const response = await axios.post(
      `${API_BASE_URL}/api/worker/reset-stats`,
      {},
      { headers: this.getHeaders() }
    );
    return response.data;
  }

  async getQueueStatus(project_id?: number): Promise<QueueStatus> {
    const params = project_id ? { project_id } : {};
    const response = await axios.get(
      `${API_BASE_URL}/api/worker/queue/status`,
      { params, headers: this.getHeaders() }
    );
    return response.data;
  }

  async addToQueue(request: QueueAddRequest) {
    const response = await axios.post(
      `${API_BASE_URL}/api/worker/queue/add`,
      request,
      { headers: this.getHeaders() }
    );
    return response.data;
  }

  async removeFromQueue(chapter_id: number) {
    const response = await axios.delete(
      `${API_BASE_URL}/api/worker/queue/${chapter_id}`,
      { headers: this.getHeaders() }
    );
    return response.data;
  }

  async clearFailed(project_id?: number) {
    const response = await axios.post(
      `${API_BASE_URL}/api/worker/queue/clear-failed`,
      {},
      { params: project_id ? { project_id } : {}, headers: this.getHeaders() }
    );
    return response.data;
  }

  async getWritingPlan(project_id: number) {
    const response = await axios.get(
      `${API_BASE_URL}/api/worker/plan/${project_id}`,
      { headers: this.getHeaders() }
    );
    return response.data;
  }

  async getWorkerConfig() {
    const response = await axios.get(
      `${API_BASE_URL}/api/worker/config`,
      { headers: this.getHeaders() }
    );
    return response.data;
  }
}

export const workerService = new WorkerService();
