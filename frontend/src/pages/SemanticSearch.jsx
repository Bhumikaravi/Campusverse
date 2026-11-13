import { useState } from "react";
import { Link } from "react-router-dom";
import {
  Search,
  Sparkles,
  BookOpen,
  FileText,
  ArrowRight,
  ExternalLink,
  Layers,
  HelpCircle,
} from "lucide-react";
import { searchApi } from "../services/endpoints";
import Loader from "../components/Loader";
import { useToast } from "../context/ToastContext";

const SAMPLE_QUERIES = [
  "Find notes about machine learning.",
  "Explain database normalization.",
  "Where is process scheduling explained?",
  "Find the definition of neural networks.",
  "What is Newton's law of motion?",
];

export default function SemanticSearch() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [searched, setSearched] = useState(false);
  const [loading, setLoading] = useState(false);
  const { showToast } = useToast();

  const handleSearch = async (searchQuery) => {
    const q = (searchQuery || query).trim();
    if (!q) {
      showToast("Please enter a question or search query.", "error");
      return;
    }

    setLoading(true);
    setSearched(true);
    try {
      const res = await searchApi.semantic(q, 10);
      setResults(res.data.results || []);
    } catch (err) {
      showToast(err.friendlyMessage || "Semantic search request failed.", "error");
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  const handleSampleClick = (sample) => {
    setQuery(sample);
    handleSearch(sample);
  };

  return (
    <div className="mx-auto max-w-5xl px-4 py-10 sm:px-6">
      {/* Header */}
      <div className="text-center max-w-2xl mx-auto space-y-3 mb-8">
        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-brand-100/90 text-brand-900 text-xs font-bold border border-brand-200">
          <Sparkles size={14} className="text-brand-600" />
          <span>AI-Powered Vector Semantic Search</span>
        </div>
        <h1 className="text-3xl font-extrabold text-white font-display">
          Search Academic Notes Naturally
        </h1>
        <p className="text-sm text-white/80">
          Ask full conceptual questions rather than exact keywords. Our embedding engine finds the most relevant document passages and page numbers.
        </p>
      </div>

      {/* Search Input Box */}
      <div className="card p-4 bg-white/95 rounded-2xl shadow-lg border border-white/40 mb-6">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSearch();
          }}
          className="flex items-center gap-2"
        >
          <div className="relative flex-1">
            <Search size={18} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Ask a question (e.g., Where is CPU scheduling explained?)..."
              className="input-field !pl-10 !py-3 w-full text-sm font-medium"
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="btn-primary !py-3 !px-6 flex items-center gap-2 shrink-0"
          >
            <Sparkles size={16} />
            <span>{loading ? "Searching..." : "Search"}</span>
          </button>
        </form>

        {/* Sample queries pills */}
        <div className="mt-3 flex flex-wrap items-center gap-2 pt-2 border-t border-gray-100 text-xs text-gray-500">
          <span className="font-semibold flex items-center gap-1">
            <HelpCircle size={12} /> Try asking:
          </span>
          {SAMPLE_QUERIES.map((sample, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => handleSampleClick(sample)}
              className="px-2.5 py-1 rounded-full bg-brand-50 hover:bg-brand-100 text-brand-900 font-medium text-[11px] border border-brand-200/60 transition"
            >
              {sample}
            </button>
          ))}
        </div>
      </div>

      {/* Results Container */}
      {loading ? (
        <div className="card p-12 bg-white/95 rounded-2xl shadow-md text-center">
          <Loader label="Comparing query embeddings against notes chunks..." />
        </div>
      ) : searched && results.length === 0 ? (
        <div className="card p-12 bg-white/95 rounded-2xl shadow-md text-center space-y-3">
          <FileText size={48} className="mx-auto text-gray-300" />
          <h3 className="font-bold text-gray-800 text-base">No Matching Notes Found</h3>
          <p className="text-xs text-gray-500 max-w-md mx-auto">
            We couldn't find semantically relevant chunks for your query. Try rephrasing your question or checking if notes on this topic have been uploaded.
          </p>
        </div>
      ) : (
        results.length > 0 && (
          <div className="space-y-4">
            <div className="flex items-center justify-between text-xs text-white/80 font-medium px-1">
              <span>Found {results.length} relevant passages</span>
              <span>Sorted by cosine similarity</span>
            </div>

            <div className="space-y-3">
              {results.map((res, idx) => (
                <div
                  key={idx}
                  className="card p-5 bg-white/95 rounded-2xl shadow-md border border-white/40 space-y-3 hover:shadow-lg transition"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="space-y-1">
                      <Link
                        to={`/materials/${res.materialId}`}
                        className="text-base font-bold text-brand-900 hover:text-brand-700 flex items-center gap-1.5 transition"
                      >
                        <FileText size={17} className="text-brand-600 shrink-0" />
                        <span>{res.title}</span>
                      </Link>
                      <div className="flex items-center gap-2 text-xs text-gray-500">
                        <span className="font-semibold px-2 py-0.5 rounded bg-brand-100 text-brand-900">
                          Page {res.pageNumber}
                        </span>
                        <span>•</span>
                        <span>Relevance Match: {Math.round(res.score * 100)}%</span>
                      </div>
                    </div>

                    <Link
                      to={`/materials/${res.materialId}`}
                      className="px-3 py-1.5 rounded-lg bg-brand-50 hover:bg-brand-100 text-brand-800 text-xs font-bold flex items-center gap-1 shrink-0 border border-brand-200 transition"
                    >
                      <span>Open Note</span>
                      <ArrowRight size={13} />
                    </Link>
                  </div>

                  <p className="text-xs leading-relaxed text-gray-700 bg-brand-50/40 p-3 rounded-xl border border-brand-100/60 font-mono">
                    "{res.snippet}"
                  </p>
                </div>
              ))}
            </div>
          </div>
        )
      )}
    </div>
  );
}
