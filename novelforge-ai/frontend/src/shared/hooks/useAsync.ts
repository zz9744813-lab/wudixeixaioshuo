import { useEffect, useState, useCallback } from "react";

export function useAsync(fn, deps = []) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [data, setData] = useState(null);

  const execute = useCallback(
    async (...args) => {
      setLoading(true);
      setError(null);
      try {
        const result = await fn(...args);
        setData(result);
        return result;
      } catch (err) {
        setError(err);
        throw err;
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
