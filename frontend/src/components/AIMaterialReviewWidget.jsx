import { useState, useRef } from "react";
import { Bot, UploadCloud, FileText, X, RefreshCw, CheckCircle2, Send } from "lucide-react";
import { materialsApi } from "../services/endpoints";
import { useToast } from "../context/ToastContext";

export default function AIMaterialReviewWidget({ onMaterialPublished }) {
  const { showToast } = useToast();
  const fileInputRef = useRef(null);

  const [file, setFile] = useState(null);
  const [dragOver, setDragOver] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [summary, setSummary] = useState("");
  const [detectedTitle, setDetectedTitle] = useState("");

  const analyzeFile = async (f) => {
    if (!f) return;
    setFile(f);
    setAnalyzing(true);
    setSummary("");

    const fd = new FormData();
    fd.append("file", f);

    try {
      const res = await materialsApi.generateAiSummary(fd);
      setSummary(res.data?.summary || "");
      setDetectedTitle(res.data?.title || f.name.replace(/\.[^/.]+$/, ""));
      showToast("AI Chatbot analyzed document & generated concise summary!", "success");
    } catch {
      showToast("Could not analyze file right now.", "error");
    } finally {
      setAnalyzing(false);
    }
  };

  const handleClear = () => {
    setFile(null);
    setSummary("");
    setDetectedTitle("");
  };

  return (
    <div className="card bg-white rounded-2xl shadow-md border border-gray-100 p-6">
      <div className="flex items-center gap-3 pb-4 border-b border-gray-100">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#3e362e] text-white">
          <Bot size={20} />
        </div>
        <div>
          <h3 className="font-display text-lg font-bold text-gray-900">
            AI Chatbot Summary Generator
          </h3>
          <p className="text-xs text-gray-500">
            Automatically analyzes uploaded study documents and generates concise summaries.
          </p>
        </div>
      </div>

      <div className="mt-5 space-y-4">
        {/* Dropzone */}
        <div
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragOver(false);
            if (e.dataTransfer.files?.[0]) analyzeFile(e.dataTransfer.files[0]);
          }}
          onClick={() => fileInputRef.current?.click()}
          className={`flex cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed p-6 text-center transition ${
            dragOver ? "border-brand-500 bg-brand-50" : "border-gray-200 hover:border-brand-400 hover:bg-gray-50/60"
          }`}
        >
          <input
            ref={fileInputRef}
            type="file"
            className="hidden"
            accept=".pdf,.docx,.doc,.txt,.pptx,.png,.jpg,.jpeg,.webp"
            onChange={(e) => e.target.files?.[0] && analyzeFile(e.target.files[0])}
          />

          {file ? (
            <div className="flex items-center gap-3 rounded-xl bg-brand-50 px-4 py-2 border border-brand-200 text-brand-900">
              <FileText size={20} className="text-brand-600 shrink-0" />
              <div className="text-left min-w-0">
                <p className="text-xs font-bold text-gray-900 truncate max-w-xs">{file.name}</p>
                <p className="text-[11px] text-gray-500">{(file.size / 1024).toFixed(1)} KB</p>
              </div>
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  handleClear();
                }}
                className="ml-2 rounded-full p-1 text-gray-400 hover:text-red-600"
              >
                <X size={15} />
              </button>
            </div>
          ) : (
            <>
              <UploadCloud size={28} className="text-gray-400" />
              <p className="text-xs font-semibold text-gray-700">
                Select or drag a study document to analyze
              </p>
              <p className="text-[11px] text-gray-400">PDF, DOCX, PPTX up to 25MB</p>
            </>
          )}
        </div>

        {/* AI Summary Output */}
        {analyzing && (
          <div className="p-4 rounded-xl bg-gray-50 border border-gray-100 flex items-center justify-center gap-2 text-xs text-gray-600">
            <RefreshCw size={14} className="animate-spin text-brand-600" />
            <span>AI Chatbot analyzing document concepts...</span>
          </div>
        )}

        {summary && !analyzing && (
          <div className="rounded-xl border border-brand-200 bg-brand-50/50 p-4 space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="font-bold text-gray-900 flex items-center gap-1.5">
                <CheckCircle2 size={14} className="text-emerald-600" />
                AI-Generated Summary
              </span>
              <span className="text-[11px] font-semibold text-brand-800 bg-brand-100 px-2 py-0.5 rounded">
                {summary.split(/\s+/).length} words
              </span>
            </div>
            <p className="text-xs text-gray-800 leading-relaxed font-medium italic bg-white p-3 rounded-lg border border-brand-100">
              &ldquo;{summary}&rdquo;
            </p>
            <p className="text-[11px] text-gray-400">
              Accurate, concise summary generated automatically. No manual typing required.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
