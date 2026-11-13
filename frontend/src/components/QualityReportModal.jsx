import {
  FileCheck,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Copy,
  BookOpen,
  Info,
  Layers,
  Sparkles,
} from "lucide-react";
import Modal from "./Modal";

export default function QualityReportModal({ isOpen, onClose, report, materialTitle }) {
  if (!report) return null;

  const isPassed = report.overallStatus === "Quality Check Passed";
  const readability = report.readability || {};
  const blankPages = report.blankPages || { count: 0, pageNumbers: [] };
  const duplicatePages = report.duplicatePages || { count: 0, pageNumbers: [], groups: [] };
  const subjectRelevance = report.subjectRelevance || {};
  const completeness = report.completeness || { warnings: [] };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="AI Document Quality Analysis">
      <div className="space-y-5 text-gray-800">
        {/* Header summary banner */}
        <div
          className={`flex items-center justify-between rounded-xl p-4 border ${
            isPassed
              ? "bg-emerald-50 border-emerald-200 text-emerald-900"
              : "bg-amber-50 border-amber-200 text-amber-900"
          }`}
        >
          <div className="flex items-center gap-3">
            {isPassed ? (
              <CheckCircle2 size={24} className="text-emerald-600 shrink-0" />
            ) : (
              <AlertTriangle size={24} className="text-amber-600 shrink-0" />
            )}
            <div>
              <h3 className="font-bold text-sm">Overall Status: {report.overallStatus}</h3>
              <p className="text-xs opacity-90">
                {isPassed
                  ? "Document passed automated quality benchmarks."
                  : "Flags detected. Admin inspection recommended before final approval."}
              </p>
            </div>
          </div>
          <div className="text-right">
            <span className="text-xs font-semibold uppercase tracking-wider block opacity-75">Score</span>
            <span className="text-xl font-extrabold">{report.qualityScore ?? 85}/100</span>
          </div>
        </div>

        {/* Document Title */}
        <div className="text-xs text-gray-500 font-medium">
          Inspecting: <span className="font-bold text-gray-800">{materialTitle}</span>
        </div>

        {/* 5-Dimension Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {/* A. Blank Pages */}
          <div className="rounded-xl border border-gray-200 bg-gray-50/70 p-3.5 space-y-1.5">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-gray-700 flex items-center gap-1.5">
                <Layers size={14} className="text-brand-600" />
                Pages Blank
              </span>
              <span
                className={`text-xs font-bold px-2 py-0.5 rounded-full ${
                  blankPages.count === 0
                    ? "bg-emerald-100 text-emerald-800"
                    : "bg-amber-100 text-amber-800"
                }`}
              >
                {blankPages.count} {blankPages.count === 1 ? "page" : "pages"}
              </span>
            </div>
            <p className="text-xs text-gray-600">
              {blankPages.count === 0
                ? "No blank pages detected across the document."
                : `Blank or non-text content on page(s): ${blankPages.pageNumbers.join(", ")}`}
            </p>
          </div>

          {/* B. Duplicate Pages */}
          <div className="rounded-xl border border-gray-200 bg-gray-50/70 p-3.5 space-y-1.5">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-gray-700 flex items-center gap-1.5">
                <Copy size={14} className="text-brand-600" />
                Pages Duplicated
              </span>
              <span
                className={`text-xs font-bold px-2 py-0.5 rounded-full ${
                  duplicatePages.count === 0
                    ? "bg-emerald-100 text-emerald-800"
                    : "bg-amber-100 text-amber-800"
                }`}
              >
                {duplicatePages.count} {duplicatePages.count === 1 ? "page" : "pages"}
              </span>
            </div>
            <p className="text-xs text-gray-600">
              {duplicatePages.count === 0
                ? "No duplicated or repeated pages found."
                : `Repeated content on page(s): ${duplicatePages.pageNumbers.join(", ")}`}
            </p>
          </div>

          {/* C. PDF Readability / Corruption */}
          <div className="rounded-xl border border-gray-200 bg-gray-50/70 p-3.5 space-y-1.5">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-gray-700 flex items-center gap-1.5">
                <FileCheck size={14} className="text-brand-600" />
                PDF Readable or Corrupted
              </span>
              <span
                className={`text-xs font-bold px-2 py-0.5 rounded-full ${
                  readability.status === "Fully Readable" || readability.status === "Good"
                    ? "bg-emerald-100 text-emerald-800"
                    : "bg-red-100 text-red-800"
                }`}
              >
                {readability.status || "Good"}
              </span>
            </div>
            <p className="text-xs text-gray-600">
              {readability.ocrUsed
                ? "Scanned pages detected — RapidOCR neural engine applied."
                : "Digital text extracted cleanly from document structure; file is not corrupted."}
            </p>
          </div>

          {/* D. Content Matches Selected Subject */}
          <div className="rounded-xl border border-gray-200 bg-gray-50/70 p-3.5 space-y-1.5">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-gray-700 flex items-center gap-1.5">
                <BookOpen size={14} className="text-brand-600" />
                Content Matches Subject
              </span>
              <span
                className={`text-xs font-bold px-2 py-0.5 rounded-full ${
                  subjectRelevance.status === "Highly Relevant" || subjectRelevance.status === "Relevant"
                    ? "bg-emerald-100 text-emerald-800"
                    : "bg-amber-100 text-amber-800"
                }`}
              >
                {subjectRelevance.status || "Relevant"} ({Math.round((subjectRelevance.score || 0.7) * 100)}%)
              </span>
            </div>
            <p className="text-xs text-gray-600">
              {subjectRelevance.explanation || "Content correlates with academic subject taxonomy."}
            </p>
          </div>
        </div>

        {/* E. Incomplete or Not */}
        <div className="rounded-xl border border-gray-200 bg-gray-50/50 p-3.5 space-y-2">
          <span className="text-xs font-bold uppercase tracking-wider text-gray-700 flex items-center gap-1.5">
            <Info size={14} className="text-brand-600" />
            Completeness Check (Incomplete or Complete)
          </span>
          <div className="text-xs text-gray-600 space-y-1">
            <p>
              • <strong>Content volume:</strong> {completeness.totalWords || 0} words across {completeness.totalPages || 1} pages ({completeness.readablePages || 1} readable).
            </p>
            {completeness.warnings?.map((w, idx) => (
              <p key={idx} className="text-amber-800">
                • {w}
              </p>
            ))}
          </div>
        </div>

        {/* Recommendation */}
        <div className="flex items-center justify-between border-t border-gray-100 pt-3 text-xs text-gray-500">
          <span>
            Admin Action Recommended:{" "}
            <strong className="text-brand-900">{report.adminActionRecommended || "Review Flags"}</strong>
          </span>
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
