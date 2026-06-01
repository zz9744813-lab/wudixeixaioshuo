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

// ── Bible ──────────────────────────────────────────────────────────────────
export interface ProjectBible {
  id: string;
  project_id: string;
  selling_points: string | null;
  worldview: string | null;
  protagonist: string | null;
  characters: unknown[] | null;
  factions: unknown[] | null;
  power_system: string | null;
  plot_rules: string | null;
  style_guide: string | null;
  reader_expectation: string | null;
  forbidden_elements: string | null;
  version: number;
  created_at: string | null;
  updated_at: string | null;
}

export async function fetchBible(projectId: string): Promise<ProjectBible> {
  const { data } = await api.get(`/projects/${projectId}/bible`);
  return data as ProjectBible;
}

export async function updateBible(projectId: string, payload: Partial<ProjectBible>): Promise<ProjectBible> {
  const { data } = await api.patch(`/projects/${projectId}/bible`, payload);
  return data as ProjectBible;
}

// ── Outline ─────────────────────────────────────────────────────────────────
export interface OutlineNode {
  id: string;
  project_id: string;
  parent_id: string | null;
  node_type: string;
  order_index: number;
  title: string;
  summary: string | null;
  target_words: number | null;
  node_meta: Record<string, unknown> | null;
  children?: OutlineNode[];
}

export async function fetchOutlineTree(projectId: string): Promise<{ roots: OutlineNode[]; flat: OutlineNode[] }> {
  const { data } = await api.get(`/projects/${projectId}/outline`);
  return data as { roots: OutlineNode[]; flat: OutlineNode[] };
}

export async function createOutlineNode(projectId: string, payload: {
  parent_id?: string | null;
  node_type?: string;
  order_index?: number;
  title: string;
  summary?: string | null;
  target_words?: number | null;
  node_meta?: Record<string, unknown> | null;
}): Promise<OutlineNode> {
  const { data } = await api.post(`/projects/${projectId}/outline/nodes`, payload);
  return data as OutlineNode;
}

export async function updateOutlineNode(projectId: string, nodeId: string, payload: Partial<OutlineNode>): Promise<OutlineNode> {
  const { data } = await api.put(`/projects/${projectId}/outline/nodes/${nodeId}`, payload);
  return data as OutlineNode;
}

export async function deleteOutlineNode(projectId: string, nodeId: string): Promise<void> {
  await api.delete(`/projects/${projectId}/outline/nodes/${nodeId}`);
}

// ── Chapters ────────────────────────────────────────────────────────────────
export interface Chapter {
  id: string;
  project_id: string;
  chapter_index: number;
  title: string;
  summary: string | null;
  content: string | null;
  word_count: number;
  status: string;
  quality_score: number | null;
  continuity_score: number | null;
  locked: boolean;
  created_at: string | null;
  updated_at: string | null;
}

export async function fetchChapters(projectId: string): Promise<{ items: Chapter[]; total: number }> {
  const { data } = await api.get(`/projects/${projectId}/chapters`);
  return data as { items: Chapter[]; total: number };
}

export async function createChapter(projectId: string, payload: {
  chapter_index: number;
  title: string;
  summary?: string | null;
  target_words?: number;
}): Promise<Chapter> {
  const { data } = await api.post(`/projects/${projectId}/chapters`, { ...payload, project_id: projectId });
  return data as Chapter;
}

export async function updateChapter(projectId: string, chapterId: string, payload: Partial<Chapter>): Promise<Chapter> {
  const { data } = await api.put(`/projects/${projectId}/chapters/${chapterId}`, payload);
  return data as Chapter;
}

export async function deleteChapter(projectId: string, chapterId: string): Promise<void> {
  await api.delete(`/projects/${projectId}/chapters/${chapterId}`);
}

// ── Memory ──────────────────────────────────────────────────────────────────
export interface MemoryItem {
  id: string;
  project_id: string;
  chapter_id: string | null;
  item_type: string;
  content: string;
  embedding: number[] | null;
  tags: string[] | null;
  extra_meta: Record<string, unknown> | null;
  created_at: string | null;
  updated_at: string | null;
}

export async function fetchMemoryItems(projectId: string, itemType?: string): Promise<{ items: MemoryItem[]; total: number }> {
  const { data } = await api.get(`/projects/${projectId}/memory`, { params: itemType ? { item_type: itemType } : {} });
  return data as { items: MemoryItem[]; total: number };
}

// ── Foreshadow ──────────────────────────────────────────────────────────────
export interface ForeshadowItem {
  id: string;
  project_id: string;
  chapter_id: string | null;
  type: string;
  description: string;
  planted_chapter_index: number;
  resolved_chapter_index: number | null;
  resolution: string | null;
  status: string;
  priority: number;
  created_at: string | null;
  updated_at: string | null;
}

export async function fetchForeshadows(projectId: string, status?: string): Promise<{ items: ForeshadowItem[]; total: number }> {
  const { data } = await api.get(`/projects/${projectId}/foreshadows`, { params: status ? { status } : {} });
  return data as { items: ForeshadowItem[]; total: number };
}

export async function createMemoryItem(projectId: string, payload: {
  item_type: string;
  content: string;
  tags?: string[];
  extra_meta?: Record<string, unknown>;
  chapter_id?: string;
}): Promise<MemoryItem> {
  const { data } = await api.post(`/projects/${projectId}/memory`, { ...payload, project_id: projectId });
  return data as MemoryItem;
}

export async function deleteMemoryItem(projectId: string, itemId: string): Promise<void> {
  await api.delete(`/projects/${projectId}/memory/${itemId}`);
}

export async function createForeshadow(projectId: string, payload: {
  type?: string;
  description: string;
  planted_chapter_index: number;
  priority?: number;
  chapter_id?: string;
}): Promise<ForeshadowItem> {
  const { data } = await api.post(`/projects/${projectId}/foreshadows`, { ...payload, project_id: projectId });
  return data as ForeshadowItem;
}

export async function updateForeshadow(projectId: string, itemId: string, payload: Partial<ForeshadowItem>): Promise<ForeshadowItem> {
  const { data } = await api.put(`/projects/${projectId}/foreshadows/${itemId}`, payload);
  return data as ForeshadowItem;
}

export async function deleteForeshadow(projectId: string, itemId: string): Promise<void> {
  await api.delete(`/projects/${projectId}/foreshadows/${itemId}`);
}

// ── Export ───────────────────────────────────────────────────────────────────
export interface ExportData {
  project: Record<string, unknown>;
  chapters: { index: number; title: string; content: string | null; word_count: number; status: string }[];
  exported_at: string;
}

export async function exportProject(projectId: string): Promise<ExportData> {
  const { data } = await api.get(`/projects/${projectId}/export`);
  return data as ExportData;
}
