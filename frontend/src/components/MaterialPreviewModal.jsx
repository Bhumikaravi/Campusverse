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
} from "lucide-react";
import api from "../services/api";
import { materialsApi } from "../services/endpoints";
import Loader from "./Loader";
import { useToast } from "../context/ToastContext";

export default function MaterialPreviewModal({ materialId, open, onClose }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // PDF & Viewer States
  const [zoom, setZoom] = useState(100);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [activeSlide, setActiveSlide] = useState(0);

  const { showToast } = useToast();

  useEffect(() => {
    if (!open || !materialId) return;

    setLoading(true);
    setError(null);
    setZoom(100);
    setActiveSlide(0);

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

  const handleDownload = () => {
    try {
      const token = localStorage.getItem("cv-token");
      const downloadUrl = `${api.defaults.baseURL}/materials/${materialId}/download${token ? `?token=${encodeURIComponent(token)}` : ""}`;
      const link = document.createElement("a");
      link.href = downloadUrl;
      link.setAttribute("download", material?.originalName || `${material?.title || "material"}.${(material?.fileType || "pdf").toLowerCase()}`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      showToast("Download initiated", "success");
    } catch {
      showToast("Download failed. Please try again.", "error");
    }
  };

  const handleZoomIn = () => setZoom((z) => Math.min(z + 20, 200));
  const handleZoomOut = () => setZoom((z) => Math.max(z - 20, 60));
  const handleResetZoom = () => setZoom(100);

  const toggleFullscreen = () => {
    setIsFullscreen(!isFullscreen);
  };

  const token = localStorage.getItem("cv-token");
  const rawFileUrl = preview?.fileUrl?.startsWith("http")
    ? preview.fileUrl
    : `${api.defaults.baseURL}${preview?.fileUrl?.replace(/^\/api/, "") || `/materials/${materialId}/file`}`;
  const fileUrl = token
    ? `${rawFileUrl}${rawFileUrl.includes("?") ? "&" : "?"}token=${encodeURIComponent(token)}`
    : rawFileUrl;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-2 sm:p-4 md:p-6">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm transition-opacity"
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
        <div className="flex items-center justify-between border-b border-gray-200 px-5 py-3.5 bg-gray-50/80">
          <div className="min-w-0 pr-4">
            <div className="flex items-center gap-2">
              <span className="rounded bg-brand-100 border border-brand-200 px-2 py-0.5 text-[11px] font-bold text-brand-900 uppercase">
                {material?.fileType || "DOCUMENT"}
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
            <button
              onClick={handleDownload}
              className="btn-primary !py-1.5 !px-3 text-xs flex items-center gap-1.5 shadow-sm"
              title="Download Document"
            >
              <Download size={14} />
              <span className="hidden sm:inline">Download</span>
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

        {/* Description Banner (if available) */}
        {material?.description && (
          <div className="bg-brand-50/60 border-b border-brand-100/60 px-5 py-2 text-xs text-brand-950 flex items-center justify-between">
            <p className="italic line-clamp-1">
              <span className="font-semibold not-italic text-brand-800">Description: </span>
              "{material.description.replace(/^[#*\s]+/, '').replace(/[*_#]+/g, '').trim()}"
            </p>
            <span className="text-[11px] text-brand-700 shrink-0 ml-3">
              {material.fileSize}
            </span>
          </div>
        )}

        {/* Main Body */}
        <div className="relative flex-1 bg-gray-100 overflow-hidden flex flex-col">
          {loading && (
            <div className="flex-1 w-full flex items-center justify-center py-24">
              <Loader label="Loading secure material preview..." />
            </div>
          )}

          {error && !loading && (
            <div className="flex-1 w-full flex items-center justify-center p-6">
              <div className="max-w-md p-6 text-center bg-white rounded-xl shadow border border-red-200 mx-4">
                <AlertCircle size={40} className="mx-auto text-red-500 mb-3" />
                <h3 className="font-bold text-gray-900">Preview Not Available</h3>
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

          {!loading && !error && preview && (
            <>
              {/* PDF PREVIEW */}
              {preview.kind === "pdf" && (
                <div className="flex flex-col w-full h-full">
                  {/* PDF Toolbar */}
                  <div className="flex items-center justify-between bg-white border-b border-gray-200 px-4 py-1.5 text-xs">
                    <span className="text-gray-500 font-medium">Inline PDF Viewer</span>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={handleZoomOut}
                        className="rounded p-1 text-gray-600 hover:bg-gray-100"
                        title="Zoom Out"
                      >
                        <ZoomOut size={15} />
                      </button>
                      <span className="text-[11px] font-semibold w-10 text-center">{zoom}%</span>
                      <button
                        onClick={handleZoomIn}
                        className="rounded p-1 text-gray-600 hover:bg-gray-100"
                        title="Zoom In"
                      >
                        <ZoomIn size={15} />
                      </button>
                      <button
                        onClick={handleResetZoom}
                        className="rounded p-1 text-gray-600 hover:bg-gray-100"
                        title="Reset Zoom"
                      >
                        <RotateCcw size={14} />
                      </button>
                      <a
                        href={fileUrl}
                        target="_blank"
                        rel="noreferrer"
                        className="ml-2 flex items-center gap-1 rounded bg-gray-100 px-2 py-0.5 text-[11px] font-semibold text-gray-700 hover:bg-gray-200"
                      >
                        <ExternalLink size={12} /> New Tab
                      </a>
                    </div>
                  </div>

                  {/* PDF View Container */}
                  <div className="flex-1 w-full h-full overflow-auto flex items-center justify-center p-2 bg-gray-200">
                    <iframe
                      src={`${fileUrl}#zoom=${zoom}`}
                      title={material?.title || "PDF Document"}
                      className="w-full h-full rounded shadow-md border border-gray-300 bg-white"
                      style={{
                        transform: `scale(${zoom > 100 ? zoom / 100 : 1})`,
                        transformOrigin: "top center",
                      }}
                    />
                  </div>
                </div>
              )}

              {/* IMAGE PREVIEW */}
              {preview.kind === "image" && (
                <div className="flex-1 w-full h-full overflow-auto flex items-center justify-center p-4">
                  <img
                    src={fileUrl}
                    alt={material?.title}
                    className="max-w-full max-h-full object-contain rounded-lg shadow-lg border border-gray-300"
                    style={{ transform: `scale(${zoom / 100})`, transition: "transform 0.15s ease-out" }}
                  />
                </div>
              )}

              {/* DOCX HTML PREVIEW */}
              {preview.kind === "html" && (
                <div className="w-full h-full overflow-y-auto p-4 sm:p-8 bg-gray-100">
                  <div className="max-w-3xl mx-auto bg-white rounded-xl shadow-md p-6 sm:p-10 border border-gray-200">
                    <div className="border-b border-gray-200 pb-4 mb-6">
                      <span className="text-xs font-semibold text-brand-700 uppercase tracking-wide">
                        Word Document Preview
                      </span>
                      <h1 className="text-2xl font-bold text-gray-900 mt-1">{material?.title}</h1>
                    </div>
                    <div
                      className="prose prose-sm max-w-none text-gray-800"
                      dangerouslySetInnerHTML={{ __html: preview.html }}
                    />
                  </div>
                </div>
              )}

              {/* PPTX SLIDES PREVIEW */}
              {preview.kind === "slides" && (
                <div className="flex flex-col w-full h-full">
                  {/* Slide controls */}
                  <div className="flex items-center justify-between bg-white border-b border-gray-200 px-4 py-2">
                    <span className="text-xs font-medium text-gray-600 flex items-center gap-1.5">
                      <Layers size={15} className="text-brand-600" />
                      Slide {activeSlide + 1} of {preview.slides?.length || 1}
                    </span>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => setActiveSlide((s) => Math.max(0, s - 1))}
                        disabled={activeSlide === 0}
                        className="btn-secondary !py-1 !px-2 text-xs flex items-center gap-1 disabled:opacity-40"
                      >
                        <ChevronLeft size={14} /> Prev
                      </button>
                      <button
                        onClick={() =>
                          setActiveSlide((s) => Math.min((preview.slides?.length || 1) - 1, s + 1))
                        }
                        disabled={activeSlide === (preview.slides?.length || 1) - 1}
                        className="btn-secondary !py-1 !px-2 text-xs flex items-center gap-1 disabled:opacity-40"
                      >
                        Next <ChevronRight size={14} />
                      </button>
                    </div>
                  </div>

                  {/* Slide Content Box */}
                  <div className="flex-1 w-full overflow-auto flex items-center justify-center p-6 bg-gray-200">
                    <div className="aspect-[16/9] w-full max-w-3xl bg-white rounded-2xl shadow-xl border border-gray-300 p-8 flex flex-col justify-between overflow-y-auto">
                      <div>
                        <span className="text-xs font-bold text-gray-400">SLIDE {activeSlide + 1}</span>
                        <div className="mt-4 whitespace-pre-wrap font-sans text-sm sm:text-base leading-relaxed text-gray-800">
                          {preview.slides?.[activeSlide]?.text || "No text available on this slide."}
                        </div>
                      </div>
                      <div className="pt-4 border-t border-gray-100 flex justify-between text-xs text-gray-400">
                        <span>{material?.subject}</span>
                        <span>CampusVerse Academic Slides</span>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* UNSUPPORTED FORMAT FALLBACK */}
              {preview.kind === "unsupported" && (
                <div className="max-w-md p-8 text-center bg-white rounded-2xl shadow-lg border border-gray-200 mx-4">
                  <div className="h-16 w-16 mx-auto rounded-2xl bg-brand-50 border border-brand-200 flex items-center justify-center text-brand-600 mb-4">
                    <FileText size={32} />
                  </div>
                  <h3 className="text-lg font-bold text-gray-900">{material?.title}</h3>
                  <p className="mt-1 text-xs text-gray-500">
                    {material?.fileType} • {material?.fileSize} • {material?.subject}
                  </p>
                  <p className="mt-4 text-xs text-gray-600 leading-relaxed bg-gray-50 p-3 rounded-lg border border-gray-200">
                    {preview.reason ||
                      "This document format cannot be previewed in the web browser. Please download it to view with your desktop application."}
                  </p>
                  <button onClick={handleDownload} className="btn-primary w-full mt-6 py-2.5">
                    <Download size={16} /> Download File ({material?.fileSize})
                  </button>
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
            <button onClick={handleDownload} className="btn-primary !py-1 !px-3 text-xs">
              <Download size={13} /> Download
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
