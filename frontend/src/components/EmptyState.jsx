import { FileQuestion, AlertTriangle } from "lucide-react";

export function EmptyState({ title = "Nothing here yet", message, icon: Icon = FileQuestion, action }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-xl border border-dashed border-gray-300 py-16 text-center dark:border-gray-700">
      <Icon size={36} className="text-gray-400" />
      <p className="font-semibold text-gray-700 dark:text-gray-200">{title}</p>
      {message && <p className="max-w-xs text-sm text-gray-500 dark:text-gray-400">{message}</p>}
      {action}
    </div>
  );
}

export function ErrorState({ message = "Something went wrong. Please try again.", onRetry }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-xl border border-red-200 bg-red-50 py-16 text-center dark:border-red-900 dark:bg-red-950">
      <AlertTriangle size={32} className="text-red-500" />
      <p className="text-sm font-medium text-red-700 dark:text-red-300">{message}</p>
      {onRetry && (
        <button onClick={onRetry} className="btn-secondary mt-2">
          Try again
        </button>
      )}
    </div>
  );
}
