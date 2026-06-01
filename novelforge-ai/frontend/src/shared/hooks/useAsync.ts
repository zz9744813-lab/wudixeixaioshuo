import { useEffect, useState, useCallback } from "react";

export function useAsync<T = unknown>(fn: (...args: unknown[]) => Promise<T>, deps: unknown[] = []) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [data, setData] = useState<T | null>(null);

  const execute = useCallback(
    async (...args: unknown[]) => {
      setLoading(true);
      setError(null);
      try {
        const result = await fn(...args);
        setData(result as T);
        return result;
      } catch (err) {
        const e = err instanceof Error ? err : new Error(String(err));
        setError(e);
        throw e;
      } finally {
        setLoading(false);
      }
    },
    deps
  );

  useEffect(() => {
    if (deps.length && deps.every(Boolean)) {
      execute();
    }
  }, deps);

  return { data, loading, error, execute };
}
