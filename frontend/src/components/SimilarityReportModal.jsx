import {
  ShieldAlert,
  CheckCircle2,
  AlertTriangle,
  FileText,
  Copy,
  Info,
  ExternalLink,
} from "lucide-react";
import Modal from "./Modal";

export default function SimilarityReportModal({ isOpen, onClose, report, materialTitle }) {
  if (!report) return null;

  const isDup = report.isDuplicate;
  const matches = report.matches || [];
  const scorePercent = report.similarityPercentage || `${Math.round((report.overallSimilarityScore || 0) * 100)}%`;

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="AI Document Similarity & Plagiarism Report">
      <div className="space-y-5 text-gray-800">
        {/* Banner */}
        <div
          className={`flex items-center justify-between rounded-xl p-4 border ${
            isDup
              ? "bg-red-50 border-red-200 text-red-900"
              : matches.length > 0
              ? "bg-amber-50 border-amber-200 text-amber-900"
              : "bg-emerald-50 border-emerald-200 text-emerald-900"
          }`}
        >
          <div className="flex items-center gap-3">
            {isDup ? (
              <ShieldAlert size={26} className="text-red-600 shrink-0" />
            ) : matches.length > 0 ? (
              <AlertTriangle size={26} className="text-amber-600 shrink-0" />
            ) : (
              <CheckCircle2 size={26} className="text-emerald-600 shrink-0" />
            )}
            <div>
              <h3 className="font-bold text-sm">Similarity Finding: {report.similarityType || "Unique Content"}</h3>
              <p className="text-xs opacity-90">{report.explanation}</p>
            </div>
          </div>
          <div className="text-right">
            <span className="text-xs font-semibold uppercase tracking-wider block opacity-75">Max Match</span>
            <span className="text-xl font-extrabold">{scorePercent}</span>
          </div>
        </div>

        {/* Note title & Analysis Methods */}
        <div className="text-xs text-gray-500 font-medium">
          Checked Document: <span className="font-bold text-gray-800">{materialTitle}</span>
          {" • "}Checked against <strong className="text-gray-700">{report.checkedAgainstCount || 0}</strong> existing authorized notes.
        </div>

        {/* Dual-Method Detection Pipeline Badges */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
          <div className="p-3 bg-gray-50 rounded-xl border border-gray-200">
            <div className="font-bold text-gray-800 flex items-center gap-1.5 mb-1">
              <span className="w-2 h-2 rounded-full bg-brand-600 inline-block"></span>
              File Hashes (Exact Duplicates)
            </div>
            <p className="text-gray-600 text-[11px]">
              {isDup && report.similarityType?.toLowerCase().includes("sha-256")
                ? "Exact binary match detected via SHA-256 cryptographic hash."
                : "SHA-256 hash verified: No identical file previously uploaded."}
            </p>
          </div>
          <div className="p-3 bg-gray-50 rounded-xl border border-gray-200">
            <div className="font-bold text-gray-800 flex items-center gap-1.5 mb-1">
              <span className="w-2 h-2 rounded-full bg-brand-600 inline-block"></span>
              Text Similarity & Document Embeddings
            </div>
            <p className="text-gray-600 text-[11px]">
              Jaccard n-gram overlap & 128-d dense vector cosine similarity analysis completed.
            </p>
          </div>
        </div>

        {/* Matching Documents List */}
        <div>
          <h4 className="text-xs font-bold uppercase tracking-wider text-gray-700 mb-2">
            Potential Matches & Overlapping Passages ({matches.length})
          </h4>

          {matches.length === 0 ? (
            <div className="rounded-xl border border-gray-200 bg-gray-50 p-4 text-center text-xs text-gray-500">
              No significant textual or semantic similarity detected against the authorized dataset.
            </div>
          ) : (
            <div className="space-y-3 max-h-72 overflow-y-auto pr-1">
              {matches.map((match, mIdx) => (
                <div key={mIdx} className="rounded-xl border border-gray-200 bg-white p-3 shadow-xs space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <FileText size={16} className="text-brand-600" />
                      <span className="text-xs font-bold text-gray-900">{match.targetTitle}</span>
                    </div>
                    <span
                      className={`text-xs font-extrabold px-2 py-0.5 rounded-full ${
                        match.similarityScore >= 0.85
                          ? "bg-red-100 text-red-800"
                          : match.similarityScore >= 0.60
                          ? "bg-amber-100 text-amber-800"
                          : "bg-blue-100 text-blue-800"
                      }`}
                    >
                      {match.similarityType}: {Math.round(match.similarityScore * 100)}%
                    </span>
                  </div>

                  {/* Matching Passages */}
                  {match.matchingPassages?.map((p, pIdx) => (
                    <div key={pIdx} className="rounded-lg bg-gray-50 p-2.5 text-xs border border-gray-100 space-y-1">
                      <div className="flex items-center justify-between text-gray-500 font-medium text-[11px]">
                        <span>Current Note (Page {p.sourcePage})</span>
                        <span className="text-brand-700 font-bold">{p.passageType}</span>
                        <span>Existing Note (Page {p.targetPage})</span>
                      </div>
                      <div className="grid grid-cols-2 gap-2 text-gray-700">
                        <div className="bg-white p-2 rounded border border-gray-100 italic">
                          "{p.sourceSnippet}"
                        </div>
                        <div className="bg-white p-2 rounded border border-gray-100 italic">
                          "{p.targetSnippet}"
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Disclaimer */}
        <div className="rounded-lg bg-blue-50/70 border border-blue-200/60 p-2.5 text-[11px] text-blue-900 flex items-start gap-2">
          <Info size={14} className="shrink-0 mt-0.5 text-blue-600" />
          <span>
            <strong>Academic Note:</strong> High semantic similarity represents overlapping syllabus concepts or lecture topics, and does not definitively indicate plagiarism without administrative review.
          </span>
        </div>

        {/* Footer */}
        <div className="flex justify-end border-t border-gray-100 pt-3">
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg bg-gray-200 hover:bg-gray-300 text-gray-800 font-semibold text-xs"
          >
            Close Report
          </button>
        </div>
      </div>
    </Modal>
  );
}
