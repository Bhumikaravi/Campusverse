import { useState } from "react";
import { Link } from "react-router-dom";
import {
  Bookmark,
  Download,
  FileText,
  Eye,
  Sparkles,
  CheckCircle2,
  Clock,
  AlertCircle,
  RefreshCw,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { StarDisplay } from "./StarRating";
import MaterialPreviewModal from "./MaterialPreviewModal";
import api from "../services/api";
import { useToast } from "../context/ToastContext";

export default function MaterialCard({ material, onToggleBookmark }) {
  const [showPreview, setShowPreview] = useState(false);
  const [expandedSummary, setExpandedSummary] = useState(false);
  const { showToast } = useToast();

  const resolvedId = material?.id || material?._id || material?.documentId || "";

  const {
    id,
    documentId,
    title,
    academicCategory,
    mainCategory,
    fileType = "PDF",
    fileSize,
    pageCount = 1,
    totalPageCount,
    processedPageCount,
    pagesOcr = [],
    pagesFailed = [],
    extractionStatus = "Completed",
    summary,
    description,
    summaryWordCount,
    maxSummaryWords = 500,
    processingStatus = "Completed",
    rating = 5.0,
    ratingCount = 0,
    downloads = 0,
    bookmarked = false,
    thumbnail,
  } = material || {};

  const resolvedCategory = academicCategory || mainCategory || "Engineering";
  const resolvedSummary = summary || description || "";
  const calculatedWordCount = summaryWordCount || (resolvedSummary ? resolvedSummary.trim().split(/\s+/).filter(Boolean).length : 0);

  const totalPages = totalPageCount || pageCount || 1;
  const processedPages = processedPageCount || totalPages;
  const isSlideType = fileType.toUpperCase().includes("PPT");
  const unit = isSlideType ? (totalPages === 1 ? "slide" : "slides") : (totalPages === 1 ? "page" : "pages");
  const pageLabel = processedPages === totalPages ? `${totalPages} ${unit}` : `${processedPages}/${totalPages} ${unit}`;

  const handleDownload = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (!resolvedId) {
      showToast("Material ID not found.", "error");
      return;
    }
    try {
      const token = localStorage.getItem("cv-token");
      const downloadUrl = `${api.defaults.baseURL}/materials/${resolvedId}/download${token ? `?token=${encodeURIComponent(token)}` : ""}`;
      const link = document.createElement("a");
      link.href = downloadUrl;
      link.setAttribute("download", material.originalName || `${material.title || "study-material"}.${(material.fileType || "pdf").toLowerCase()}`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      showToast("Download started", "success");
    } catch {
      showToast("Download failed. Try again.", "error");
    }
  };

  const handleOpenPreview = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setShowPreview(true);
  };

  // Render processing status badge with required exact states
  const renderStatusBadge = () => {
    const st = processingStatus || extractionStatus;
    switch (st) {
      case "Completed":
      case "Summary ready":
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 text-emerald-800 px-2 py-0.5 text-[10px] font-extrabold shadow-2xs">
            <CheckCircle2 size={11} className="text-emerald-600" />
            <span>Completed</span>
          </span>
        );
      case "Partially processed":
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-amber-100 text-amber-800 px-2 py-0.5 text-[10px] font-bold shadow-2xs">
            <AlertCircle size={11} className="text-amber-600" />
            <span>Partially processed</span>
          </span>
        );
      case "Generating summary":
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-amber-100 text-amber-800 px-2 py-0.5 text-[10px] font-bold shadow-2xs">
            <RefreshCw size={11} className="animate-spin text-amber-600" />
            <span>Generating summary</span>
          </span>
        );
      case "Extracting text":
      case "Processing document":
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-blue-100 text-blue-800 px-2 py-0.5 text-[10px] font-bold shadow-2xs">
            <RefreshCw size={11} className="animate-spin text-blue-600" />
            <span>Extracting text</span>
          </span>
        );
      case "Running OCR":
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-purple-100 text-purple-800 px-2 py-0.5 text-[10px] font-bold shadow-2xs">
            <RefreshCw size={11} className="animate-spin text-purple-600" />
            <span>Running OCR</span>
          </span>
        );
      case "Uploading":
      case "Uploaded":
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-gray-100 text-gray-700 px-2 py-0.5 text-[10px] font-bold shadow-2xs">
            <Clock size={11} className="text-gray-500" />
            <span>Uploaded</span>
          </span>
        );
      case "Failed":
      case "Processing failed":
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-red-100 text-red-800 px-2 py-0.5 text-[10px] font-bold shadow-2xs">
            <AlertCircle size={11} className="text-red-600" />
            <span>Failed</span>
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 text-emerald-800 px-2 py-0.5 text-[10px] font-extrabold shadow-2xs">
            <CheckCircle2 size={11} className="text-emerald-600" />
            <span>Completed</span>
          </span>
        );
    }
  };

  return (
    <>
      <div className="card group flex flex-col overflow-hidden bg-white border border-brand-200/80 transition hover:-translate-y-0.5 hover:shadow-md hover:border-brand-300">
        {/* Card Header & Preview Banner */}
        <div
          onClick={handleOpenPreview}
          className="relative block h-32 overflow-hidden bg-brand-50/50 border-b border-brand-100 cursor-pointer"
          title="Click to preview"
        >
          {thumbnail ? (
            <img src={thumbnail} alt="" className="h-full w-full object-cover transition group-hover:scale-105" />
          ) : (
            <div className="flex h-full w-full items-center justify-center">
              <FileText size={36} className="text-brand-400 group-hover:text-brand-600 transition" />
            </div>
          )}

          {/* File Type & Page Count Badge */}
          <div className="absolute left-2.5 top-2.5 flex items-center gap-1.5">
            <span className="rounded-full bg-white/95 border border-brand-200 px-2 py-0.5 text-[11px] font-semibold text-brand-900 shadow-sm">
              {fileType}
            </span>
            {pageLabel && (
              <span className="rounded-full bg-brand-900/80 backdrop-blur-xs px-2 py-0.5 text-[10px] font-medium text-white shadow-sm">
                {pageLabel}
              </span>
            )}
          </div>

          {/* Processing Status Badge */}
          <div className="absolute right-2.5 top-2.5">
            {renderStatusBadge()}
          </div>

          {/* Hover overlay preview hint */}
          <div className="absolute inset-0 bg-brand-900/20 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
            <span className="rounded-lg bg-white/95 px-2.5 py-1 text-xs font-bold text-brand-900 shadow-md flex items-center gap-1.5">
              <Eye size={13} /> Quick Preview
            </span>
          </div>
        </div>

        {/* Card Body */}
        <div className="flex flex-1 flex-col gap-2.5 p-4">
          {/* Document Title */}
          <Link
            to={resolvedId ? `/materials/${resolvedId}` : "#"}
            className="line-clamp-2 font-bold leading-snug text-gray-900 hover:text-brand-700 transition text-sm"
          >
            {title}
          </Link>

          {/* Academic Category & File Details */}
          <div className="flex items-center justify-between text-[11px] text-gray-500">
            <span className="font-semibold text-brand-900 truncate max-w-[170px]" title={resolvedCategory}>
              {resolvedCategory}
            </span>
            {fileSize && <span>{fileSize}</span>}
          </div>

          {/* AI-Generated Summary Container */}
          <div className="rounded-xl border border-brand-100 bg-brand-50/40 p-2.5 space-y-1.5">
            <div className="flex items-center justify-between">
              <span className="flex items-center gap-1 text-[11px] font-bold text-brand-900 uppercase tracking-wider">
                <Sparkles size={11} className="text-brand-600" />
                <span>AI Summary</span>
              </span>
              <span className="text-[10px] font-bold text-emerald-800 bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-200">
                {calculatedWordCount} / {maxSummaryWords} words
              </span>
            </div>

            {resolvedSummary ? (
              <div>
                <p
                  className={`text-[11px] text-gray-700 leading-relaxed font-normal ${
                    expandedSummary ? "" : "line-clamp-3"
                  }`}
                >
                  {resolvedSummary}
                </p>
                {resolvedSummary.length > 120 && (
                  <button
                    type="button"
                    onClick={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                      setExpandedSummary(!expandedSummary);
                    }}
                    className="mt-1 text-[10px] font-semibold text-brand-700 hover:text-brand-900 flex items-center gap-0.5"
                  >
                    {expandedSummary ? (
                      <>
                        Show less <ChevronUp size={11} />
                      </>
                    ) : (
                      <>
                        Read summary <ChevronDown size={11} />
                      </>
                    )}
                  </button>
                )}
              </div>
            ) : (
              <p className="text-[11px] text-gray-400 italic">No summary generated.</p>
            )}
          </div>

          {/* Rating */}
          <div className="flex items-center justify-between text-xs pt-0.5">
            <StarDisplay rating={rating} count={ratingCount} size={13} />
            <span className="text-[11px] text-gray-400">{downloads} downloads</span>
          </div>

          {/* Action Row */}
          <div className="mt-auto flex items-center gap-1.5 border-t border-gray-100 pt-2.5">
            <button
              onClick={handleOpenPreview}
              className="flex-1 btn-secondary !py-1 !px-2 text-xs flex items-center justify-center gap-1 text-brand-800 hover:bg-brand-50 hover:text-brand-900"
              title="Preview document in browser"
            >
              <Eye size={13} /> Preview
            </button>
            <button
              onClick={handleDownload}
              className="flex-1 btn-primary !py-1 !px-2 text-xs flex items-center justify-center gap-1 !bg-[#3e362e] hover:!bg-[#2a241e]"
              title="Download file"
            >
              <Download size={13} /> Download
            </button>
            <button
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                if (resolvedId) onToggleBookmark?.(resolvedId);
              }}
              className="rounded-lg p-1.5 hover:bg-brand-50 transition text-gray-400 hover:text-brand-600 shrink-0"
              aria-label="Bookmark"
            >
              <Bookmark
                size={16}
                className={bookmarked ? "fill-brand-600 text-brand-600" : ""}
              />
            </button>
          </div>
        </div>
      </div>

      {/* Modal Preview Instance */}
      <MaterialPreviewModal
        materialId={resolvedId}
        open={showPreview}
        onClose={() => setShowPreview(false)}
      />
    </>
  );
}
