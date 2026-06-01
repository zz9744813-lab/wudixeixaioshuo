import { api } from "./client";
import type { Project } from "../store";

export async function fetchProjects(): Promise<Project[]> {
  const { data } = await api.get("/projects");
  const payload = data as { items?: Project[] } | Project[];
  if (Array.isArray(payload)) return payload;
  return payload.items ?? [];
}

export async function fetchProject(id: string): Promise<Project> {
  const { data } = await api.get(`/projects/${id}`);
  return data as Project;
}

export async function createProjectApi(payload: { title: string; genre?: string; description?: string }): Promise<Project> {
  const { data } = await api.post("/projects", payload);
  return data as Project;
}

export async function deleteProjectApi(id: string): Promise<void> {
  await api.delete(`/projects/${id}`);
}

export async function fetchSetupStatus(): Promise<{ ok: boolean; checks: { key: string; label: string; status: string; message: string }[]; next_action?: { type: string; label: string } }> {
  const { data } = await api.get("/setup/status");
  return data as { ok: boolean; checks: { key: string; label: string; status: string; message: string }[]; next_action?: { type: string; label: string } };
}

export async function fetchDiagnostics(): Promise<Record<string, unknown>> {
  const { data } = await api.get("/diagnostics");
  return data as Record<string, unknown>;
}

export interface AgentRun {
  id: string;
  project_id: string;
  status: string;
  chapter_id?: string;
  current_step: string | null;
  total_tokens: number;
  total_cost: number;
  error_message?: string;
}

export async function fetchProjectRuns(projectId: string): Promise<{ items: AgentRun[] }> {
  const { data } = await api.get(`/projects/${projectId}/runs`);
  return data as { items: AgentRun[] };
}

export async function createProjectRun(projectId: string, chapterIndex = 0): Promise<AgentRun> {
  const { data } = await api.post("/runs", { project_id: projectId, chapter_index: chapterIndex });
  return data as AgentRun;
}

export async function executeRun(runId: string): Promise<AgentRun> {
  const { data } = await api.post(`/runs/${runId}/execute`);
  return data as AgentRun;
}
