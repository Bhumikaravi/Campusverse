import { useState, useEffect, useRef } from "react";
import { renderAsync } from "docx-preview";
import {
  X,
  Download,
  ExternalLink,
  ZoomIn,
  ZoomOut,
  Maximize2,
  Minimize2,
  FileText,
  ChevronLeft,
  ChevronRight,
  AlertCircle,
  RotateCcw,
  User,
  Calendar,
  Layers,
  Sparkles,
  Copy,
  Check,
  RefreshCw,
  Monitor,
  Globe,
} from "lucide-react";
import api from "../services/api";
import { materialsApi } from "../services/endpoints";
import Loader from "./Loader";
import { useToast } from "../context/ToastContext";

export default function MaterialPreviewModal({ materialId, open, onClose }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Viewer controls
  const [zoom, setZoom] = useState(100);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [activeSlide, setActiveSlide] = useState(0);
  const [activeTab, setActiveTab] = useState("preview"); // "preview" | "summary"
  const [downloading, setDownloading] = useState(false);
  const [copied, setCopied] = useState(false);
  const [presentationEngine, setPresentationEngine] = useState("deck"); // "deck" | "office" | "google"

  // DOCX High-Fidelity in-browser rendering
  const docxContainerRef = useRef(null);
  const [docxRendering, setDocxRendering] = useState(false);
  const [docxError, setDocxError] = useState(null);

  // On-demand summary generation
  const [generatingSummary, setGeneratingSummary] = useState(false);
  const [summaryData, setSummaryData] = useState(null);

  const { showToast } = useToast();

  useEffect(() => {
    if (!open || !materialId) return;

    setLoading(true);
    setError(null);
    setZoom(100);
    setActiveSlide(0);
    setActiveTab("preview");
    setPresentationEngine("deck");
    setDocxRendering(false);
    setDocxError(null);
    setCopied(false);
    setGeneratingSummary(false);
    setSummaryData(null);

    materialsApi
      .preview(materialId)
      .then((res) => {
        setData(res.data);
        if (res.data?.material?.summary) {
          setSummaryData({
            summary: res.data.material.summary,
            wordCount: res.data.material.summaryWordCount || res.data.material.summary.split(/\s+/).filter(Boolean).length,
          });
        }
      })
      .catch((err) => {
        const msg = err.response?.data?.detail || err.message || "Could not load material preview.";
        setError(msg);
      })
      .finally(() => setLoading(false));
  }, [open, materialId]);

  // Handle escape key & slide navigation keys
  useEffect(() => {
    if (!open) return;
    const handleKeyDown = (e) => {
      if (e.key === "Escape") {
        onClose();
      } else if (e.key === "ArrowLeft") {
        setActiveSlide((s) => Math.max(0, s - 1));
      } else if (e.key === "ArrowRight") {
        const total = data?.preview?.slides?.length || 1;
        setActiveSlide((s) => Math.min(total - 1, s + 1));
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [open, onClose, data]);

  const material = data?.material;
  const preview = data?.preview;

  // Resolve pure file URL with auth token for browser iframe loading
  const rawFileUrl = preview?.fileUrl || material?.fileUrl || "";
  let fileUrl = rawFileUrl.startsWith("http")
    ? rawFileUrl
    : `${api.defaults.baseURL}${rawFileUrl.replace(/^\/api/, "") || `/materials/${materialId}/file`}`;

  const token = localStorage.getItem("cv-token");
  if (token && fileUrl.includes("/materials/") && !fileUrl.includes("token=")) {
    const separator = fileUrl.includes("?") ? "&" : "?";
    fileUrl = `${fileUrl}${separator}token=${encodeURIComponent(token)}`;
  }

  // Extension & Kind
  const ext = String(preview?.extension || material?.fileType || material?.extension || "pdf")
    .toLowerCase()
    .replace(".", "");

  const isPresentation = ["pptx", "ppt", "odp"].includes(ext) || preview?.kind === "slides";
  const isDoc = ["docx", "doc", "rtf", "odt"].includes(ext) || preview?.kind === "docx";
  const isPdf = ext === "pdf" || preview?.kind === "pdf";
  const isImage = ["png", "jpg", "jpeg", "webp", "gif", "svg"].includes(ext) || preview?.kind === "image";
  const isText = ["txt", "md", "json", "js", "ts", "py", "java", "c", "cpp", "sql", "csv", "log"].includes(ext) || preview?.kind === "text";

  // Load and render authentic DOCX document with docx-preview
  useEffect(() => {
    if (!open || !isDoc || activeTab !== "preview" || !fileUrl) return;

    let isCancelled = false;
    setDocxRendering(true);
    setDocxError(null);

    const loadDocx = async () => {
      try {
        const fetchUrl = fileUrl.startsWith("http")
          ? fileUrl
          : `${api.defaults.baseURL}${fileUrl.startsWith("/") ? "" : "/"}${fileUrl}`;
        const response = await fetch(fetchUrl);
        if (!response.ok) {
          throw new Error(`Failed to load document: HTTP ${response.status}`);
        }
        const blob = await response.blob();
        if (isCancelled) return;

        if (docxContainerRef.current) {
          docxContainerRef.current.innerHTML = "";
          await renderAsync(blob, docxContainerRef.current, null, {
            className: "docx-preview-wrapper",
            inWrapper: true,
            ignoreWidth: false,
            ignoreHeight: false,
            breakPages: true,
            renderHeaders: true,
            renderFooters: true,
          });
        }
      } catch (err) {
        if (!isCancelled) {
          console.warn("docx-preview notice:", err);
          setDocxError(err.message || "Could not render document in browser.");
        }
      } finally {
        if (!isCancelled) setDocxRendering(false);
      }
    };

    loadDocx();

    return () => {
      isCancelled = true;
    };
  }, [open, isDoc, activeTab, fileUrl]);

  if (!open) return null;

  const handleDownload = () => {
    if (downloading) return;
    setDownloading(true);
    try {
      showToast("Starting download...", "info");
      const downloadEndpoint = `${api.defaults.baseURL}/materials/${materialId}/download`;
      const downloadName =
        material?.original_name ||
        material?.originalName ||
        material?.fileName ||
        `${material?.title || "study_material"}.${ext || "pdf"}`;

      const link = document.createElement("a");
      link.href = downloadEndpoint;
      link.setAttribute("download", downloadName);
      link.setAttribute("target", "_blank");
      link.setAttribute("rel", "noopener noreferrer");
      document.body.appendChild(link);
      link.click();
      setTimeout(() => {
        try {
          document.body.removeChild(link);
        } catch {}
        setDownloading(false);
        showToast(`Downloaded ${downloadName}`, "success");
      }, 1000);
    } catch {
      window.location.href = `${api.defaults.baseURL}/materials/${materialId}/download`;
      setDownloading(false);
    }
  };

  const handleCopyText = () => {
    if (preview?.content) {
      navigator.clipboard.writeText(preview.content);
      setCopied(true);
      showToast("Copied original text to clipboard", "success");
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleGenerateSummary = async () => {
    if (generatingSummary) return;
    setGeneratingSummary(true);
    try {
      showToast("Generating AI summary from original document...", "info");
      const res = await materialsApi.summarize(materialId);
      setSummaryData({
        summary: res.data.summary,
        wordCount: res.data.wordCount,
      });
      showToast("AI summary generated successfully!", "success");
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || "Failed to generate summary.";
      showToast(msg, "error");
    } finally {
      setGeneratingSummary(false);
    }
  };

  const handleZoomIn = () => setZoom((z) => Math.min(z + 20, 200));
  const handleZoomOut = () => setZoom((z) => Math.max(z - 20, 60));
  const handleResetZoom = () => setZoom(100);
  const toggleFullscreen = () => setIsFullscreen(!isFullscreen);

  const slides = preview?.slides || [];
  const currentSlide = slides[activeSlide] || slides[0] || null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-2 sm:p-4 md:p-6 animate-in fade-in duration-150">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/75 backdrop-blur-sm transition-opacity"
        onClick={onClose}
      />

      {/* Modal Container */}
      <div
        className={`relative flex flex-col bg-white rounded-2xl shadow-2xl border border-gray-200 overflow-hidden transition-all duration-200 ${
          isFullscreen
            ? "w-full h-full max-w-none max-h-none rounded-none"
            : "w-full max-w-6xl h-[92vh] max-h-[950px]"
        }`}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-gray-200 px-4 sm:px-6 py-3 bg-gray-50/95">
          <div className="min-w-0 pr-3">
            <div className="flex items-center gap-2">
              <span className="rounded bg-brand-100 border border-brand-200 px-2 py-0.5 text-[11px] font-bold text-brand-900 uppercase">
                {ext.toUpperCase()}
              </span>
              <h2 className="truncate text-base font-bold text-gray-900">
                {material?.title || "Document Preview"}
              </h2>
            </div>
            <p className="mt-0.5 truncate text-xs text-gray-500">
              {material?.subject || material?.department} • Semester {material?.semester || 1} • By{" "}
              <span className="font-medium text-gray-700">{material?.uploaderName || "Student"}</span>
            </p>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            {/* View Mode Tabs: Document Preview vs AI Summary */}
            <div className="flex items-center bg-gray-200/80 p-0.5 rounded-lg text-xs font-semibold">
              <button
                onClick={() => setActiveTab("preview")}
                className={`px-3 py-1 rounded-md transition ${
                  activeTab === "preview"
                    ? "bg-white text-brand-900 shadow-xs font-bold"
                    : "text-gray-600 hover:text-gray-900"
                }`}
              >
                {isPresentation ? "Slides Preview" : "Document Preview"}
              </button>
              <button
                onClick={() => setActiveTab("summary")}
                className={`px-3 py-1 rounded-md transition flex items-center gap-1.5 ${
                  activeTab === "summary"
                    ? "bg-white text-brand-900 shadow-xs font-bold"
                    : "text-gray-600 hover:text-gray-900"
                }`}
              >
                <Sparkles size={13} className="text-brand-600" />
                <span>AI Summary</span>
              </button>
            </div>

            <button
              onClick={handleDownload}
              disabled={downloading}
              className="btn-primary !py-1.5 !px-3 text-xs flex items-center gap-1.5 shadow-sm !bg-[#3e362e] hover:!bg-[#2a241e]"
              title="Download original file"
            >
              <Download size={14} />
              <span className="hidden sm:inline">{downloading ? "Downloading..." : "Download"}</span>
            </button>

            <button
              onClick={toggleFullscreen}
              className="rounded-lg p-2 text-gray-500 hover:bg-gray-200 transition"
              title={isFullscreen ? "Exit Fullscreen" : "Fullscreen Mode"}
              aria-label="Toggle Fullscreen"
            >
              {isFullscreen ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
            </button>

            <button
              onClick={onClose}
              className="rounded-lg p-2 text-gray-500 hover:bg-gray-200 transition"
              title="Close Preview"
              aria-label="Close"
            >
              <X size={18} />
            </button>
          </div>
        </div>

        {/* Sub-toolbar when viewing original document */}
        {activeTab === "preview" && !loading && !error && (
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-gray-200 bg-white px-4 py-2 text-xs">
            <div className="flex items-center gap-2">
              <span className="text-gray-500 font-medium">Original Document Viewer:</span>
              <span className="font-semibold text-gray-800">
                {preview?.fileName || material?.originalName || `Document.${ext}`}
              </span>

              {/* Format-specific status badge */}
              {isPresentation && (
                <div className="flex items-center gap-2">
                  <span className="rounded bg-brand-50 border border-brand-200 px-2 py-0.5 text-[10px] font-bold text-brand-800">
                    {slides.length} {slides.length === 1 ? "Slide" : "Slides"}
                  </span>
                  <div className="flex items-center bg-gray-100 p-0.5 rounded-lg ml-1">
                    <button
                      onClick={() => setPresentationEngine("deck")}
                      className={`px-2 py-0.5 rounded text-[10px] font-bold flex items-center gap-1 transition ${
                        presentationEngine === "deck"
                          ? "bg-white text-brand-900 shadow-2xs"
                          : "text-gray-600 hover:text-gray-900"
                      }`}
                      title="Interactive Slide Deck"
                    >
                      <Layers size={11} /> Slide Deck
                    </button>
                    <button
                      onClick={() => setPresentationEngine("office")}
                      className={`px-2 py-0.5 rounded text-[10px] font-bold flex items-center gap-1 transition ${
                        presentationEngine === "office"
                          ? "bg-white text-brand-900 shadow-2xs"
                          : "text-gray-600 hover:text-gray-900"
                      }`}
                      title="Microsoft Office Online Viewer"
                    >
                      <Monitor size={11} /> Office Viewer
                    </button>
                    <button
                      onClick={() => setPresentationEngine("google")}
                      className={`px-2 py-0.5 rounded text-[10px] font-bold flex items-center gap-1 transition ${
                        presentationEngine === "google"
                          ? "bg-white text-brand-900 shadow-2xs"
                          : "text-gray-600 hover:text-gray-900"
                      }`}
                      title="Google Docs Viewer"
                    >
                      <Globe size={11} /> Google Docs
                    </button>
                  </div>
                </div>
              )}
              {isText && preview?.lineCount && (
                <span className="rounded bg-gray-100 border border-gray-200 px-2 py-0.5 text-[10px] font-medium text-gray-700">
                  {preview.lineCount} lines • {preview.wordCount || 0} words
                </span>
              )}
            </div>

            {/* Zoom Controls */}
            <div className="flex items-center gap-1">
              <button
                onClick={handleZoomOut}
                className="rounded p-1 text-gray-600 hover:bg-gray-100 transition"
                title="Zoom Out"
              >
                <ZoomOut size={14} />
              </button>
              <span className="text-[11px] font-semibold w-10 text-center text-gray-700">
                {zoom}%
              </span>
              <button
                onClick={handleZoomIn}
                className="rounded p-1 text-gray-600 hover:bg-gray-100 transition"
                title="Zoom In"
              >
                <ZoomIn size={14} />
              </button>
              <button
                onClick={handleResetZoom}
                className="rounded p-1 text-gray-600 hover:bg-gray-100 transition"
                title="Reset Zoom"
              >
                <RotateCcw size={13} />
              </button>

              {isText && (
                <button
                  onClick={handleCopyText}
                  className="ml-2 flex items-center gap-1 rounded bg-gray-100 px-2.5 py-1 text-[11px] font-medium text-gray-700 hover:bg-gray-200 transition"
                  title="Copy full text"
                >
                  {copied ? <Check size={12} className="text-emerald-600" /> : <Copy size={12} />}
                  <span>{copied ? "Copied" : "Copy Text"}</span>
                </button>
              )}

              <a
                href={fileUrl}
                target="_blank"
                rel="noreferrer"
                className="ml-2 flex items-center gap-1 rounded bg-gray-100 px-2.5 py-1 text-[11px] font-semibold text-gray-700 hover:bg-gray-200 transition"
                title="Open original file in new window"
              >
                <ExternalLink size={12} /> Open in New Tab
              </a>
            </div>
          </div>
        )}

        {/* Main Body */}
        <div className="relative flex-1 bg-gray-100 overflow-hidden flex flex-col">
          {loading && (
            <div className="flex-1 w-full flex items-center justify-center py-24">
              <Loader label="Loading original uploaded document..." />
            </div>
          )}

          {error && !loading && (
            <div className="flex-1 w-full flex items-center justify-center p-6">
              <div className="max-w-md p-6 text-center bg-white rounded-xl shadow border border-red-200 mx-4">
                <AlertCircle size={40} className="mx-auto text-red-500 mb-3" />
                <h3 className="font-bold text-gray-900">Preview Notice</h3>
                <p className="mt-1 text-xs text-gray-500">{error}</p>
                <div className="mt-4 flex justify-center gap-3">
                  <button onClick={onClose} className="btn-secondary !py-1.5 text-xs">
                    Close
                  </button>
                  <button onClick={handleDownload} className="btn-primary !py-1.5 text-xs">
                    <Download size={14} /> Download Original File
                  </button>
                </div>
              </div>
            </div>
          )}

          {!loading && !error && (
            <>
              {/* TAB 1: SEPARATE AI SUMMARY SECTION (Only when student requests it) */}
              {activeTab === "summary" && (
                <div className="w-full h-full overflow-y-auto p-4 sm:p-8 bg-gray-50">
                  <div className="max-w-3xl mx-auto bg-white rounded-2xl shadow-md p-6 sm:p-10 border border-gray-200 space-y-6">
                    <div className="flex items-center justify-between border-b border-gray-100 pb-4">
                      <div>
                        <span className="text-xs font-bold text-brand-700 uppercase tracking-wide flex items-center gap-1.5">
                          <Sparkles size={14} className="text-brand-600" />
                          AI Summarization Feature
                        </span>
                        <h1 className="text-xl sm:text-2xl font-bold text-gray-900 mt-1">
                          {material?.title}
                        </h1>
                      </div>
                      <span className="rounded-full bg-brand-50 border border-brand-200 px-3 py-1 text-xs font-bold text-brand-900">
                        {ext.toUpperCase()}
                      </span>
                    </div>

                    {summaryData?.summary ? (
                      <div className="space-y-4">
                        <div className="flex items-center justify-between text-xs text-gray-500">
                          <span>AI Summary • Grounded in original study material</span>
                          <span className="font-bold text-emerald-800 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                            {summaryData.wordCount || 0} words
                          </span>
                        </div>
                        <div className="bg-brand-50/40 p-5 rounded-xl border border-brand-100 text-sm text-gray-800 leading-relaxed whitespace-pre-line font-normal">
                          {summaryData.summary}
                        </div>
                        <div className="flex justify-end pt-2">
                          <button
                            onClick={handleGenerateSummary}
                            disabled={generatingSummary}
                            className="btn-secondary !py-1.5 !px-3 text-xs flex items-center gap-1.5"
                          >
                            <RefreshCw size={13} className={generatingSummary ? "animate-spin" : ""} />
                            <span>{generatingSummary ? "Regenerating..." : "Regenerate Summary"}</span>
                          </button>
                        </div>
                      </div>
                    ) : (
                      <div className="p-8 text-center bg-gray-50 rounded-xl border border-dashed border-gray-300">
                        <Sparkles size={36} className="mx-auto text-brand-500 mb-3" />
                        <h3 className="text-base font-bold text-gray-900">No Summary Generated Yet</h3>
                        <p className="mt-1 text-xs text-gray-500 max-w-md mx-auto">
                          In CampusVerse, notes preview shows your original document unchanged. AI summaries are only generated when you explicitly request them.
                        </p>
                        <button
                          onClick={handleGenerateSummary}
                          disabled={generatingSummary}
                          className="btn-primary mt-5 !py-2 !px-4 text-xs inline-flex items-center gap-2 shadow-sm"
                        >
                          {generatingSummary ? (
                            <>
                              <RefreshCw size={14} className="animate-spin" />
                              <span>Generating AI Summary...</span>
                            </>
                          ) : (
                            <>
                              <Sparkles size={14} />
                              <span>Generate AI Summary Now</span>
                            </>
                          )}
                        </button>
                      </div>
                    )}

                    <div className="flex items-center justify-between pt-4 border-t border-gray-100 text-xs text-gray-500">
                      <span>{material?.department} • Semester {material?.semester}</span>
                      <button
                        onClick={() => setActiveTab("preview")}
                        className="btn-secondary !py-1.5 !px-3 text-xs"
                      >
                        Return to Original Preview
                      </button>
                    </div>
                  </div>
                </div>
              )}

              {/* TAB 2: ORIGINAL DOCUMENT PREVIEW (Unchanged, Unsummarized) */}
              {activeTab === "preview" && (
                <div className="flex-1 w-full h-full relative overflow-hidden flex flex-col">
                  {/* 1. PDF DOCUMENT VIEWER */}
                  {isPdf && (
                    <div className="flex-1 w-full h-full overflow-hidden flex flex-col bg-gray-200">
                      <iframe
                        src={`${fileUrl}#toolbar=1&navpanes=1`}
                        title={material?.title || "PDF Document"}
                        className="w-full h-full border-0 bg-white"
                        style={{
                          transform: `scale(${zoom > 100 ? zoom / 100 : 1})`,
                          transformOrigin: "top center",
                        }}
                      />
                    </div>
                  )}

                  {/* 2. DOCX DOCUMENT VIEWER (Authentic In-Browser docx-preview) */}
                  {isDoc && (
                    <div className="flex-1 w-full h-full overflow-y-auto p-4 sm:p-8 bg-gray-200/90 flex flex-col items-center">
                      {docxRendering && (
                        <div className="my-auto flex flex-col items-center justify-center p-12">
                          <Loader label="Rendering original Word document formatting..." />
                          <p className="mt-2 text-xs text-gray-500">Preserving original layout, fonts, tables, and images...</p>
                        </div>
                      )}
                      {docxError && !docxRendering && (
                        <div className="max-w-md mx-auto my-auto p-6 bg-white rounded-xl shadow border border-amber-200 text-center">
                          <AlertCircle size={36} className="mx-auto text-amber-500 mb-2" />
                          <h4 className="font-bold text-gray-950">Word Document Preview</h4>
                          <p className="mt-1 text-xs text-gray-600 leading-relaxed">
                            {docxError}
                          </p>
                          <div className="mt-4 flex flex-col sm:flex-row justify-center gap-2">
                            <a
                              href={`https://view.officeapps.live.com/op/embed.aspx?src=${encodeURIComponent(fileUrl)}`}
                              target="_blank"
                              rel="noreferrer"
                              className="btn-secondary !py-1.5 !px-3 text-xs inline-flex items-center gap-1.5"
                            >
                              <ExternalLink size={13} /> Open with Office Online
                            </a>
                            <button onClick={handleDownload} className="btn-primary !py-1.5 !px-3 text-xs inline-flex items-center gap-1.5">
                              <Download size={13} /> Download Original .DOCX
                            </button>
                          </div>
                        </div>
                      )}
                      <div
                        ref={docxContainerRef}
                        style={{
                          transform: `scale(${zoom / 100})`,
                          transformOrigin: "top center",
                          transition: "transform 0.15s ease-out",
                        }}
                        className={`w-full max-w-4xl mx-auto shadow-xl rounded-xl overflow-hidden bg-white p-4 sm:p-8 ${
                          docxRendering || docxError ? "hidden" : "block"
                        }`}
                      />
                    </div>
                  )}

                  {/* 3. PPTX PRESENTATION VIEWER */}
                  {isPresentation && (
                    <div className="flex-1 w-full h-full flex flex-col bg-gray-900 text-white overflow-hidden">
                      {/* Office Online Embed Engine */}
                      {presentationEngine === "office" && (
                        <iframe
                          key={`office-${fileUrl}`}
                          src={`https://view.officeapps.live.com/op/embed.aspx?src=${encodeURIComponent(fileUrl)}`}
                          title={material?.title || "Presentation Preview"}
                          className="w-full h-full border-0 bg-white"
                          allowFullScreen
                        />
                      )}

                      {/* Google Docs Viewer Engine */}
                      {presentationEngine === "google" && (
                        <iframe
                          key={`google-${fileUrl}`}
                          src={`https://docs.google.com/viewer?url=${encodeURIComponent(fileUrl)}&embedded=true`}
                          title={material?.title || "Presentation Preview"}
                          className="w-full h-full border-0 bg-white"
                          allowFullScreen
                        />
                      )}

                      {/* Interactive Slide Deck Engine */}
                      {presentationEngine === "deck" && (
                        <div className="flex-1 w-full h-full flex flex-col md:flex-row overflow-hidden">
                          {/* Left Thumbnail Filmstrip */}
                          <div className="w-full md:w-56 bg-gray-950 border-r border-gray-800 flex md:flex-col overflow-auto p-2 gap-2 shrink-0">
                            <div className="hidden md:flex items-center justify-between px-2 py-1 text-xs text-gray-400 font-bold border-b border-gray-800 pb-2">
                              <span className="flex items-center gap-1.5">
                                <Layers size={13} className="text-brand-400" /> Slides ({slides.length})
                              </span>
                            </div>
                            {slides.map((s, idx) => (
                              <div
                                key={idx}
                                onClick={() => setActiveSlide(idx)}
                                className={`p-2 rounded-xl cursor-pointer transition border text-left flex items-start gap-2 ${
                                  activeSlide === idx
                                    ? "bg-brand-900/50 border-brand-500 text-white shadow-sm"
                                    : "bg-gray-900/60 border-gray-800 text-gray-400 hover:bg-gray-800 hover:text-gray-200"
                                }`}
                              >
                                <span className="text-[10px] font-mono font-bold bg-gray-800 px-1.5 py-0.5 rounded text-gray-300 shrink-0">
                                  {s.index || idx + 1}
                                </span>
                                <div className="min-w-0">
                                  <p className="truncate text-xs font-semibold leading-tight">
                                    {s.title || `Slide ${idx + 1}`}
                                  </p>
                                </div>
                              </div>
                            ))}
                          </div>

                          {/* Main Presentation Stage */}
                          <div className="flex-1 flex flex-col bg-gray-850 overflow-hidden">
                            {/* Slide Top Navigation Bar */}
                            <div className="flex items-center justify-between bg-gray-900/90 px-4 py-2 border-b border-gray-800 text-xs">
                              <span className="font-bold text-gray-200 flex items-center gap-1.5">
                                <span>Slide {activeSlide + 1} of {slides.length}</span>
                                {currentSlide?.title && (
                                  <span className="text-gray-400 hidden sm:inline">— {currentSlide.title}</span>
                                )}
                              </span>

                              <div className="flex items-center gap-2">
                                <button
                                  onClick={() => setActiveSlide((s) => Math.max(0, s - 1))}
                                  disabled={activeSlide === 0}
                                  className="px-2.5 py-1 rounded bg-gray-800 hover:bg-gray-700 disabled:opacity-40 text-xs flex items-center gap-1 font-semibold transition"
                                >
                                  <ChevronLeft size={14} /> Prev
                                </button>
                                <button
                                  onClick={() => setActiveSlide((s) => Math.min(slides.length - 1, s + 1))}
                                  disabled={activeSlide >= slides.length - 1}
                                  className="px-2.5 py-1 rounded bg-gray-800 hover:bg-gray-700 disabled:opacity-40 text-xs flex items-center gap-1 font-semibold transition"
                                >
                                  Next <ChevronRight size={14} />
                                </button>
                              </div>
                            </div>

                            {/* Slide Viewport */}
                            <div className="flex-1 overflow-auto flex items-center justify-center p-3 sm:p-6 bg-gray-950">
                              {currentSlide ? (
                                <div
                                  style={{
                                    transform: `scale(${zoom / 100})`,
                                    transformOrigin: "center center",
                                    transition: "transform 0.15s ease-out",
                                  }}
                                  className="w-full max-w-4xl min-h-[300px] sm:min-h-[420px] max-h-[85vh] rounded-xl shadow-2xl relative overflow-auto border border-gray-700 bg-white p-5 sm:p-10 text-gray-900 select-text flex flex-col justify-between"
                                >
                                  <div>
                                    <div className="flex items-center justify-between border-b border-gray-200 pb-2 mb-4">
                                      <span className="text-xs font-bold text-brand-600 uppercase tracking-wide">
                                        SLIDE {activeSlide + 1} OF {slides.length}
                                      </span>
                                      <span className="text-xs text-gray-500 font-medium">{material?.title}</span>
                                    </div>
                                    <h3 className="text-xl sm:text-2xl font-bold text-gray-900 mb-4">
                                      {currentSlide.title || `Slide ${activeSlide + 1}`}
                                    </h3>
                                    <div className="whitespace-pre-wrap font-sans text-sm sm:text-base leading-relaxed text-gray-800">
                                      {currentSlide.text || "Original slide content."}
                                    </div>
                                  </div>
                                  <div className="pt-4 mt-6 border-t border-gray-200 flex flex-wrap justify-between gap-2 text-xs text-gray-500">
                                    <span>{material?.subject || material?.department}</span>
                                    <span className="font-semibold text-brand-700">CampusVerse Original Presentation Deck</span>
                                  </div>
                                </div>
                              ) : (
                                <div className="text-gray-400 text-sm">No slides available.</div>
                              )}
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  {/* 4. TEXT / CODE DOCUMENT VIEWER */}
                  {isText && (
                    <div className="flex-1 w-full h-full overflow-auto bg-gray-900 text-gray-100 font-mono text-xs sm:text-sm">
                      <div
                        style={{
                          transform: `scale(${zoom / 100})`,
                          transformOrigin: "top left",
                          transition: "transform 0.15s ease-out",
                        }}
                        className="max-w-5xl mx-auto p-4 sm:p-8"
                      >
                        <div className="bg-gray-950 rounded-xl border border-gray-800 shadow-2xl overflow-hidden">
                          {/* File banner */}
                          <div className="px-4 py-2.5 bg-gray-900 border-b border-gray-800 flex items-center justify-between text-xs text-gray-400">
                            <span className="font-bold text-gray-200">{preview?.fileName || material?.originalName}</span>
                            <span>{preview?.lineCount || 0} lines</span>
                          </div>

                          {/* Line numbers + content */}
                          <div className="p-4 sm:p-6 overflow-x-auto flex">
                            {preview?.content ? (
                              <div className="w-full flex gap-4">
                                {/* Line Number Column */}
                                <div className="select-none text-right text-gray-600 font-mono text-xs pr-3 border-r border-gray-800 shrink-0">
                                  {preview.content.split("\n").map((_, idx) => (
                                    <div key={idx} className="leading-relaxed">
                                      {idx + 1}
                                    </div>
                                  ))}
                                </div>
                                {/* Content Column */}
                                <div className="flex-1 font-mono text-xs sm:text-sm leading-relaxed text-gray-200 whitespace-pre">
                                  {preview.content}
                                </div>
                              </div>
                            ) : (
                              <div className="p-6 text-gray-400 italic">No text content found in file.</div>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* 5. IMAGE VIEWER */}
                  {isImage && (
                    <div className="flex-1 w-full h-full overflow-auto flex items-center justify-center p-4 bg-gray-900/10">
                      <img
                        src={fileUrl}
                        alt={material?.title}
                        className="max-w-full max-h-full object-contain rounded-lg shadow-lg border border-gray-300 bg-white"
                        style={{
                          transform: `scale(${zoom / 100})`,
                          transition: "transform 0.15s ease-out",
                        }}
                      />
                    </div>
                  )}

                  {/* 6. UNSUPPORTED FORMAT FALLBACK */}
                  {!isPdf && !isDoc && !isPresentation && !isText && !isImage && (
                    <div className="flex-1 w-full flex items-center justify-center p-6">
                      <div className="max-w-md p-8 text-center bg-white rounded-2xl shadow-lg border border-gray-200 mx-4">
                        <div className="h-16 w-16 mx-auto rounded-2xl bg-brand-50 border border-brand-200 flex items-center justify-center text-brand-600 mb-4">
                          <FileText size={32} />
                        </div>
                        <h3 className="text-lg font-bold text-gray-900">{material?.title}</h3>
                        <p className="mt-1 text-xs text-gray-500">
                          {material?.fileType || ext.toUpperCase()} • {material?.fileSize} • {material?.subject}
                        </p>
                        <p className="mt-4 text-xs text-gray-600 leading-relaxed bg-gray-50 p-3 rounded-lg border border-gray-200">
                          This original file format ({ext.toUpperCase()}) can be opened directly with your desktop application. Click below to download in its original format.
                        </p>
                        <button
                          onClick={handleDownload}
                          disabled={downloading}
                          className="btn-primary w-full mt-6 py-2.5 !bg-[#3e362e] hover:!bg-[#2a241e]"
                        >
                          <Download size={16} /> Download Original .{ext.toUpperCase()}
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </>
          )}
        </div>

        {/* Footer info bar */}
        <div className="flex flex-wrap items-center justify-between border-t border-gray-200 px-5 py-2.5 bg-gray-50 text-xs text-gray-500">
          <div className="flex items-center gap-4">
            <span className="flex items-center gap-1">
              <User size={13} /> {material?.uploaderName || "Student"}
            </span>
            <span className="flex items-center gap-1">
              <Calendar size={13} />{" "}
              {material?.createdAt ? new Date(material.createdAt).toLocaleDateString() : "Recent"}
            </span>
            <span className="flex items-center gap-1">
              <Download size={13} /> {material?.downloads || 0} downloads
            </span>
          </div>

          <div className="flex items-center gap-3">
            <button onClick={onClose} className="btn-secondary !py-1 !px-3 text-xs">
              Close
            </button>
            <button
              onClick={handleDownload}
              disabled={downloading}
              className="btn-primary !py-1 !px-3 text-xs !bg-[#3e362e] hover:!bg-[#2a241e]"
            >
              <Download size={13} /> Download .{ext.toUpperCase()}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
