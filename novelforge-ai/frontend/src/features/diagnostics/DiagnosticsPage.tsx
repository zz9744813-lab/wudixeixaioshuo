import { useEffect, useState } from "react";
import { api } from "../../shared/api/client";

type Diagnostic = Record<string, unknown>;

const STATE_STYLE: Record<string, string> = {
  ok: "bg-green-50 text-green-700",
  error: "bg-red-50 text-red-700",
  unknown: "bg-gray-100 text-gray-600",
};

export function DiagnosticsPage() {
  const [data, setData] = useState<Diagnostic | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void (async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await api.get("/diagnostics");
        setData(response.data as Diagnostic);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "请求失败");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const blob = JSON.stringify(data ?? {}, null, 2);
  const ts = data?.timestamp
    ? new Date(data.timestamp as string).toLocaleString("zh-CN")
    : "-";

  return (
    <div className="mx-auto max-w-3xl px-4 py-10">
      <h1 className="mb-6 text-3xl font-bold text-gray-900">系统诊断</h1>

      {error && (
        <div className="mb-6 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="mb-6 flex items-center justify-between">
        <p className="text-sm text-gray-500">诊断时间：{ts}</p>
        <CopyButton text={blob}>复制诊断包</CopyButton>
      </div>

      {!loading && !error && data ? (
        <div className="space-y-3">
          {Object.entries(data)
            .filter(([k]) => !k.startsWith("backend_"))
            .map(([key, value]) => {
              if (key === "timestamp") return null;
              const obj =
                typeof value === "object" && value !== null
                  ? (value as Record<string, unknown>)
                  : { status: "unknown" };
              const status = (obj.status as string) ?? "unknown";
              const style = STATE_STYLE[status] ?? STATE_STYLE.unknown;
              return (
                <div
                  key={key}
                  className="rounded-xl border border-gray-200 bg-white p-4"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-gray-900">{key}</span>
                    <span
                      className={`rounded-full px-3 py-1 text-xs font-semibold ${style}`}
                    >
                      {status}
                    </span>
                  </div>
                  {obj.message
                    ? <p className="mt-2 text-sm text-gray-500">{String(obj.message)}</p>
                    : null}
                </div>
              );
            })}
        </div>
      ) : null}
    </div>
  );
}

function CopyButton({
  text,
  children,
}: {
  text: string;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={() => void navigator.clipboard.writeText(text)}
      className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:border-gray-400"
    >
      {children}
    </button>
  );
}
