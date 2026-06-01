import { create } from 'zustand';

export type Project = {
  id: string;
  title: string;
  genre?: string;
  status: string;
  current_chapter_index: number;
  chapters_count?: number;
  created_at?: string;
};

type UiState = {
  sidebarOpen: boolean;
  toggleSidebar: () => void;
  activeProjectId: string | null;
  setActiveProject: (id: string | null) => void;
};

export const useProjectStore = create<{ projects: Project[]; setProjects: (p: Project[]) => void; addProject: (p: Project) => void; updateProject: (id: string, patch: Partial<Project>) => void; removeProject: (id: string) => void }>((set) => ({
  projects: [],
  setProjects: (projects) => set({ projects }),
  addProject: (project) => set((s) => ({ projects: [project, ...s.projects] })),
  updateProject: (id, patch) => set((s) => ({ projects: s.projects.map((p) => (p.id === id ? { ...p, ...patch } : p)) })),
  removeProject: (id) => set((s) => ({ projects: s.projects.filter((p) => p.id !== id) })),
}));

export const useUiStore = create<UiState>((set) => ({
  sidebarOpen: true,
  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
  activeProjectId: null,
  setActiveProject: (id) => set({ activeProjectId: id }),
}));
