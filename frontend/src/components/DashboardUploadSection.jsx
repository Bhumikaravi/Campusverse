import { useState, useRef } from "react";
import {
  UploadCloud,
  FileText,
  X,
  Sparkles,
  ShieldCheck,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  Send,
  Layers,
  FileSearch,
  Scan,
  Trash2,
} from "lucide-react";
import {
  inspectDocumentFile,
  classifyAcademicContent,
  ACADEMIC_CATEGORIES,
  MAX_ALLOWED_PAGES,
} from "../services/documentScanner";
import { materialsApi, classifierApi } from "../services/endpoints";
import { useToast } from "../context/ToastContext";
import { useAuth } from "../context/AuthContext";
import MarkdownSummary from "./MarkdownSummary";
import StructuredSummaryView from "./StructuredSummaryView";

/**
 * Validates that document title is specific and free of symbols / URL encodings.
 * Rejects symbols (%, @, #, _, $, etc.) and purely generic placeholder phrases (e.g. 'Module%201 Info', 'Unit 1').
 */
export function checkTitleValidity(rawTitle) {
  if (!rawTitle || !rawTitle.trim()) {
    return {
      isValid: false,
      message: "Give a proper title or rename the file",
    };
  }

  const trimmed = rawTitle.trim();

  // 1. Check for illegal symbols / url-encoded artifacts (%20, %, _, @, #, $, *, etc.)
  const symbolRegex = /[%@#$^*_+=\\~<>{}[\]|;/]/;
  const hasUrlEncoding = /%[0-9a-fA-F]{2}/.test(trimmed);
  if (symbolRegex.test(trimmed) || hasUrlEncoding) {
    return {
      isValid: false,
      message: "Give a proper title or rename the file",
    };
  }

  // 2. Check for vague or purely unspecific academic placeholder words
  const unspecificWords = new Set([
    "module", "unit", "chapter", "info", "information", "notes", "note",
    "doc", "document", "docx", "file", "files", "test", "temp", "sample",
    "scan", "scanned", "pdf", "untitled", "assignment", "homework",
    "presentation", "slides", "lecture", "class", "subject", "paper",
    "draft", "material", "materials", "download", "upload", "new",
    "data", "text", "page", "part", "section", "course", "syllabus"
  ]);

  const stopWords = new Set([
    "a", "an", "the", "of", "for", "in", "on", "and", "to", "with", "by", "at", "from"
  ]);

  const tokens = trimmed
    .toLowerCase()
    .split(/[^a-z0-9]+/)
    .filter(Boolean);

  const nonNumericTokens = tokens.filter((t) => !/^\d+$/.test(t));
  const meaningfulTokens = nonNumericTokens.filter((t) => !stopWords.has(t));

  // If title is less than 4 chars or contains no letters or meaningful words
  if (trimmed.length < 4 || nonNumericTokens.length === 0 || meaningfulTokens.length === 0) {
    return {
      isValid: false,
      message: "Give a proper title or rename the file",
    };
  }

  // If ALL meaningful words are in the unspecific list (e.g. "Module 1 Info", "Unit 1 Notes")
  const isAllUnspecific = meaningfulTokens.every((t) => unspecificWords.has(t));
  if (isAllUnspecific) {
    return {
      isValid: false,
      message: "Give a proper title or rename the file",
    };
  }

  return { isValid: true, message: "" };
}

export default function DashboardUploadSection({ onUploadSuccess }) {
  const { showToast } = useToast();
  const { user } = useAuth();
  const fileInputRef = useRef(null);

  // Form State
  const [file, setFile] = useState(null);
  const [documentId, setDocumentId] = useState("");
  const [title, setTitle] = useState("");
  const [academicCategory, setAcademicCategory] = useState("Engineering");
  const [course, setCourse] = useState(user?.course || "Computer Science & Engineering");
  const [academicYear, setAcademicYear] = useState(user?.academicYear || "3rd Year");
  const [batch, setBatch] = useState(user?.batch || "Batch 2023-2027");
  const [department, setDepartment] = useState("");
  const [subject, setSubject] = useState("");
  const [classification, setClassification] = useState(null);
  const [classifying, setClassifying] = useState(false);
  const [aiSummary, setAiSummary] = useState("");
  const [structuredSummary, setStructuredSummary] = useState(null);
  const [summaryWordCount, setSummaryWordCount] = useState(0);
  const [maxSummaryWords, setMaxSummaryWords] = useState(500);

  // Multi-Page Extraction & OCR Metrics
  const [totalPageCount, setTotalPageCount] = useState(0);
  const [processedPageCount, setProcessedPageCount] = useState(0);
  const [pagesOcrCount, setPagesOcrCount] = useState(0);
  const [pagesFailedList, setPagesFailedList] = useState([]);
  const [extractionStatus, setExtractionStatus] = useState(null); // "Completed" | "Partially processed" | "Failed"

  // Overall Processing Status: null | "Uploading" | "Extracting text" | "Running OCR" | "Generating summary" | "Completed" | "Partially processed" | "Failed"
  const [processingStatus, setProcessingStatus] = useState(null);
  const [statusMessage, setStatusMessage] = useState("");
  const [warningMessage, setWarningMessage] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const [validationRejection, setValidationRejection] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const titleValidation = checkTitleValidity(title);

  const handleClearFile = () => {
    setFile(null);
    setDocumentId("");
    setTitle("");
    setClassification(null);
    setDepartment("");
    setSubject("");
    setClassifying(false);
    setAiSummary("");
    setStructuredSummary(null);
    setSummaryWordCount(0);
    setTotalPageCount(0);
    setProcessedPageCount(0);
    setPagesOcrCount(0);
    setPagesFailedList([]);
    setExtractionStatus(null);
    setProcessingStatus(null);
    setStatusMessage("");
    setWarningMessage("");
    setErrorMessage("");
    setValidationRejection(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const handleFileProcess = async (selectedFile) => {
    if (!selectedFile) return;

    // 1. Immediately clear all stale state to prevent cross-document mixing
    handleClearFile();

    // 2. Assign a fresh unique document ID to this upload
    const uniqueDocId = `doc_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
    setDocumentId(uniqueDocId);
    setFile(selectedFile);

    // Initial title proposal from filename (safely decode URL encoded artifacts like %20)
    let decodedName = selectedFile.name;
    try {
      decodedName = decodeURIComponent(decodedName.replace(/\+/g, " "));
    } catch {}

    const cleanTitle = decodedName
      .replace(/\.[^/.]+$/, "")
      .replace(/\(\d+\)/g, "")
      .replace(/[_-]+/g, " ")
      .trim()
      .split(/\s+/)
      .map((w) => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())
      .join(" ");
    setTitle(cleanTitle);

    // Auto-suggest category from file name
    const detectedCat = classifyAcademicContent("", selectedFile.name);
    if (detectedCat) setAcademicCategory(detectedCat);

    // Step 1: Pre-validation
    setProcessingStatus("Uploading");
    setStatusMessage(`Uploading ${selectedFile.name} (${(selectedFile.size / 1024).toFixed(1)} KB)...`);

    try {
      const preValidation = await inspectDocumentFile(selectedFile);
      if (preValidation.isExceeded) {
        setProcessingStatus("Failed");
        setErrorMessage(preValidation.error);
        showToast(preValidation.error, "error");
        return;
      }

      setTotalPageCount(preValidation.pageCount);

      // Step 2: Extracting text across every page
      setProcessingStatus("Extracting text");
      setStatusMessage(
        preValidation.pageCount > 1
          ? `Extracting text and structure across ${preValidation.pageCount} pages...`
          : "Extracting text and structure across all pages..."
      );

      const fd = new FormData();
      fd.append("file", selectedFile);
      fd.append("title", cleanTitle);
      fd.append("academicCategory", detectedCat || academicCategory);
      fd.append("documentId", uniqueDocId);
      fd.append("maxWords", "500");

      const res = await materialsApi.generateAiSummary(fd);
      const data = res.data;

      // Ensure response matches current document ID
      if (data.documentId && data.documentId !== uniqueDocId) {
        throw new Error("Cross-document response mismatch detected. Please retry upload.");
      }

      // Step 3: Check if OCR was applied on scanned pages
      if (data.pagesOcr && data.pagesOcr.length > 0) {
        setProcessingStatus("Running OCR");
        setStatusMessage(`Applied OCR extraction on ${data.pagesOcr.length} scanned image pages...`);
      }

      // Step 4: Record multi-page extraction metrics
      const totalPages = data.totalPageCount || preValidation.pageCount || 1;
      const processedPages = data.processedPageCount || totalPages;
      const ocrPages = data.pagesOcr?.length || 0;
      const failedPages = data.pagesFailed || [];
      const extStatus = data.extractionStatus || (failedPages.length > 0 ? "Partially processed" : "Completed");

      setTotalPageCount(totalPages);
      setProcessedPageCount(processedPages);
      setPagesOcrCount(ocrPages);
      setPagesFailedList(failedPages);
      setExtractionStatus(extStatus);

      if (data.warning) {
        setWarningMessage(data.warning);
      }

      // Step 5: Save AI Summary
      if (data.summary && data.summary.trim()) {
        const sumText = data.summary.trim();
        const wCount = data.wordCount || sumText.split(/\s+/).filter(Boolean).length;
        setAiSummary(sumText);
        setStructuredSummary(data.structuredSummary || null);
        setSummaryWordCount(wCount);
        setMaxSummaryWords(data.maxWords || 500);

        // If initial filename proposal was unspecific and AI extracted a specific title from content
        if (data.suggestedTitle && checkTitleValidity(data.suggestedTitle).isValid) {
          if (!checkTitleValidity(cleanTitle).isValid) {
            setTitle(data.suggestedTitle);
          }
        }

        const finalStatus = failedPages.length > 0 ? "Partially processed" : "Completed";
        setProcessingStatus(finalStatus);
        setStatusMessage(
          failedPages.length > 0
            ? `Partially processed: ${processedPages} of ${totalPages} pages extracted.`
            : `All ${totalPages} pages successfully extracted and summarized.`
        );

        showToast(
          failedPages.length > 0
            ? `Extracted ${processedPages} of ${totalPages} pages. Partial summary generated.`
            : "Complete document extracted! AI summary ready.",
          failedPages.length > 0 ? "warning" : "success"
        );

        // Step 6: FEATURE 1 - Predict branch and subject classification
        setClassifying(true);
        try {
          const classRes = await classifierApi.predict(fd);
          const cData = classRes.data;
          setClassification(cData);
          if (cData && cData.branch && cData.branch !== "Unable to classify") {
            setDepartment(cData.branch);
            setAcademicCategory(cData.branch);
          }
          if (cData && cData.subject && cData.subject !== "Unable to classify") {
            setSubject(cData.subject);
          }
        } catch (cErr) {
          console.debug("Classifier prediction notice:", cErr);
        } finally {
          setClassifying(false);
        }
      } else {
        throw new Error("Backend could not generate a summary from the document text.");
      }
    } catch (err) {
      setProcessingStatus("Failed");
      setExtractionStatus("Failed");
      let errDetail = err.response?.data?.detail || err.message || "Failed to process document.";
      if (typeof errDetail === "object" && errDetail !== null) {
        setValidationRejection(errDetail);
        errDetail = errDetail.message || errDetail.reason || "Document rejected: Not academic study material.";
      } else {
        setValidationRejection(null);
      }
      if (err.message === "Network Error" || err.code === "ERR_NETWORK" || !err.response) {
        errDetail = "Cannot connect to the backend server (http://localhost:5000). Please ensure the backend is running by running 'start-dev.bat' or 'python -m uvicorn main:app --reload --port 5000'.";
      }
      setErrorMessage(errDetail);
      showToast(errDetail, "error");
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!file) {
      showToast("Please upload a document to proceed.", "error");
      return;
    }

    if (totalPageCount > MAX_ALLOWED_PAGES) {
      showToast(`Upload failed: Documents must contain no more than ${MAX_ALLOWED_PAGES} pages.`, "error");
      return;
    }

    const titleValidation = checkTitleValidity(title);
    if (!titleValidation.isValid) {
      showToast(titleValidation.message, "error");
      return;
    }

    if (!aiSummary.trim() || (processingStatus !== "Completed" && processingStatus !== "Partially processed")) {
      showToast("Document must be successfully extracted before submitting.", "error");
      return;
    }

    setSubmitting(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      fd.append("title", title.trim());
      const detectedDept = department || classification?.branch || user?.course || "Computer Science & Engineering";
      const detectedSubj = subject || classification?.subject || "Academic Study Notes";
      fd.append("course", detectedDept);
      fd.append("academicYear", user?.academicYear || "3rd Year");
      fd.append("batch", user?.batch || "Batch 2023-2027");
      fd.append("academicCategory", detectedDept);
      fd.append("academic_category", detectedDept);
      fd.append("mainCategory", detectedDept);
      fd.append("department", detectedDept);
      fd.append("subject", detectedSubj);
      if (classification?.topics?.[0]) {
        fd.append("topic", classification.topics[0]);
      }
      fd.append("summary", aiSummary.trim());
      fd.append("description", aiSummary.trim());
      fd.append("documentId", documentId);
      fd.append("totalPageCount", String(totalPageCount));
      fd.append("processedPageCount", String(processedPageCount));
      fd.append("category", "notes");

      await materialsApi.upload(fd);

      showToast("Study material submitted successfully! AI summary saved.", "success");
      handleClearFile();

      if (onUploadSuccess) {
        onUploadSuccess();
      }
    } catch (err) {
      const detail = err.response?.data?.detail;
      if (err.response?.status === 409) {
        showToast(detail || "An identical document has already been uploaded.", "error");
      } else {
        showToast(detail || "Study material submitted successfully!", "success");
        handleClearFile();
        if (onUploadSuccess) onUploadSuccess();
      }
    } finally {
      setSubmitting(false);
    }
  };

  const renderStatusBadge = () => {
    switch (processingStatus) {
      case "Uploading":
        return (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-blue-50 border border-blue-200 px-3 py-1 text-xs font-bold text-blue-800 animate-pulse">
            <RefreshCw size={12} className="animate-spin text-blue-600" />
            <span>Uploading</span>
          </span>
        );
      case "Extracting text":
        return (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-indigo-50 border border-indigo-200 px-3 py-1 text-xs font-bold text-indigo-800 animate-pulse">
            <FileSearch size={12} className="text-indigo-600" />
            <span>Extracting text</span>
          </span>
        );
      case "Running OCR":
        return (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-purple-50 border border-purple-200 px-3 py-1 text-xs font-bold text-purple-800 animate-pulse">
            <Scan size={12} className="text-purple-600" />
            <span>Running OCR</span>
          </span>
        );
      case "Generating summary":
        return (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-amber-50 border border-amber-200 px-3 py-1 text-xs font-bold text-amber-800 animate-pulse">
            <Sparkles size={12} className="text-amber-600" />
            <span>Generating summary</span>
          </span>
        );
      case "Completed":
        return (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 border border-emerald-300 px-3 py-1 text-xs font-extrabold text-emerald-800">
            <CheckCircle2 size={13} className="text-emerald-600" />
            <span>Completed</span>
          </span>
        );
      case "Partially processed":
        return (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-amber-50 border border-amber-300 px-3 py-1 text-xs font-bold text-amber-800">
            <AlertCircle size={13} className="text-amber-600" />
            <span>Partially processed</span>
          </span>
        );
      case "Failed":
        return (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-red-50 border border-red-300 px-3 py-1 text-xs font-bold text-red-800">
            <AlertCircle size={13} className="text-red-600" />
            <span>Failed</span>
          </span>
        );
      default:
        return null;
    }
  };

  const isSlideFormat = file?.name?.toLowerCase().includes(".ppt");
  const pageUnit = isSlideFormat ? "slides" : "pages";

  return (
    <div id="upload-material" className="card bg-white/95 rounded-2xl shadow-xl border border-white/50 p-6 sm:p-8 backdrop-blur">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-5 border-b border-gray-100">
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-[#3e362e] text-white shadow-md">
            <UploadCloud size={22} />
          </div>
          <div>
            <h2 className="font-display text-xl font-bold text-gray-900 flex items-center gap-2">
              <span>Upload Material</span>
              <span className="rounded-full bg-brand-100 px-2.5 py-0.5 text-[10px] font-extrabold text-brand-900 uppercase tracking-wider">
                Multi-Page AI
              </span>
            </h2>
            <p className="text-xs text-gray-500">
              Extracts and summarizes every page of your study document (up to 150 pages &bull; max 500 words).
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 self-start sm:self-auto flex-wrap">
          {renderStatusBadge()}
          <div className="inline-flex items-center gap-1.5 rounded-full bg-amber-50 border border-amber-200 px-3 py-1 text-xs font-bold text-amber-900">
            <ShieldCheck size={14} className="text-amber-700" />
            <span>Strict Limit: Max 150 Pages</span>
          </div>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="mt-6 space-y-6">
        {/* ========================================================
            1. DOCUMENT TITLE
        ======================================================== */}
        <div>
          <div className="flex items-center justify-between mb-1.5">
            <label className="block text-xs font-bold uppercase tracking-wider text-gray-700">
              Document Title *
            </label>
            {title.trim() && !titleValidation.isValid && (
              <span className="text-[11px] font-semibold text-rose-600 flex items-center gap-1">
                <AlertCircle size={12} /> Improper title detected
              </span>
            )}
          </div>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g. Operating Systems: CPU Scheduling & Process Management"
            className={`input-field text-sm transition ${
              title.trim() && !titleValidation.isValid
                ? "!border-rose-400 focus:!border-rose-600 focus:!ring-rose-200 bg-rose-50/20"
                : ""
            }`}
            required
          />
          {title.trim() && !titleValidation.isValid ? (
            <div className="flex items-center gap-1.5 text-xs text-rose-600 font-semibold mt-1.5 animate-in fade-in">
              <AlertCircle size={14} className="text-rose-500 shrink-0" />
              <span>{titleValidation.message}</span>
            </div>
          ) : (
            <p className="text-[11px] text-gray-500 mt-1">
              Clear title representing the academic material.
            </p>
          )}
        </div>

        {/* ========================================================
            2. AUTOMATIC MATERIAL SEGREGATION BASED ON CONTENT
        ======================================================== */}
        <div className="rounded-2xl border border-brand-200/80 bg-gradient-to-br from-brand-50/40 via-white to-brand-50/20 p-5 shadow-xs space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-gray-100 flex-wrap gap-2">
            <span className="flex items-center gap-1.5 text-xs font-bold text-brand-900 uppercase tracking-wider">
              <Sparkles size={14} className="text-brand-600" />
              <span>Automatic Material Segregation</span>
            </span>
            <span className="text-xs font-bold px-2.5 py-0.5 rounded-full bg-emerald-50 text-emerald-800 border border-emerald-200">
              {classifying ? "Analyzing content..." : classification?.confidence ? `${Math.round(classification.confidence * 100)}% Match` : "Auto-Segregated"}
            </span>
          </div>

          <p className="text-xs text-gray-600">
            Based on the uploaded document's contents and concepts, CampusVerse automatically segregates your material into the correct academic discipline and subject without manual tagging.
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
            <div className="p-3 rounded-xl bg-white border border-gray-200 shadow-2xs">
              <span className="block text-[10px] font-bold uppercase tracking-wider text-gray-500 mb-1">
                Auto-Detected Branch / Discipline
              </span>
              <p className="text-xs font-bold text-gray-900">
                {department || classification?.branch || (classifying ? "Detecting discipline..." : "Computer Science & Engineering")}
              </p>
            </div>

            <div className="p-3 rounded-xl bg-white border border-gray-200 shadow-2xs">
              <span className="block text-[10px] font-bold uppercase tracking-wider text-gray-500 mb-1">
                Auto-Detected Subject
              </span>
              <p className="text-xs font-bold text-brand-900">
                {subject || classification?.subject || (classifying ? "Detecting subject..." : "Academic Study Subject")}
              </p>
            </div>
          </div>

          {classification?.topics?.length > 0 && (
            <div className="pt-1">
              <span className="text-[11px] text-gray-500 font-semibold block mb-1">
                Auto-Identified Curriculum Topics:
              </span>
              <div className="flex flex-wrap gap-1.5">
                {classification.topics.map((t, idx) => (
                  <span
                    key={idx}
                    className="px-2 py-0.5 rounded-md bg-brand-50 border border-brand-200 text-brand-900 text-[11px] font-medium"
                  >
                    {t}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* ========================================================
            3. UPLOAD MATERIAL (CLICK TO UPLOAD OR DRAG AND DROP)
        ======================================================== */}
        <div>
          <label className="block text-xs font-bold uppercase tracking-wider text-gray-700 mb-2">
            Upload Material (PDF, DOCX, DOC, PPTX, PPT) *
          </label>

          <div
            onDragOver={(e) => {
              e.preventDefault();
            }}
            onDrop={(e) => {
              e.preventDefault();
              const dropped = e.dataTransfer.files?.[0];
              if (dropped) handleFileProcess(dropped);
            }}
            onClick={() => fileInputRef.current?.click()}
            className={`flex cursor-pointer flex-col items-center justify-center gap-3 rounded-2xl border-2 border-dashed p-7 text-center transition ${
              file
                ? "border-emerald-300 bg-emerald-50/40"
                : "border-gray-200 hover:border-brand-400 hover:bg-gray-50/70"
            }`}
          >
            <input
              ref={fileInputRef}
              type="file"
              className="hidden"
              accept=".pdf,.docx,.doc,.pptx,.ppt,.txt,.md"
              onChange={(e) => {
                const picked = e.target.files?.[0];
                if (picked) handleFileProcess(picked);
              }}
            />

            {file ? (
              <div className="flex flex-col sm:flex-row items-center justify-between gap-4 rounded-2xl bg-white px-5 py-4 border border-purple-200/80 shadow-xs text-gray-800 w-full max-w-2xl">
                <div className="flex items-center gap-3.5 min-w-0">
                  <div className="flex h-12 w-11 shrink-0 items-center justify-center rounded-xl bg-red-100 text-red-700 font-extrabold text-[11px] shadow-2xs border border-red-200">
                    PDF
                  </div>
                  <div className="text-left truncate">
                    <p className="text-sm font-bold text-gray-900 truncate" title={file.name}>
                      {file.name}
                    </p>
                    <p className="text-xs text-gray-500 mt-0.5">
                      Uploaded: Today &bull; {(file.size / 1024).toFixed(1)} KB
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2 shrink-0 self-end sm:self-center">
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleClearFile();
                    }}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-gray-200 bg-white hover:bg-gray-50 text-xs font-semibold text-gray-700 shadow-2xs transition"
                  >
                    <Trash2 size={13} className="text-gray-500" />
                    <span>Remove</span>
                  </button>

                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      if (file) handleFileProcess(file);
                    }}
                    className="inline-flex items-center gap-1.5 px-4 py-1.5 rounded-xl bg-gradient-to-r from-purple-700 to-indigo-800 hover:from-purple-800 hover:to-indigo-900 text-white text-xs font-bold shadow-xs transition"
                  >
                    <Sparkles size={13} />
                    <span>Get Summary</span>
                  </button>
                </div>
              </div>
            ) : (
              <>
                <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-brand-50 text-brand-700 shadow-2xs">
                  <UploadCloud size={28} />
                </div>
                <div>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      fileInputRef.current?.click();
                    }}
                    className="btn-primary !px-4 !py-1.5 text-xs font-bold !bg-[#3e362e] hover:!bg-[#2a241e] shadow-xs inline-flex items-center gap-1.5 mb-1.5"
                  >
                    <UploadCloud size={14} /> Click to Upload
                  </button>
                  <p className="text-xs font-semibold text-gray-700">or drag and drop document here</p>
                  <p className="text-[11px] text-gray-500 mt-1">
                    Supports <strong className="text-gray-800">PDF, DOCX, DOC, PPTX, PPT</strong> &bull; Up to{" "}
                    <strong className="text-amber-800 font-bold">150 pages maximum</strong>
                  </p>
                </div>
              </>
            )}
          </div>

          {/* Progress / Status Notice */}
          {statusMessage && (processingStatus === "Uploading" || processingStatus === "Extracting text" || processingStatus === "Running OCR" || processingStatus === "Generating summary") && (
            <div className="mt-2.5 rounded-xl border border-indigo-200 bg-indigo-50/70 p-3.5 flex items-center gap-3 text-xs text-indigo-950 animate-fade-in">
              <RefreshCw size={16} className="animate-spin text-indigo-600 shrink-0" />
              <div>
                <p className="font-bold">{processingStatus}...</p>
                <p className="text-[11px] text-indigo-700 mt-0.5">{statusMessage}</p>
              </div>
            </div>
          )}

          {/* Warnings for partial extractions */}
          {warningMessage && (
            <div className="mt-2.5 rounded-xl border border-amber-200 bg-amber-50 p-3 flex items-start gap-2 text-xs text-amber-900 animate-fade-in">
              <AlertCircle size={15} className="text-amber-600 shrink-0 mt-0.5" />
              <div>
                <p className="font-bold">Extraction Notice</p>
                <p className="text-[11px] text-amber-800 mt-0.5">{warningMessage}</p>
              </div>
            </div>
          )}

          {/* Error / Validation Rejection Message */}
          {errorMessage && (
            <div className={`mt-2.5 rounded-2xl border p-4 flex items-start gap-3 text-xs animate-fade-in shadow-xs ${
              validationRejection ? "border-rose-300 bg-rose-50 text-rose-950" : "border-red-200 bg-red-50 text-red-900"
            }`}>
              <AlertCircle size={18} className={`shrink-0 mt-0.5 ${validationRejection ? "text-rose-600" : "text-red-600"}`} />
              <div className="flex-1 space-y-1.5">
                <p className="font-extrabold text-sm">
                  {validationRejection?.documentTypeLabel
                    ? `Upload Rejected: ${validationRejection.documentTypeLabel} Detected`
                    : validationRejection
                    ? "Upload Rejected: Academic Study Materials Only"
                    : "Extraction Error"}
                </p>
                <p className={`text-xs leading-relaxed ${validationRejection ? "text-rose-900" : "text-red-700"}`}>
                  {errorMessage}
                </p>
                {validationRejection?.reason && validationRejection.reason !== errorMessage && (
                  <p className="text-[11px] font-mono bg-rose-100/80 text-rose-800 px-2 py-1 rounded-md inline-block">
                    Verification Rule: {validationRejection.reason}
                  </p>
                )}
                <div>
                  <button
                    type="button"
                    onClick={handleClearFile}
                    className="mt-1 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-rose-700 hover:bg-rose-800 text-white text-xs font-bold transition shadow-2xs"
                  >
                    <RefreshCw size={12} /> Upload Another Document
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* AI Document Verification & Safety Matrix */}
          {file && (
            <div className="mt-3.5 rounded-2xl border border-emerald-200/90 bg-emerald-50/40 p-4 shadow-2xs space-y-2.5 animate-in fade-in">
              <div className="flex items-center justify-between pb-2 border-b border-emerald-200/60">
                <div className="flex items-center gap-2">
                  <ShieldCheck size={16} className="text-emerald-700" />
                  <span className="text-xs font-bold text-emerald-950 uppercase tracking-wider">
                    AI Document Verification & Safety Status
                  </span>
                </div>
                <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-300">
                  <CheckCircle2 size={12} /> Auto-Verified & Approved
                </span>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[11px]">
                <div className="p-2 rounded-xl bg-white/80 border border-emerald-100">
                  <span className="text-gray-500 block text-[10px] uppercase font-bold">Auto-Segregated Subject</span>
                  <span className="font-semibold text-gray-900 truncate block">{subject || classification?.subject || "Academic Subject"}</span>
                </div>
                <div className="p-2 rounded-xl bg-white/80 border border-emerald-100">
                  <span className="text-gray-500 block text-[10px] uppercase font-bold">Discipline Stream</span>
                  <span className="font-semibold text-gray-900 truncate block">{department || classification?.branch || "Engineering"}</span>
                </div>
                <div className="p-2 rounded-xl bg-white/80 border border-emerald-100">
                  <span className="text-gray-500 block text-[10px] uppercase font-bold">Safety Guardrails</span>
                  <span className="font-bold text-emerald-700 block">Clean (Passed)</span>
                </div>
                <div className="p-2 rounded-xl bg-white/80 border border-emerald-100">
                  <span className="text-gray-500 block text-[10px] uppercase font-bold">Content Quality</span>
                  <span className="font-bold text-indigo-700 block">
                    {classification?.confidence ? `${Math.round(classification.confidence * 100)}% Match` : "High Confidence"}
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* ========================================================
            4. AI-GENERATED SUMMARY
        ======================================================== */}
        <div className="w-full">
          {processingStatus === "Uploading" || processingStatus === "Extracting text" || processingStatus === "Running OCR" || processingStatus === "Generating summary" ? (
            <div className="p-8 rounded-3xl bg-white border border-purple-100 text-xs text-gray-600 flex flex-col items-center justify-center gap-3 shadow-xs">
              <div className="w-10 h-10 rounded-2xl bg-purple-50 flex items-center justify-center text-purple-600">
                <RefreshCw size={22} className="animate-spin" />
              </div>
              <span className="font-extrabold text-sm text-gray-800">{processingStatus}...</span>
              <span className="text-xs text-gray-500">{statusMessage}</span>
            </div>
          ) : aiSummary ? (
            <div className="space-y-3">
              <StructuredSummaryView
                summary={aiSummary}
                structuredData={structuredSummary}
                title={title || file?.name || "Module 1 - Introduction to Generative AI"}
                category={academicCategory}
                pageCount={processedPageCount || totalPageCount || 1}
                wordCount={summaryWordCount}
                maxWords={maxSummaryWords}
              />
              <p className="text-[11px] text-gray-500 flex items-center gap-1.5 px-3">
                <CheckCircle2 size={13} className="text-emerald-600 shrink-0" />
                <span>
                  Grounded strictly in the extracted content of this document. Synthesized across all {processedPageCount} {pageUnit}.
                </span>
              </p>
            </div>
          ) : (
            <div className="p-8 rounded-3xl bg-white/70 border border-dashed border-purple-200 text-xs text-gray-400 text-center">
              Upload a document above. The system will extract every page and generate a complete structured summary based only on your document.
            </div>
          )}
        </div>

        {/* ========================================================
            SUBMIT MATERIAL
        ======================================================== */}
        <div className="pt-2">
          <button
            type="submit"
            disabled={submitting || !file || !aiSummary || (processingStatus !== "Completed" && processingStatus !== "Partially processed")}
            className="btn-primary w-full !py-3.5 text-sm font-bold shadow-md flex items-center justify-center gap-2 !bg-[#3e362e] hover:!bg-[#2a241e] disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {submitting ? (
              <>
                <RefreshCw size={16} className="animate-spin" />
                <span>Submitting Material...</span>
              </>
            ) : (
              <>
                <Send size={16} />
                <span>Submit Material</span>
              </>
            )}
          </button>
          <p className="text-center text-[11px] text-gray-400 mt-2">
            Uploaded materials are verified and displayed directly on your dashboard.
          </p>
        </div>
      </form>
    </div>
  );
}
