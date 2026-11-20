import { useState, useEffect } from "react";
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
  const [viewerEngine, setViewerEngine] = useState("office"); // "office" | "google"
  const [slideViewMode, setSlideViewMode] = useState("cards"); // "cards" | "embed"
  const [activeSlide, setActiveSlide] = useState(0);
  const [activeTab, setActiveTab] = useState("preview"); // "preview" | "summary"
  const [iframeLoaded, setIframeLoaded] = useState(false);
  const [downloading, setDownloading] = useState(false);

  const { showToast } = useToast();

  useEffect(() => {
    if (!open || !materialId) return;

    setLoading(true);
    setError(null);
    setZoom(100);
    setViewerEngine("office");
    setSlideViewMode("cards");
    setActiveSlide(0);
    setActiveTab("preview");
    setIframeLoaded(false);

    materialsApi
      .preview(materialId)
      .then((res) => {
        setData(res.data);
      })
      .catch((err) => {
        const msg = err.response?.data?.detail || err.message || "Could not load material preview.";
        setError(msg);
      })
      .finally(() => setLoading(false));
  }, [open, materialId]);

  // Handle escape key
  useEffect(() => {
    if (!open) return;
    const handleKeyDown = (e) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [open, onClose]);

  if (!open) return null;

  const material = data?.material;
  const preview = data?.preview;

  // Resolve pure file URL without corrupting Supabase signed tokens
  const rawFileUrl = preview?.fileUrl || material?.fileUrl || "";
  const fileUrl = rawFileUrl.startsWith("http")
    ? rawFileUrl
    : `${api.defaults.baseURL}${rawFileUrl.replace(/^\/api/, "") || `/materials/${materialId}/download`}`;

  // Extension & Kind
  const ext = (preview?.extension || material?.fileType || "pdf").toLowerCase().replace(".", "");
  const isPresentation = ["pptx", "ppt", "odp"].includes(ext) || preview?.kind === "slides";
  const isDoc = ["docx", "doc", "rtf", "odt"].includes(ext) || preview?.kind === "document" || preview?.kind === "html";
  const isSpreadsheet = ["xlsx", "xls", "csv"].includes(ext) || preview?.kind === "spreadsheet";
  const isPdf = ext === "pdf" || preview?.kind === "pdf";
  const isImage = ["png", "jpg", "jpeg", "webp", "gif", "svg"].includes(ext) || preview?.kind === "image";
  const isText = ["txt", "md", "json", "js", "ts", "py", "java", "c", "cpp", "sql"].includes(ext) || preview?.kind === "text";
  const isOfficeDoc = isPresentation || isDoc || isSpreadsheet;

  // Viewer URLs
  const officeEmbedUrl = `https://view.officeapps.live.com/op/embed.aspx?src=${encodeURIComponent(fileUrl)}`;
  const googleEmbedUrl = `https://docs.google.com/viewer?url=${encodeURIComponent(fileUrl)}&embedded=true`;

  const activeViewerSrc = viewerEngine === "office" ? officeEmbedUrl : googleEmbedUrl;

  const handleDownload = async () => {
    if (downloading) return;
    setDownloading(true);
    try {
      showToast("Starting download...", "info");
      const res = await api.get(`/materials/${materialId}/download?json=true`);
      const downloadUrl = res.data?.url;
      const downloadName =
        res.data?.fileName ||
        material?.originalName ||
        `${material?.title || "study_material"}.${ext || "pdf"}`;

      if (downloadUrl) {
        const link = document.createElement("a");
        link.href = downloadUrl;
        link.setAttribute("download", downloadName);
        link.setAttribute("target", "_blank");
        link.setAttribute("rel", "noopener noreferrer");
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        showToast(`Downloaded ${downloadName}`, "success");
      } else {
        // Fallback: 302 redirect endpoint
        window.location.href = `${api.defaults.baseURL}/materials/${materialId}/download`;
      }
    } catch {
      window.location.href = `${api.defaults.baseURL}/materials/${materialId}/download`;
    } finally {
      setDownloading(false);
    }
  };

  const handleZoomIn = () => setZoom((z) => Math.min(z + 20, 200));
  const handleZoomOut = () => setZoom((z) => Math.max(z - 20, 60));
  const handleResetZoom = () => setZoom(100);

  const toggleFullscreen = () => {
    setIsFullscreen(!isFullscreen);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-2 sm:p-4 md:p-6">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/70 backdrop-blur-sm transition-opacity"
        onClick={onClose}
      />

      {/* Modal Container */}
      <div
        className={`relative flex flex-col bg-white rounded-2xl shadow-2xl border border-gray-200 overflow-hidden transition-all duration-200 ${
          isFullscreen
            ? "w-full h-full max-w-none max-h-none rounded-none"
            : "w-full max-w-5xl h-[92vh] max-h-[900px]"
        }`}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-gray-200 px-4 sm:px-6 py-3 bg-gray-50/90">
          <div className="min-w-0 pr-3">
            <div className="flex items-center gap-2">
              <span className="rounded bg-brand-100 border border-brand-200 px-2 py-0.5 text-[11px] font-bold text-brand-900 uppercase">
                {material?.fileType || ext.toUpperCase()}
              </span>
              <h2 className="truncate text-base font-bold text-gray-900">
                {material?.title || "Document Preview"}
              </h2>
            </div>
            <p className="mt-0.5 truncate text-xs text-gray-500">
              {material?.subject} • Semester {material?.semester} • {material?.department} • By{" "}
              <span className="font-medium text-gray-700">{material?.uploaderName || "Student"}</span>
            </p>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            {/* View Mode Tabs (Document vs AI Summary) */}
            <div className="hidden sm:flex items-center bg-gray-200/80 p-0.5 rounded-lg text-xs font-semibold">
              <button
                onClick={() => setActiveTab("preview")}
                className={`px-2.5 py-1 rounded-md transition ${
                  activeTab === "preview"
                    ? "bg-white text-brand-900 shadow-xs"
                    : "text-gray-600 hover:text-gray-900"
                }`}
              >
                {isPresentation ? "Slides" : "Document"}
              </button>
              <button
                onClick={() => setActiveTab("summary")}
                className={`px-2.5 py-1 rounded-md transition flex items-center gap-1 ${
                  activeTab === "summary"
                    ? "bg-white text-brand-900 shadow-xs"
                    : "text-gray-600 hover:text-gray-900"
                }`}
              >
                <Sparkles size={12} className="text-brand-600" />
                Notes
              </button>
            </div>

            <button
              onClick={handleDownload}
              disabled={downloading}
              className="btn-primary !py-1.5 !px-3 text-xs flex items-center gap-1.5 shadow-sm !bg-[#3e362e] hover:!bg-[#2a241e]"
              title="Download Document in Original Format"
            >
              <Download size={14} />
              <span className="hidden sm:inline">
                {downloading ? "Downloading..." : "Download"}
              </span>
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

        {/* Viewer Sub-toolbar (When in preview mode) */}
        {activeTab === "preview" && !loading && !error && (
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-gray-200 bg-white px-4 py-2 text-xs">
            {/* Viewer Switcher for Office Docs / Presentations */}
            {isPresentation ? (
              <div className="flex items-center gap-2">
                <span className="text-gray-500 font-medium hidden sm:inline">Presentation View:</span>
                <div className="flex items-center bg-gray-100 p-0.5 rounded-lg">
                  <button
                    onClick={() => setSlideViewMode("cards")}
                    className={`px-2.5 py-1 rounded-md text-[11px] font-bold flex items-center gap-1 transition ${
                      slideViewMode === "cards"
                        ? "bg-white text-brand-900 shadow-xs"
                        : "text-gray-600 hover:text-gray-900"
                    }`}
                    title="View Authentic Slide Deck"
                  >
                    <Layers size={12} />
                    Slide Deck
                  </button>
                  <button
                    onClick={() => {
                      setSlideViewMode("embed");
                      setIframeLoaded(false);
                    }}
                    className={`px-2.5 py-1 rounded-md text-[11px] font-bold flex items-center gap-1 transition ${
                      slideViewMode === "embed"
                        ? "bg-white text-brand-900 shadow-xs"
                        : "text-gray-600 hover:text-gray-900"
                    }`}
                    title="View with Office Online Embed"
                  >
                    <Monitor size={12} />
                    Office Viewer
                  </button>
                </div>
              </div>
            ) : isOfficeDoc ? (
              <div className="flex items-center gap-2">
                <span className="text-gray-500 font-medium hidden sm:inline">Viewer Engine:</span>
                <div className="flex items-center bg-gray-100 p-0.5 rounded-lg">
                  <button
                    onClick={() => {
                      setViewerEngine("office");
                      setIframeLoaded(false);
                    }}
                    className={`px-2.5 py-1 rounded-md text-[11px] font-bold flex items-center gap-1 transition ${
                      viewerEngine === "office"
                        ? "bg-white text-brand-900 shadow-xs"
                        : "text-gray-600 hover:text-gray-900"
                    }`}
                    title="View with Microsoft PowerPoint / Word Online"
                  >
                    <Monitor size={12} />
                    Microsoft Office
                  </button>
                  <button
                    onClick={() => {
                      setViewerEngine("google");
                      setIframeLoaded(false);
                    }}
                    className={`px-2.5 py-1 rounded-md text-[11px] font-bold flex items-center gap-1 transition ${
                      viewerEngine === "google"
                        ? "bg-white text-brand-900 shadow-xs"
                        : "text-gray-600 hover:text-gray-900"
                    }`}
                    title="View with Google Docs Viewer"
                  >
                    <Globe size={12} />
                    Google Docs
                  </button>
                </div>
              </div>
            ) : isPdf ? (
              <div className="flex items-center gap-2">
                <span className="text-gray-500 font-medium">PDF Document Viewer</span>
                <div className="flex items-center gap-1 ml-2">
                  <button
                    onClick={handleZoomOut}
                    className="rounded p-1 text-gray-600 hover:bg-gray-100"
                    title="Zoom Out"
                  >
                    <ZoomOut size={14} />
                  </button>
                  <span className="text-[11px] font-semibold w-9 text-center">{zoom}%</span>
                  <button
                    onClick={handleZoomIn}
                    className="rounded p-1 text-gray-600 hover:bg-gray-100"
                    title="Zoom In"
                  >
                    <ZoomIn size={14} />
                  </button>
                  <button
                    onClick={handleResetZoom}
                    className="rounded p-1 text-gray-600 hover:bg-gray-100"
                    title="Reset Zoom"
                  >
                    <RotateCcw size={13} />
                  </button>
                </div>
              </div>
            ) : isImage ? (
              <div className="flex items-center gap-2">
                <span className="text-gray-500 font-medium">Image Viewer</span>
                <div className="flex items-center gap-1 ml-2">
                  <button
                    onClick={handleZoomOut}
                    className="rounded p-1 text-gray-600 hover:bg-gray-100"
                    title="Zoom Out"
                  >
                    <ZoomOut size={14} />
                  </button>
                  <span className="text-[11px] font-semibold w-9 text-center">{zoom}%</span>
                  <button
                    onClick={handleZoomIn}
                    className="rounded p-1 text-gray-600 hover:bg-gray-100"
                    title="Zoom In"
                  >
                    <ZoomIn size={14} />
                  </button>
                  <button
                    onClick={handleResetZoom}
                    className="rounded p-1 text-gray-600 hover:bg-gray-100"
                    title="Reset Zoom"
                  >
                    <RotateCcw size={13} />
                  </button>
                </div>
              </div>
            ) : (
              <span className="text-gray-500 font-medium">Document View</span>
            )}

            <div className="flex items-center gap-2 ml-auto">
              <a
                href={fileUrl}
                target="_blank"
                rel="noreferrer"
                className="flex items-center gap-1 rounded bg-gray-100 px-2.5 py-1 text-[11px] font-semibold text-gray-700 hover:bg-gray-200 transition"
                title="Open original file in new browser window"
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
              <Loader label="Loading authentic material preview..." />
            </div>
          )}

          {error && !loading && (
            <div className="flex-1 w-full flex items-center justify-center p-6">
              <div className="max-w-md p-6 text-center bg-white rounded-xl shadow border border-red-200 mx-4">
                <AlertCircle size={40} className="mx-auto text-red-500 mb-3" />
                <h3 className="font-bold text-gray-900">Preview Error</h3>
                <p className="mt-1 text-xs text-gray-500">{error}</p>
                <div className="mt-4 flex justify-center gap-3">
                  <button onClick={onClose} className="btn-secondary !py-1.5 text-xs">
                    Close
                  </button>
                  <button onClick={handleDownload} className="btn-primary !py-1.5 text-xs">
                    <Download size={14} /> Download File Directly
                  </button>
                </div>
              </div>
            </div>
          )}

          {!loading && !error && (
            <>
              {/* TAB 1: AI Summary & Notes */}
              {activeTab === "summary" && (
                <div className="w-full h-full overflow-y-auto p-4 sm:p-8 bg-gray-50">
                  <div className="max-w-3xl mx-auto bg-white rounded-2xl shadow-md p-6 sm:p-10 border border-gray-200 space-y-6">
                    <div className="flex items-center justify-between border-b border-gray-100 pb-4">
                      <div>
                        <span className="text-xs font-bold text-brand-700 uppercase tracking-wide flex items-center gap-1.5">
                          <Sparkles size={14} className="text-brand-600" />
                          Academic Study Summary
                        </span>
                        <h1 className="text-xl sm:text-2xl font-bold text-gray-900 mt-1">
                          {material?.title}
                        </h1>
                      </div>
                      <span className="rounded-full bg-brand-50 border border-brand-200 px-3 py-1 text-xs font-bold text-brand-900">
                        {material?.fileType}
                      </span>
                    </div>

                    <div className="bg-brand-50/40 p-4 rounded-xl border border-brand-100 text-sm text-gray-800 leading-relaxed whitespace-pre-line">
                      {material?.summary || material?.description || preview?.summary || "No summary available."}
                    </div>

                    <div className="flex items-center justify-between pt-4 border-t border-gray-100 text-xs text-gray-500">
                      <span>{material?.department} • Semester {material?.semester}</span>
                      <button
                        onClick={() => setActiveTab("preview")}
                        className="btn-secondary !py-1.5 !px-3 text-xs"
                      >
                        Return to {isPresentation ? "Slides" : "Document"}
                      </button>
                    </div>
                  </div>
                </div>
              )}

              {/* TAB 2: LIVE PREVIEW */}
              {activeTab === "preview" && (
                <div className="flex-1 w-full h-full relative overflow-hidden flex flex-col">
                  {/* PRESENTATION SLIDES (PPTX, PPT) - AUTHENTIC SLIDE DECK */}
                  {isPresentation && slideViewMode === "cards" && (
                    <div className="flex-1 w-full h-full flex flex-col bg-gray-100 overflow-hidden">
                      {/* Slide Navigation Header */}
                      <div className="flex items-center justify-between bg-white border-b border-gray-200 px-4 py-2">
                        <span className="text-xs font-bold text-gray-700 flex items-center gap-1.5">
                          <Layers size={15} className="text-brand-600" />
                          Slide {activeSlide + 1} of {preview?.slides?.length || 1}
                        </span>
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => setActiveSlide((s) => Math.max(0, s - 1))}
                            disabled={activeSlide === 0}
                            className="btn-secondary !py-1 !px-2.5 text-xs flex items-center gap-1 disabled:opacity-40"
                          >
                            <ChevronLeft size={14} /> Prev
                          </button>
                          <button
                            onClick={() =>
                              setActiveSlide((s) => Math.min((preview?.slides?.length || 1) - 1, s + 1))
                            }
                            disabled={activeSlide >= (preview?.slides?.length || 1) - 1}
                            className="btn-secondary !py-1 !px-2.5 text-xs flex items-center gap-1 disabled:opacity-40"
                          >
                            Next <ChevronRight size={14} />
                          </button>
                        </div>
                      </div>

                      {/* Slide Card */}
                      <div className="flex-1 w-full overflow-auto flex items-center justify-center p-4 sm:p-6 bg-gray-200/80">
                        <div className="aspect-[16/9] w-full max-w-3xl bg-white rounded-2xl shadow-xl border border-gray-300 p-6 sm:p-8 flex flex-col justify-between overflow-y-auto">
                          <div>
                            <div className="flex items-center justify-between border-b border-gray-100 pb-2 mb-4">
                              <span className="text-xs font-bold text-brand-600 uppercase tracking-wide">
                                SLIDE {activeSlide + 1}
                              </span>
                              <span className="text-[11px] text-gray-400">
                                {material?.title}
                              </span>
                            </div>
                            {preview?.slides?.[activeSlide]?.heading && (
                              <h3 className="text-lg font-bold text-gray-900 mb-3">
                                {preview.slides[activeSlide].heading}
                              </h3>
                            )}
                            <div className="whitespace-pre-wrap font-sans text-sm sm:text-base leading-relaxed text-gray-800">
                              {preview?.slides?.[activeSlide]?.text || "No text available on this slide."}
                            </div>
                          </div>
                          <div className="pt-4 border-t border-gray-100 flex justify-between text-xs text-gray-400 mt-6">
                            <span>{material?.subject || material?.department}</span>
                            <span>CampusVerse Academic Slides</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* PRESENTATION EMBED OR OTHER OFFICE DOCS (DOCX, XLSX) */}
                  {((isPresentation && slideViewMode === "embed") || (!isPresentation && isOfficeDoc)) && (
                    <div className="flex-1 w-full h-full relative flex flex-col bg-gray-200">
                      {!iframeLoaded && (
                        <div className="absolute inset-0 flex flex-col items-center justify-center bg-gray-100/90 z-10">
                          <Loader label={`Loading ${isPresentation ? "PowerPoint Presentation" : "Document"}...`} />
                          <p className="mt-3 text-xs text-gray-500 max-w-sm text-center">
                            Rendering authentic document formatting via {viewerEngine === "office" ? "Microsoft Office" : "Google Docs"}...
                          </p>
                        </div>
                      )}

                      <iframe
                        key={`${viewerEngine}-${fileUrl}`}
                        src={activeViewerSrc}
                        title={material?.title || "Document Preview"}
                        className="w-full h-full border-0 bg-white"
                        onLoad={() => setIframeLoaded(true)}
                        allowFullScreen
                      />

                      {/* Fallback hint bar for Office docs */}
                      <div className="bg-white/95 border-t border-gray-200 px-4 py-1.5 text-[11px] text-gray-600 flex items-center justify-between">
                        <span className="truncate">
                          Showing original <strong>.{ext.toUpperCase()}</strong> file as uploaded.
                        </span>
                        <div className="flex items-center gap-2 shrink-0">
                          <button
                            onClick={() => {
                              setViewerEngine((v) => (v === "office" ? "google" : "office"));
                              setIframeLoaded(false);
                            }}
                            className="text-brand-700 hover:text-brand-900 font-bold hover:underline"
                          >
                            Switch to {viewerEngine === "office" ? "Google Viewer" : "Office Viewer"}
                          </button>
                          {isPresentation && (
                            <>
                              <span>•</span>
                              <button
                                onClick={() => setSlideViewMode("cards")}
                                className="text-brand-700 hover:text-brand-900 font-bold hover:underline"
                              >
                                Switch to Slide Deck
                              </button>
                            </>
                          )}
                          <span>•</span>
                          <button
                            onClick={handleDownload}
                            className="text-brand-700 hover:text-brand-900 font-bold hover:underline"
                          >
                            Download .{ext.toUpperCase()}
                          </button>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* PDF PREVIEW */}
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

                  {/* IMAGE PREVIEW */}
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

                  {/* TEXT / CODE PREVIEW */}
                  {isText && (
                    <div className="flex-1 w-full h-full overflow-auto p-4 sm:p-8 bg-gray-900 text-gray-100 font-mono text-xs leading-relaxed">
                      <div className="max-w-4xl mx-auto bg-gray-950 p-6 rounded-xl border border-gray-800 shadow-xl overflow-x-auto">
                        <div className="pb-3 mb-4 border-b border-gray-800 flex justify-between items-center text-gray-400">
                          <span>{material?.title}</span>
                          <span className="uppercase text-[10px]">{ext}</span>
                        </div>
                        <div className="whitespace-pre-wrap">
                          {material?.description || preview?.summary || "Content preview."}
                        </div>
                      </div>
                    </div>
                  )}

                  {/* UNSUPPORTED FORMAT FALLBACK */}
                  {!isOfficeDoc && !isPdf && !isImage && !isText && (
                    <div className="flex-1 w-full flex items-center justify-center p-6">
                      <div className="max-w-md p-8 text-center bg-white rounded-2xl shadow-lg border border-gray-200 mx-4">
                        <div className="h-16 w-16 mx-auto rounded-2xl bg-brand-50 border border-brand-200 flex items-center justify-center text-brand-600 mb-4">
                          <FileText size={32} />
                        </div>
                        <h3 className="text-lg font-bold text-gray-900">{material?.title}</h3>
                        <p className="mt-1 text-xs text-gray-500">
                          {material?.fileType} • {material?.fileSize} • {material?.subject}
                        </p>
                        <p className="mt-4 text-xs text-gray-600 leading-relaxed bg-gray-50 p-3 rounded-lg border border-gray-200">
                          This format can be opened with your native desktop application. Click below to download in its original .{ext.toUpperCase()} format.
                        </p>
                        <button
                          onClick={handleDownload}
                          disabled={downloading}
                          className="btn-primary w-full mt-6 py-2.5 !bg-[#3e362e] hover:!bg-[#2a241e]"
                        >
                          <Download size={16} /> Download {material?.originalName || `File (.${ext})`}
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
