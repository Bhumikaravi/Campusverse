import { ChevronLeft, ChevronRight } from "lucide-react";

export default function Pagination({ page, totalPages, onChange }) {
  if (totalPages <= 1) return null;

  const pages = Array.from({ length: totalPages }, (_, i) => i + 1).filter(
    (p) => p === 1 || p === totalPages || Math.abs(p - page) <= 1
  );

  return (
    <div className="flex items-center justify-center gap-1 pt-6">
      <button
        disabled={page === 1}
        onClick={() => onChange(page - 1)}
        className="rounded-lg p-2 text-white hover:bg-white/20 disabled:opacity-30 transition"
      >
        <ChevronLeft size={18} />
      </button>

      {pages.map((p, i) => (
        <span key={p} className="flex items-center">
          {i > 0 && pages[i - 1] !== p - 1 && <span className="px-1 text-white/60">…</span>}
          <button
            onClick={() => onChange(p)}
            className={`h-9 w-9 rounded-lg text-sm font-medium transition ${
              p === page
                ? "bg-[#3e362e] text-white font-bold shadow-md"
                : "bg-white/25 text-white hover:bg-white/40 shadow-sm backdrop-blur"
            }`}
          >
            {p}
          </button>
        </span>
      ))}

      <button
        disabled={page === totalPages}
        onClick={() => onChange(page + 1)}
        className="rounded-lg p-2 text-white hover:bg-white/20 disabled:opacity-30 transition"
      >
        <ChevronRight size={18} />
      </button>
    </div>
  );
}
