export function Spinner({ label = "Loading…" }: { label?: string }) {
  return (
    <div role="status" className="flex items-center gap-2 text-sm text-gray-600">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-gray-300 border-t-gray-700" />
      {label}
    </div>
  );
}

export function ErrorMessage({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div role="alert" className="rounded border border-red-300 bg-red-50 p-3 text-sm text-red-900">
      <p>{message}</p>
      <button
        type="button"
        onClick={onRetry}
        className="mt-2 rounded bg-red-800 px-3 py-1 text-white hover:bg-red-900"
      >
        Retry
      </button>
    </div>
  );
}
