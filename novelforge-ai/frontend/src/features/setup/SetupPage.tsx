import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchSetupStatus } from "../../shared/api/novelforge";

type Check = { key: string; label: string; status: "ok" | "warning" | "error"; message: string };
type SetupPayload = { ok: boolean; checks: Check[]; next_action?: { type: string; label: string } };

const STATUS_STYLE: Record<string, string> = {
  ok: "bg-green-50 text-green-700",
  warning: "bg-yellow-50 text-yellow-700",
  error: "bg-red-50 text-red-700",
};

export function SetupPage() {
  const [data, setData] = useState<SetupPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchSetupStatus();
      setData(res as SetupPayload);
    } catch (err) {
      setError(err instanceof Error ? err.message : "请求失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { void load(); }, []);

  const allOk = !!data?.ok && !loading && !error;

  return (
    <div className="mx-auto max-w-2xl px-4 py-16">
      <h1 className="mb-2 text-3xl font-bold text-gray-900">小说锻炉初始化</h1>
      <p className="mb-6 text-gray-500">让系统先跑通，再开始生产小说</p>

      <div className="mb-6 flex items-center gap-3">
        <button onClick={load} disabled={loading} className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:border-gray-400">
          {loading ? "检测中…" : "重新检测"}
        </button>
        {allOk && <Link to="/cockpit" className="rounded-lg bg-blue-600 px-5 py-2 text-sm font-semibold text-white hover:bg-blue-700">进入生产舱</Link>}
      </div>

      {error && <div className="mb-4 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">无法完成初始化检测：{error}</div>}

      {!loading && !error && data && (
        <div className="space-y-3">
          {data.checks.map((c) => (
            <div key={c.key} className="flex items-center justify-between rounded-xl border border-gray-200 bg-white p-4">
              <div>
                <span className="font-medium text-gray-900">{c.label}</span>
                <p className="mt-1 text-sm text-gray-500">{c.message}</p>
              </div>
              <span className={`rounded-full px-3 py-1 text-xs font-semibold ${STATUS_STYLE[c.status] ?? STATUS_STYLE.error}`}>
                {c.status === "ok" ? "正常" : c.status === "warning" ? "待处理" : "异常"}
              </span>
            </div>
          ))}
          {data.next_action && !allOk && (
            <p className="pt-2 text-sm text-gray-500">下一步建议：{data.next_action.label}</p>
          )}
        </div>
      )}
    </div>
  );
}
