import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Play, Pause, Download, RefreshCcw, AlertTriangle } from "lucide-react";

type AgentStep = { name: string; status: "ok" | "running" | "waiting"; label?: string };
type QueueItem = { chapter: string; status: "running" | "pending" | "failed" };
type FailedTask = { chapter: string; reason: string };

export function CockpitPage() {
  const navigate = useNavigate();
  const [project] = useState({ title: "《苍穹之刃》", todayWords: 8720, todayCost: 1.24, targetWords: 10000 });

  const systemStatus = [
    { label: "后端", ok: true },
    { label: "数据库", ok: true },
    { label: "Redis", ok: true },
    { label: "Worker", ok: true },
    { label: "模型", ok: true },
  ];

  const agentRun: AgentStep[] = [
    { name: "Planner", status: "ok", label: "已完成" },
    { name: "Draft", status: "running", label: "第 12 章起草中…" },
    { name: "Critic", status: "waiting" },
    { name: "Rewrite", status: "waiting" },
    { name: "Continuity", status: "waiting" },
    { name: "Memory", status: "waiting" },
  ];

  const queue: QueueItem[] = [
    { chapter: "第 12 章", status: "running" },
    { chapter: "第 13 章", status: "pending" },
    { chapter: "第 14 章", status: "pending" },
  ];

  const failures: FailedTask[] = [
    { chapter: "第 11 章", reason: "Draft 失败：模型超时" },
  ];

  return (
    <div className="mx-auto max-w-5xl px-4 py-10">
      <div className="mb-8 flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">小说生产舱</h1>
          <p className="mt-1 text-gray-500">
            当前项目：{project.title} &nbsp;|&nbsp; 今日目标：{project.targetWords.toLocaleString()}字 &nbsp;|&nbsp; 今日成本：${project.todayCost}
          </p>
        </div>
        <div className="flex gap-2">
          <button onClick={() => {}} className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700">
            <span className="inline-flex items-center gap-2"><Play className="h-4 w-4" />生成下一章</span>
          </button>
          <button onClick={() => {}} className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:border-gray-400">
            <span className="inline-flex items-center gap-2"><Pause className="h-4 w-4" />暂停生产</span>
          </button>
          <button onClick={() => {}} className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:border-gray-400">
            <span className="inline-flex items-center gap-2"><Download className="h-4 w-4" />导出作品</span>
          </button>
        </div>
      </div>

      {/* Status */}
      <div className="mb-6 rounded-xl border border-gray-200 bg-white p-4">
        <p className="text-sm font-medium text-gray-500">系统状态</p>
        <div className="mt-3 flex flex-wrap gap-3">
          {systemStatus.map((s) => (
            <span key={s.label} className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold ${s.ok ? "bg-green-50 text-green-700" : "bg-red-50 text-red-700"}`}>
              {s.ok ? "✅" : "❌"} {s.label}
            </span>
          ))}
        </div>
      </div>

      {/* Agent Run */}
      <SectionCard title="当前 Agent Run">
        <div className="flex items-center gap-2">
          {agentRun.map((s, i) => (
            <span key={s.name} className="flex items-center gap-1 text-sm">
              <span
                className={
                  s.status === "ok"
                    ? "text-green-700"
                    : s.status === "running"
                      ? "font-semibold text-blue-700"
                      : "text-gray-400"
                }
              >
                {s.label ?? s.name}
              </span>
              {i < agentRun.length - 1 && <span className="text-gray-400">→</span>}
            </span>
          ))}
        </div>
        <p className="mt-3 rounded-lg bg-gray-50 p-3 text-sm text-gray-600">
          正在生成第 12 章……
        </p>
      </SectionCard>

      {/* Queue */}
      <SectionCard title="章节队列">
        <div className="flex gap-3">
          {queue.map((q) => (
            <span
              key={q.chapter}
              className={`rounded-lg border px-3 py-2 text-sm font-medium ${
                q.status === "running"
                  ? "border-blue-200 bg-blue-50 text-blue-700"
                  : "border-gray-200 bg-white text-gray-600"
              }`}
            >
              {q.chapter} {q.status === "running" ? "running" : "pending"}
            </span>
          ))}
        </div>
      </SectionCard>

      {/* Failures */}
      <SectionCard title="最近失败">
        {failures.length === 0 ? (
          <p className="text-sm text-gray-500">暂无失败任务</p>
        ) : (
          <div className="space-y-3">
            {failures.map((f) => (
              <div key={f.chapter} className="flex items-start justify-between rounded-lg border border-amber-200 bg-amber-50 p-3">
                <div className="flex gap-2">
                  <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />
                  <div>
                    <p className="text-sm font-medium text-amber-900">{f.chapter}：{f.reason}</p>
                  </div>
                </div>
                <div className="flex gap-2">
                  <button className="rounded-md bg-white px-3 py-1 text-xs font-medium text-amber-700 hover:bg-amber-100">
                    <span className="inline-flex items-center gap-1"><RefreshCcw className="h-3 w-3" />重试</span>
                  </button>
                  <button className="rounded-md bg-white px-3 py-1 text-xs font-medium text-amber-700 hover:bg-amber-100">
                    换模型
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
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
