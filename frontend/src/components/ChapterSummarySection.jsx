import { useEffect, useState } from "react";
import {
  BookOpen,
  Sparkles,
  RefreshCw,
  Layers,
  ChevronDown,
  ChevronUp,
  Bookmark,
  CheckCircle2,
  FunctionSquare,
} from "lucide-react";
import { summariesApi } from "../services/endpoints";
import { useToast } from "../context/ToastContext";
import Loader from "./Loader";

export default function ChapterSummarySection({ materialId, materialTitle, subject, isOwnerOrAdmin }) {
  const { showToast } = useToast();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [regenerating, setRegenerating] = useState(false);
  const [expandedChapter, setExpandedChapter] = useState(1);

  const loadSummaries = () => {
    setLoading(true);
    summariesApi
      .getChapterSummaries(materialId)
      .then((res) => setData(res.data))
      .catch((err) => {
        // May not be available if not yet approved or processing
        setData(null);
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    if (materialId) loadSummaries();
  }, [materialId]);

  const handleRegenerate = async () => {
    setRegenerating(true);
    try {
      const res = await summariesApi.regenerate(materialId);
      setData(res.data.chapterSummaries || res.data);
      showToast("Chapter summaries regenerated successfully!", "success");
    } catch (err) {
      showToast(err.friendlyMessage || "Failed to regenerate summaries.", "error");
    } finally {
      setRegenerating(false);
    }
  };

  if (loading) {
    return (
      <div className="card mt-6 p-6 bg-white/95 rounded-2xl shadow-md border border-white/40">
        <Loader label="Generating chapter-wise breakdown & formulas..." />
      </div>
    );
  }

  const chapters = data?.chapters || [];

  return (
    <div className="card mt-6 p-6 bg-white/95 rounded-2xl shadow-md border border-white/40 space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-gray-100 pb-3 flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <div className="h-8 w-8 rounded-lg bg-brand-100 flex items-center justify-center text-brand-800">
            <BookOpen size={18} />
          </div>
          <div>
            <h3 className="text-base font-bold text-gray-900 flex items-center gap-2">
              <span>Chapter-Wise Summaries & Key Concepts</span>
              <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-brand-100 text-brand-800">
                {chapters.length} {chapters.length === 1 ? "Section" : "Chapters"}
              </span>
            </h3>
            <p className="text-xs text-gray-500">
              Grounded breakdown extracted directly from the notes content
            </p>
          </div>
        </div>

        {isOwnerOrAdmin && (
          <button
            onClick={handleRegenerate}
            disabled={regenerating}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-brand-200 text-xs font-semibold text-brand-800 hover:bg-brand-50 transition"
          >
            <RefreshCw size={12} className={regenerating ? "animate-spin" : ""} />
            <span>{regenerating ? "Regenerating..." : "Regenerate Breakdown"}</span>
          </button>
        )}
      </div>

      {chapters.length === 0 ? (
        <div className="text-center py-6 text-xs text-gray-500">
          No chapter breakdown available yet. Click "Regenerate" above to analyze document sections.
        </div>
      ) : (
        <div className="space-y-3">
          {chapters.map((ch) => {
            const isExpanded = expandedChapter === ch.chapterNumber;
            const definitions = ch.importantDefinitions || [];
            const formulas = ch.importantFormulas || [];
            const concepts = ch.keyConcepts || [];
            const summaryBullets = Array.isArray(ch.summary) ? ch.summary : [ch.summary];

            return (
              <div
                key={ch.chapterNumber}
                className="rounded-xl border border-gray-200 bg-white overflow-hidden transition shadow-2xs"
              >
                {/* Chapter Accordion Header */}
                <button
                  type="button"
                  onClick={() => setExpandedChapter(isExpanded ? null : ch.chapterNumber)}
                  className="w-full flex items-center justify-between p-4 text-left hover:bg-gray-50/60 transition"
                >
                  <div className="flex items-center gap-2.5">
                    <span className="flex h-6 w-6 items-center justify-center rounded-full bg-brand-100 text-brand-900 text-xs font-extrabold shrink-0">
                      {ch.chapterNumber}
                    </span>
                    <span className="font-bold text-sm text-gray-900">{ch.title}</span>
                    <span className="text-xs text-gray-400 font-medium">
                      (Pages {ch.startPage}–{ch.endPage})
                    </span>
                  </div>
                  {isExpanded ? <ChevronUp size={16} className="text-gray-400" /> : <ChevronDown size={16} className="text-gray-400" />}
                </button>

                {/* Chapter Details Body */}
                {isExpanded && (
                  <div className="p-4 pt-1 border-t border-gray-100 space-y-4 text-xs text-gray-700 bg-gray-50/30">
                    {/* Summary */}
                    <div>
                      <h4 className="font-bold text-gray-800 uppercase tracking-wider text-[11px] mb-1.5 flex items-center gap-1.5">
                        <Sparkles size={13} className="text-brand-600" />
                        Summary
                      </h4>
                      <ul className="space-y-1 pl-4 list-disc text-gray-700 leading-relaxed">
                        {summaryBullets.map((bullet, bIdx) => (
                          <li key={bIdx}>{bullet}</li>
                        ))}
                      </ul>
                    </div>

                    {/* Key Concepts */}
                    {concepts.length > 0 && (
                      <div>
                        <h4 className="font-bold text-gray-800 uppercase tracking-wider text-[11px] mb-1.5">
                          Key Concepts
                        </h4>
                        <div className="flex flex-wrap gap-1.5">
                          {concepts.map((c, cIdx) => (
                            <span
                              key={cIdx}
                              className="px-2.5 py-0.5 rounded-full bg-brand-50 border border-brand-200 text-brand-900 font-medium text-[11px]"
                            >
                              {c}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Important Definitions */}
                    {definitions.length > 0 && (
                      <div>
                        <h4 className="font-bold text-gray-800 uppercase tracking-wider text-[11px] mb-1.5">
                          Important Definitions
                        </h4>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                          {definitions.map((d, dIdx) => (
                            <div key={dIdx} className="p-2.5 rounded-lg bg-white border border-gray-200 shadow-2xs">
                              <span className="font-bold text-gray-900 block mb-0.5">{d.term}</span>
                              <span className="text-gray-600 leading-snug">{d.definition}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Important Formulas */}
                    {formulas.length > 0 && (
                      <div>
                        <h4 className="font-bold text-gray-800 uppercase tracking-wider text-[11px] mb-1.5 flex items-center gap-1.5">
                          <FunctionSquare size={13} className="text-brand-600" />
                          Important Formulas & Complexity
                        </h4>
                        <div className="space-y-1">
                          {formulas.map((f, fIdx) => (
                            <div
                              key={fIdx}
                              className="font-mono text-[11px] bg-white p-2 rounded-lg border border-gray-200 text-brand-900 font-semibold"
                            >
                              {f}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
