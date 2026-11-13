import { Loader2 } from "lucide-react";

export default function Loader({ label = "Loading...", size = 22 }) {
  return (
    <div className="flex flex-col items-center gap-2 py-10 text-gray-500 dark:text-gray-400">
      <Loader2 size={size} className="animate-spin text-brand-600" />
      {label && <span className="text-sm">{label}</span>}
    </div>
  );
}

export function CardSkeleton() {
  return (
    <div className="card animate-pulse overflow-hidden">
      <div className="h-36 bg-gray-200 dark:bg-gray-800" />
      <div className="space-y-2 p-4">
        <div className="h-3 w-2/3 rounded bg-gray-200 dark:bg-gray-800" />
        <div className="h-3 w-1/2 rounded bg-gray-200 dark:bg-gray-800" />
        <div className="h-3 w-1/3 rounded bg-gray-200 dark:bg-gray-800" />
      </div>
    </div>
  );
}
