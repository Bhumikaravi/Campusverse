import { Link } from "react-router-dom";
import { Compass } from "lucide-react";

export default function NotFound() {
  return (
    <div className="flex min-h-[70vh] flex-col items-center justify-center px-4 text-center">
      <Compass size={40} className="mb-4 text-brand-400" />
      <h1 className="font-display text-4xl font-bold">404</h1>
      <p className="mt-2 text-gray-500 dark:text-gray-400">
        This page doesn't exist, or has moved.
      </p>
      <Link to="/" className="btn-primary mt-6">
        Back to home
      </Link>
    </div>
  );
}
