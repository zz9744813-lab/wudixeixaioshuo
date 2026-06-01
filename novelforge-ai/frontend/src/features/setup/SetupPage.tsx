import { useEffect, useState } from "react";
import { api } from "../shared/api/client";
import { useNavigate } from "react-router-dom";

type Check = {
  key: string;
  label: string;
  status: "ok" | "warning" | "error";
  message: string;
};

type SetupPayload = {
  ok: boolean;
  checks: Check[];
  next_action?: { type: string; label: string };
};

const STATUS_META: Record<string, { color: string; label: string }> = {
  ok: { color: "text-green-700 bg-green-50", label: "正常" },
  warning: { color: "text-yellow-700 bg-yellow-50", label: "待处理" },
  error: { color: "text-red-700 bg-red-50", label: "异常" },
};

export function SetupPage() {
  const [data, setData] = useState<SetupPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const { data } = await api.get("/setup/status");
      setData(data as SetupPayload);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "请求失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const allReady = data?.ok && !loading && !error;

  return (
    <div className="mx-auto max-w-2xl px-4 py-16">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">小说锻炉初始化</h1>
        <p className="mt-2 text-gray-500">让系统先跑通，再开始生产小说</p>
      </div>

      <div className="mb-6 flex items-center gap-3">
        <button
          onClick={() => void load()}
          className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:border-gray-400"
          disabled={loading}
        >
          {loading ? "检测中…" : "重新检测"}
        </button>

        {allReady && (
          <button
            onClick={() => navigate("/cockpit")}
            className="rounded-lg bg-blue-600 px-5 py-2 text-sm font-semibold text-white hover:bg-blue-700"
          >
            进入生产舱
          </button>
        )}
      </div>

      {error && <ErrorBanner message={error} />}

      {!loading && !error && data && (
        <div className="space-y-3">
          {data.checks.map((c) => {
            const meta = STATUS_META[c.status] ?? STATUS_META.error;
            return (
              <div key={c.key} className="flex items-center justify-between rounded-xl border border-gray-200 bg-white p-4">
                <div>
                  <span className="font-medium text-gray-900">{c.label}</span>
                  <p className="mt-1 text-sm text-gray-500">{c.message}</p>
                </div>
                <span className={`rounded-full px-3 py-1 text-xs font-semibold ${meta.color}`}>
                  {meta.label}
                </span>
              </div>
            );
          })}

          {data.next_action && !allReady && (
            <p className="pt-4 text-sm text-gray-500">
              {data.next_action.type === "configure_model" && (
                <span>下一步建议：{data.next_action.label}</span>
              )}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

function ErrorBanner({ message }: { message: string }) {
  return (
    <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-red-700">
      <p className="text-sm font-medium">无法完成初始化检测</p>
      <p className="mt-1 text-sm">{message}</p>
    </div>
  );
}
