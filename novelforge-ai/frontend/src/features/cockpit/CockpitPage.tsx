import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Play, Pause, Download, AlertTriangle, RefreshCcw } from "lucide-react";
import { fetchProjects, fetchProjectRuns, createProjectRun, executeRun } from "../../shared/api/novelforge";
import type { Project } from "../../shared/store";

type Run = {
  id: string;
  project_id: string;
  status: string;
  current_step: string | null;
  total_tokens: number;
  total_cost: number;
  error_message?: string;
};

export function CockpitPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [runs, setRuns] = useState<Run[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => { void loadProjects(); }, []);
  useEffect(() => { if (selectedId) void loadRuns(selectedId); }, [selectedId]);

  const loadProjects = async () => {
    setError(null);
    try {
      const list = await fetchProjects();
      setProjects(list);
      if (list.length && !selectedId) setSelectedId(list[0].id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "加载失败");
    }
  };

  const loadRuns = async (pid: string) => {
    try {
      const res = await fetchProjectRuns(pid);
      setRuns((res?.items ?? []) as Run[]);
    } catch (err) {
      console.error(err);
    }
  };

  const handleGenerate = async () => {
    if (!selectedId) return;
    try {
      const run = await createProjectRun(selectedId);
      await executeRun(run.id);
      await loadRuns(selectedId);
    } catch (err) {
      console.error(err);
    }
  };

  const selected = projects.find((p) => p.id === selectedId);

  return (
    <div className="mx-auto max-w-5xl px-4 py-10">
      <div className="mb-8 flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">小说生产舱</h1>
          {selected && <p className="mt-1 text-gray-500">当前项目：{selected.title} &nbsp;|&nbsp; 状态：{selected.status}</p>}
        </div>
        <div className="flex gap-2">
          <button onClick={handleGenerate} className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700"><span className="inline-flex items-center gap-2"><Play className="h-4 w-4" />生成下一章</span></button>
          <button className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:border-gray-400"><span className="inline-flex items-center gap-2"><Pause className="h-4 w-4" />暂停生产</span></button>
          <button className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:border-gray-400"><span className="inline-flex items-center gap-2"><Download className="h-4 w-4" />导出作品</span></button>
        </div>
      </div>

      {/* Project selector */}
      <div className="mb-6 flex flex-wrap gap-2">
        {projects.map((p) => (
          <button key={p.id} onClick={() => setSelectedId(p.id)} className={`rounded-lg border px-4 py-2 text-sm font-medium ${p.id === selectedId ? "border-blue-400 bg-blue-50 text-blue-700" : "border-gray-200 bg-white text-gray-700"}`}>
            {p.title}
          </button>
        ))}
        <Link to="/projects" className="rounded-lg border border-dashed border-gray-300 px-4 py-2 text-sm text-gray-500 hover:border-gray-400">+ 新建项目</Link>
      </div>

      {error && <div className="mb-4 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div>}

      {/* Agent Runs */}
      <SectionCard title="最近 Agent 运行">
        {runs.length === 0 ? <p className="text-sm text-gray-500">暂无运行记录</p> : (
          <div className="space-y-3">
            {runs.slice(0, 5).map((r) => (
              <div key={r.id} className="flex items-center justify-between rounded-lg border border-gray-100 bg-gray-50 p-3">
                <div>
                  <span className="text-sm font-medium text-gray-900">Run #{r.id.slice(0, 8)}</span>
                  <span className="ml-3 text-xs text-gray-500">步骤：{r.current_step ?? "-"}/{r.total_tokens} tokens</span>
                </div>
                <div className="flex items-center gap-3">
                  <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${r.status === "completed" ? "bg-green-50 text-green-700" : r.status === "failed" ? "bg-red-50 text-red-700" : r.status === "running" ? "bg-blue-50 text-blue-700" : "bg-gray-100 text-gray-600"}`}>{r.status}</span>
                  {r.status === "failed" && <button onClick={() => executeRun(r.id).then(() => loadRuns(r.project_id))} className="rounded-md bg-white px-2 py-1 text-xs text-amber-700 hover:bg-amber-50"><span className="inline-flex items-center gap-1"><RefreshCcw className="h-3 w-3" />重试</span></button>}
                </div>
              </div>
            ))}
          </div>
        )}
      </SectionCard>

      {/* Failures */}
      <SectionCard title="最近失败">
        {(() => {
          const failed = runs.filter((r) => r.status === "failed");
          if (!failed.length) return <p className="text-sm text-gray-500">暂无失败任务</p>;
          return (
            <div className="space-y-3">
              {failed.map((f) => (
                <div key={f.id} className="flex items-start justify-between rounded-lg border border-amber-200 bg-amber-50 p-3">
                  <div className="flex gap-2">
                    <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />
                    <div>
                      <p className="text-sm font-medium text-amber-900">Run #{f.id.slice(0, 8)} 失败</p>
                      <p className="text-xs text-amber-700">{f.error_message ?? "未知错误"}</p>
                    </div>
                  </div>
                  <button onClick={() => executeRun(f.id).then(() => loadRuns(f.project_id))} className="rounded-md bg-white px-3 py-1 text-xs font-medium text-amber-700 hover:bg-amber-100">重试</button>
                </div>
              ))}
            </div>
          );
        })()}
      </SectionCard>
    </div>
  );
}

function SectionCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mb-6 rounded-xl border border-gray-200 bg-white p-6">
      <h3 className="mb-4 text-sm font-semibold text-gray-500">{title}</h3>
      {children}
    </section>
  );
}
