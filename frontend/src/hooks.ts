import { useCallback, useEffect, useState } from "react";

interface FetchState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
}

/**
 * Run an async fetch whenever `deps` change. Returns the data, a loading flag, an error message
 * and a retry function. A newer request cancels the older one, so a slow old answer can never
 * overwrite a newer one. With keepPrevious the old data stays on screen while the new data loads.
 */
export function useFetch<T>(
  fetcher: (signal: AbortSignal) => Promise<T>,
  deps: unknown[],
  keepPrevious = false,
) {
  const [state, setState] = useState<FetchState<T>>({ data: null, loading: true, error: null });
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    setState((s) => ({ data: keepPrevious ? s.data : null, loading: true, error: null }));
    fetcher(controller.signal).then(
      (data) => {
        if (!controller.signal.aborted) setState({ data, loading: false, error: null });
      },
      (err: unknown) => {
        if (controller.signal.aborted) return;
        const message = err instanceof Error ? err.message : "Something went wrong.";
        setState((s) => ({ data: keepPrevious ? s.data : null, loading: false, error: message }));
      },
    );
    return () => controller.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, attempt]);

  const retry = useCallback(() => setAttempt((n) => n + 1), []);
  return { ...state, retry };
}
