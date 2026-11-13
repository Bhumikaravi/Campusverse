import { useState, useRef, useEffect, useMemo } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  Sparkles,
  UploadCloud,
  FileText,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Download,
  Check,
  X,
  Edit3,
  RefreshCw,
  ExternalLink,
  ChevronRight,
  ShieldCheck,
  Stethoscope,
  BookOpen,
  Filter,
  Layers,
  ArrowRight,
  Send,
} from "lucide-react";
import { scanningBoothApi, categoriesApi } from "../services/endpoints";
import { useToast } from "../context/ToastContext";
import { useAuth } from "../context/AuthContext";
import Loader from "../components/Loader";

const DEMO_SAMPLES = [
  {
    label: "Hypertension Clinical Guide (Med PDF)",
    fileUrl: "/sample_files/med_cardio_hypertension_clinical_guide.pdf",
    fileName: "med_cardio_hypertension_clinical_guide.pdf",
    mainCategory: "General Medicine",
    subcategory: "Cardiovascular Medicine",
    subject: "Cardiovascular Medicine",
  },
  {
    label: "DSA AVL Trees (CSE PDF)",
    fileUrl: "/sample_files/cse_dsa_balanced_trees_graphs_notes.pdf",
    fileName: "cse_dsa_balanced_trees_graphs_notes.pdf",
    mainCategory: "Computer Science and Engineering",
    subcategory: "Data Structures and Algorithms",
    subject: "Data Structures & Algorithms",
  },
  {
    label: "RCC Beam Design (Civil PDF)",
    fileUrl: "/sample_files/civil_structural_rcc_beam_design.pdf",
    fileName: "civil_structural_rcc_beam_design.pdf",
    mainCategory: "Civil Engineering",
    subcategory: "Structural Engineering",
    subject: "Structural Engineering",
  },
  {
    label: "Thermodynamics (Mech PDF)",
    fileUrl: "/sample_files/mech_thermo_laws_rankine_cycles.pdf",
    fileName: "mech_thermo_laws_rankine_cycles.pdf",
    mainCategory: "Mechanical Engineering",
    subcategory: "Thermodynamics",
    subject: "Engineering Thermodynamics",
  },
];

export default function ScanningBooth() {
  const { user } = useAuth();
  const { showToast } = useToast();
  const navigate = useNavigate();

  const [categoriesTree, setCategoriesTree] = useState([]);
  const [selectedMainCat, setSelectedMainCat] = useState("General Medicine");
  const [selectedSubCat, setSelectedSubCat] = useState("Cardiovascular Medicine");
  const [subjectInput, setSubjectInput] = useState("Cardiovascular Medicine");

  const [file, setFile] = useState(null);
  const [dragOver, setDragOver] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [scanStep, setScanStep] = useState(0);

  // Scan Results
  const [scanResult, setScanResult] = useState(null);
  const [issuesState, setIssuesState] = useState([]);
  const [activeTab, setActiveTab] = useState("all");
  const [editingIssueId, setEditingIssueId] = useState(null);
  const [customReplacement, setCustomReplacement] = useState("");

  // Corrections & Publishing
  const [applyingCorrections, setApplyingCorrections] = useState(false);
  const [correctedPreview, setCorrectedPreview] = useState(null);
  const [publishing, setPublishing] = useState(false);
  const [publishedData, setPublishedData] = useState(null);

  const fileInputRef = useRef(null);

  // Load categories tree
  useEffect(() => {
    categoriesApi
      .list()
      .then((res) => {
        const cats = res.data.categories || [];
        setCategoriesTree(cats);
        if (cats.length > 0) {
          const med = cats.find((c) => c.name.toLowerCase().includes("medicine")) || cats[0];
          setSelectedMainCat(med.name);
          const firstSub = med.subcategories?.[0]?.name || "";
          setSelectedSubCat(firstSub);
          setSubjectInput(firstSub);
        }
      })
      .catch(() => {});
  }, []);

  const availableSubcategories = useMemo(() => {
    const mainObj = categoriesTree.find((c) => c.name === selectedMainCat);
    return mainObj?.subcategories || [];
  }, [categoriesTree, selectedMainCat]);

  const handleMainCatChange = (e) => {
    const newMain = e.target.value;
    setSelectedMainCat(newMain);
    const mainObj = categoriesTree.find((c) => c.name === newMain);
    const firstSub = mainObj?.subcategories?.[0]?.name || "";
    setSelectedSubCat(firstSub);
    setSubjectInput(firstSub);
  };

  const handleSubCatChange = (e) => {
    const newSub = e.target.value;
    setSelectedSubCat(newSub);
    setSubjectInput(newSub);
  };

  const handleFileSelect = (f) => {
    if (!f) return;
    setFile(f);
    setScanResult(null);
    setCorrectedPreview(null);
    setPublishedData(null);
  };

  const loadDemo = async (demo) => {
    try {
      const resp = await fetch(demo.fileUrl);
      if (!resp.ok) throw new Error("Could not fetch demo file");
      const blob = await resp.blob();
      const demoFile = new File([blob], demo.fileName, { type: blob.type || "application/pdf" });
      setFile(demoFile);
      setSelectedMainCat(demo.mainCategory);
      setSelectedSubCat(demo.subcategory);
      setSubjectInput(demo.subject);
      setScanResult(null);
      setCorrectedPreview(null);
      setPublishedData(null);
      showToast(`Loaded ${demo.label}. Ready to scan!`, "success");
    } catch {
      showToast("Failed to load demo document.", "error");
    }
  };

  // Run Scan
  const handleStartScan = async () => {
    if (!file) {
      showToast("Please choose or drag a document to scan.", "error");
      return;
    }

    setScanning(true);
    setScanStep(1);

    const formData = new FormData();
    formData.append("file", file);
    formData.append("mainCategory", selectedMainCat);
    formData.append("subcategory", selectedSubCat);
    formData.append("subject", subjectInput);

    try {
      const stepTimer1 = setTimeout(() => setScanStep(2), 500);
      const stepTimer2 = setTimeout(() => setScanStep(3), 1000);
      const stepTimer3 = setTimeout(() => setScanStep(4), 1400);

      const res = await scanningBoothApi.scan(formData);

      clearTimeout(stepTimer1);
      clearTimeout(stepTimer2);
      clearTimeout(stepTimer3);

      const report = res.data.report || {};
      setScanResult(res.data);
      setIssuesState(
        (report.issues || []).map((iss) => ({
          ...iss,
          accepted: false,
          rejected: false,
          customText: iss.suggestion,
        }))
      );
      showToast("AI document scan completed successfully!", "success");
    } catch (err) {
      const msg = err.response?.data?.detail || "Document scan failed. Please check backend.";
      showToast(msg, "error");
    } finally {
      setScanning(false);
      setScanStep(0);
    }
  };

  // Toggle Accept / Reject
  const toggleAccept = (id) => {
    setIssuesState((prev) =>
      prev.map((iss) =>
        iss.id === id ? { ...iss, accepted: !iss.accepted, rejected: false } : iss
      )
    );
  };

  const toggleReject = (id) => {
    setIssuesState((prev) =>
      prev.map((iss) =>
        iss.id === id ? { ...iss, rejected: !iss.rejected, accepted: false } : iss
      )
    );
  };

  const acceptAll = () => {
    setIssuesState((prev) =>
      prev.map((iss) => ({ ...iss, accepted: true, rejected: false }))
    );
    showToast("Accepted all AI suggestions.", "success");
  };

  const saveCustomReplacement = (id) => {
    if (!customReplacement.trim()) return;
    setIssuesState((prev) =>
      prev.map((iss) =>
        iss.id === id
          ? {
              ...iss,
              suggestion: customReplacement.trim(),
              customText: customReplacement.trim(),
              accepted: true,
              rejected: false,
            }
          : iss
      )
    );
    setEditingIssueId(null);
    setCustomReplacement("");
  };

  // Apply accepted corrections
  const handleApplyCorrections = async () => {
    if (!scanResult?.scanId) return;

    const acceptedList = issuesState
      .filter((i) => i.accepted)
      .map((i) => ({
        id: i.id,
        category: i.category,
        original: i.original,
        suggestion: i.customText || i.suggestion,
        accepted: true,
      }));

    if (acceptedList.length === 0) {
      showToast("Please accept at least one correction before generating.", "error");
      return;
    }

    setApplyingCorrections(true);
    try {
      const res = await scanningBoothApi.applyCorrections(scanResult.scanId, {
        scanId: scanResult.scanId,
        acceptedIssues: acceptedList,
      });
      setCorrectedPreview(res.data.correctedPreview);
      showToast(`Applied ${acceptedList.length} corrections successfully!`, "success");
    } catch (err) {
      showToast("Failed to apply corrections.", "error");
    } finally {
      setApplyingCorrections(false);
    }
  };

  // Publish to CampusVerse
  const handleApproveAndPublish = async () => {
    if (!scanResult?.scanId) return;

    setPublishing(true);
    try {
      const res = await scanningBoothApi.approveAndPublish(scanResult.scanId, {
        scanId: scanResult.scanId,
        mainCategory: selectedMainCat,
        subcategory: selectedSubCat,
        subject: subjectInput,
        semester: 4,
        category: "notes",
        description: `Verified study material scanned with AI Booth for ${selectedSubCat} with academic consistency checks.`,
      });

      setPublishedData(res.data);
      if (res.data.isAutoApproved) {
        showToast("Material auto-approved and published live in study library!", "success");
      } else {
        showToast(res.data.message || "Material queued for staff review.", "info");
      }
    } catch (err) {
      const msg = err.response?.data?.detail || "Could not publish material.";
      showToast(msg, "error");
    } finally {
      setPublishing(false);
    }
  };

  const filteredIssues = useMemo(() => {
    if (activeTab === "all") return issuesState;
    if (activeTab === "spelling") return issuesState.filter((i) => i.category === "Spelling");
    if (activeTab === "grammar") return issuesState.filter((i) => i.category === "Grammar");
    if (activeTab === "academic")
      return issuesState.filter((i) => i.category === "Academic Review");
    if (activeTab === "formatting")
      return issuesState.filter((i) => i.category === "Formatting & Quality");
    return issuesState;
  }, [issuesState, activeTab]);

  const report = scanResult?.report || {};
  const isMedicalFaculty =
    selectedMainCat.toLowerCase().includes("medicine") ||
    report.isMedicalReviewRequired;

  return (
    <div className="mx-auto max-w-6xl px-4 py-10 sm:px-6">
      {/* Top Breadcrumb */}
      <nav className="mb-4 flex items-center gap-2 text-xs font-medium text-white/80">
        <Link to="/" className="hover:text-white transition">Home</Link>
        <ChevronRight size={13} className="text-white/40" />
        <Link to="/categories" className="hover:text-white transition">Categories</Link>
        <ChevronRight size={13} className="text-white/40" />
        <span className="text-white font-bold">AI Scanning Booth</span>
      </nav>

      {/* Hero Header */}
      <div className="flex flex-col md:flex-row md:items-end md:justify-between border-b border-white/10 pb-6 mb-8">
        <div>
          <span className="mb-2 inline-flex items-center gap-1.5 rounded-full bg-amber-500/20 border border-amber-400/30 px-3 py-1 text-xs font-semibold text-amber-300 backdrop-blur">
            <Sparkles size={14} /> AI-Powered Study Material Inspection
          </span>
          <h1 className="font-display text-3xl sm:text-4xl font-bold text-white tracking-tight">
            Study Material Scanning Booth
          </h1>
          <p className="mt-2 text-sm text-white/90 max-w-2xl leading-relaxed">
            Scan notes, lab manuals, and question banks. Detect factual contradictions, catch spelling errors while preserving technical terminology, evaluate category alignment, and auto-correct before publishing.
          </p>
        </div>

        <div className="mt-4 md:mt-0 flex items-center gap-3">
          <Link
            to="/categories"
            className="inline-flex items-center gap-1.5 rounded-xl border border-white/30 bg-white/10 px-4 py-2 text-xs font-semibold text-white backdrop-blur hover:bg-white/20 transition"
          >
            <BookOpen size={14} />
            <span>Browse Library</span>
          </Link>
          <Link
            to="/upload"
            className="inline-flex items-center gap-1.5 rounded-xl bg-white px-4 py-2 text-xs font-bold text-gray-900 shadow hover:bg-gray-100 transition"
          >
            <UploadCloud size={14} />
            <span>Direct Upload</span>
          </Link>
        </div>
      </div>

      {/* Main Grid: Upload & Controls */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left Column: Upload & Options */}
        <div className="lg:col-span-1 space-y-6">
          <div className="card p-6 bg-white rounded-2xl shadow-xl border border-gray-100">
            <h2 className="font-display text-base font-bold text-gray-900 mb-4 flex items-center gap-2">
              <Layers size={18} className="text-primary-600" />
              <span>Target Discipline Classification</span>
            </h2>

            {/* Academic Faculty */}
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-gray-600 mb-1.5">
                  Academic Faculty
                </label>
                <select
                  value={selectedMainCat}
                  onChange={handleMainCatChange}
                  className="input-field text-sm"
                >
                  {categoriesTree.map((cat) => (
                    <option key={cat.id || cat.name} value={cat.name}>
                      {cat.name}
                    </option>
                  ))}
                </select>
              </div>

              {/* Branch / Subcategory */}
              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-gray-600 mb-1.5">
                  Branch / Subcategory
                </label>
                <select
                  value={selectedSubCat}
                  onChange={handleSubCatChange}
                  className="input-field text-sm"
                >
                  {availableSubcategories.map((sub) => (
                    <option key={sub.name} value={sub.name}>
                      {sub.name}
                    </option>
                  ))}
                </select>
              </div>

              {/* Subject */}
              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-gray-600 mb-1.5">
                  Subject / Course
                </label>
                <input
                  type="text"
                  value={subjectInput}
                  onChange={(e) => setSubjectInput(e.target.value)}
                  placeholder="e.g. Cardiovascular Medicine"
                  className="input-field text-sm"
                />
              </div>
            </div>

            {/* Try Sample Materials */}
            <div className="mt-6 border-t border-gray-100 pt-4">
              <span className="block text-[11px] font-bold uppercase tracking-wider text-gray-500 mb-2">
                1-Click Sample Test Files:
              </span>
              <div className="space-y-1.5">
                {DEMO_SAMPLES.map((demo) => (
                  <button
                    key={demo.label}
                    type="button"
                    onClick={() => loadDemo(demo)}
                    className="w-full text-left rounded-lg border border-amber-200 bg-amber-50/70 px-3 py-2 text-xs font-medium text-amber-900 hover:bg-amber-100 transition flex items-center justify-between"
                  >
                    <span>{demo.label}</span>
                    <Sparkles size={12} className="text-amber-600" />
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Clinical Policy Notice for Medical Materials */}
          {isMedicalFaculty && (
            <div className="rounded-2xl border border-red-200 bg-red-50/90 p-4 text-xs text-red-900 shadow-sm backdrop-blur">
              <div className="flex items-center gap-2 font-bold text-red-800 mb-1">
                <Stethoscope size={16} />
                <span>Clinical Material Safety Protocol</span>
              </div>
              <p className="leading-relaxed">
                General Medicine materials require strict clinical verification. The AI Booth checks diagnostic guidelines, normal vital thresholds, and pharmacological protocols. Medical files are queued for senior clinical faculty sign-off prior to library release.
              </p>
            </div>
          )}
        </div>

        {/* Right Column: Dropzone & Scan Execution */}
        <div className="lg:col-span-2 space-y-6">
          <div className="card p-6 bg-white rounded-2xl shadow-xl border border-gray-100">
            {/* Dropzone */}
            <div
              onDragOver={(e) => {
                e.preventDefault();
                setDragOver(true);
              }}
              onDragLeave={() => setDragOver(false)}
              onDrop={(e) => {
                e.preventDefault();
                setDragOver(false);
                handleFileSelect(e.dataTransfer.files?.[0]);
              }}
              onClick={() => fileInputRef.current?.click()}
              className={`flex cursor-pointer flex-col items-center justify-center gap-3 rounded-2xl border-2 border-dashed p-10 text-center transition ${
                dragOver
                  ? "border-primary-500 bg-primary-50"
                  : "border-gray-200 hover:border-primary-400 hover:bg-gray-50"
              }`}
            >
              <input
                ref={fileInputRef}
                type="file"
                className="hidden"
                accept=".pdf,.docx,.doc,.txt,.pptx,.png,.jpg,.jpeg"
                onChange={(e) => handleFileSelect(e.target.files?.[0])}
              />

              {file ? (
                <div className="flex items-center gap-3 rounded-xl bg-primary-50 px-5 py-3 border border-primary-200 text-primary-900">
                  <FileText size={24} className="text-primary-600" />
                  <div className="text-left">
                    <p className="text-sm font-bold text-gray-900">{file.name}</p>
                    <p className="text-xs text-gray-500">
                      {(file.size / 1024).toFixed(1)} KB &bull; Ready for verification
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      setFile(null);
                      setScanResult(null);
                    }}
                    className="ml-3 rounded-full p-1 text-gray-400 hover:bg-white hover:text-red-600"
                  >
                    <X size={16} />
                  </button>
                </div>
              ) : (
                <>
                  <div className="rounded-2xl bg-primary-50 p-4 text-primary-600 shadow-sm">
                    <UploadCloud size={36} />
                  </div>
                  <div>
                    <p className="text-base font-semibold text-gray-900">
                      <span className="text-primary-600 underline">Upload document</span> or drag & drop here
                    </p>
                    <p className="text-xs text-gray-500 mt-1">
                      PDF, DOCX, TXT, PPTX, or scanned handwritten notes (PNG/JPG) &mdash; up to 25MB
                    </p>
                  </div>
                </>
              )}
            </div>

            {/* Scan Action Button */}
            <div className="mt-6 flex items-center justify-between">
              <span className="text-xs text-gray-500">
                AI inspects spelling, factual accuracy, formatting, and classification.
              </span>
              <button
                type="button"
                disabled={!file || scanning}
                onClick={handleStartScan}
                className="btn-primary !px-6 !py-2.5 flex items-center gap-2 shadow-lg disabled:opacity-50"
              >
                {scanning ? (
                  <>
                    <RefreshCw size={16} className="animate-spin" />
                    <span>Analyzing Document...</span>
                  </>
                ) : (
                  <>
                    <Sparkles size={16} />
                    <span>Run AI Verification Scan</span>
                  </>
                )}
              </button>
            </div>

            {/* Scanning Progress Steps */}
            {scanning && (
              <div className="mt-6 rounded-xl bg-gray-50 p-4 border border-gray-200">
                <div className="mb-2 flex items-center justify-between text-xs font-bold text-gray-700">
                  <span>AI Verification Progress</span>
                  <span>{scanStep * 25}%</span>
                </div>
                <div className="h-2 w-full overflow-hidden rounded-full bg-gray-200">
                  <div
                    className="h-full bg-primary-600 transition-all duration-300"
                    style={{ width: `${scanStep * 25}%` }}
                  />
                </div>
                <div className="mt-3 grid grid-cols-2 sm:grid-cols-4 gap-2 text-[11px] text-gray-600">
                  <span className={scanStep >= 1 ? "font-bold text-primary-700" : ""}>
                    1. Text Extraction
                  </span>
                  <span className={scanStep >= 2 ? "font-bold text-primary-700" : ""}>
                    2. Grammar & Typo Check
                  </span>
                  <span className={scanStep >= 3 ? "font-bold text-primary-700" : ""}>
                    3. Academic Fact Check
                  </span>
                  <span className={scanStep >= 4 ? "font-bold text-primary-700" : ""}>
                    4. Category Matching
                  </span>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* SCAN RESULTS DASHBOARD */}
      {scanResult && (
        <div className="mt-10 space-y-8 animate-fade-in">
          {/* Executive Overview Card */}
          <div className="rounded-3xl bg-white p-6 sm:p-8 shadow-xl border border-gray-100">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 pb-6 border-b border-gray-100">
              <div className="flex items-center gap-5">
                {/* Score Gauge */}
                <div className="relative flex h-24 w-24 flex-shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br from-gray-900 to-gray-800 text-white shadow-lg">
                  <div className="text-center">
                    <span className="font-display text-3xl font-bold">
                      {report.qualityScore ?? 88}
                    </span>
                    <span className="block text-[10px] uppercase tracking-wider text-gray-300">
                      Score / 100
                    </span>
                  </div>
                </div>

                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold uppercase tracking-wider text-primary-600">
                      AI Audit Report
                    </span>
                    <span className="rounded-full bg-gray-100 px-2 py-0.5 text-[11px] font-medium text-gray-700">
                      {scanResult.fileName}
                    </span>
                  </div>
                  <h3 className="font-display text-2xl font-bold text-gray-900 mt-1">
                    {report.statusLabel || "Comprehensive Verification Completed"}
                  </h3>
                  <p className="text-xs text-gray-500 mt-1">
                    OCR Quality: {report.ocrQuality || "Digital Text"} &bull; Total Words:{" "}
                    {report.totalWords || 450}
                  </p>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex flex-wrap items-center gap-2.5">
                <button
                  onClick={acceptAll}
                  className="rounded-xl bg-emerald-50 border border-emerald-300 px-4 py-2 text-xs font-bold text-emerald-800 hover:bg-emerald-100 transition flex items-center gap-1.5"
                >
                  <Check size={14} /> Accept All Corrections
                </button>
                <button
                  onClick={handleApplyCorrections}
                  disabled={applyingCorrections}
                  className="rounded-xl bg-gray-900 px-4 py-2 text-xs font-bold text-white hover:bg-primary-600 transition flex items-center gap-1.5 shadow"
                >
                  {applyingCorrections ? (
                    <RefreshCw size={14} className="animate-spin" />
                  ) : (
                    <Edit3 size={14} />
                  )}
                  <span>Generate Corrected Version</span>
                </button>
              </div>
            </div>

            {/* Category Match Alert / Warning */}
            <div className="mt-6">
              {report.categoryMatch ? (
                <div className="rounded-xl bg-emerald-50 border border-emerald-200 p-3.5 flex items-center justify-between text-xs text-emerald-900">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 size={16} className="text-emerald-600" />
                    <span>
                      <b>Category Match Verified:</b> Document content correctly aligns with{" "}
                      <b>{report.predictedCategory?.mainCategory} &gt; {report.predictedCategory?.subcategory}</b> ({Math.round((report.predictedCategory?.confidence || 0.9) * 100)}% confidence).
                    </span>
                  </div>
                </div>
              ) : (
                <div className="rounded-xl bg-amber-50 border border-amber-300 p-3.5 flex items-center justify-between text-xs text-amber-900">
                  <div className="flex items-center gap-2">
                    <AlertTriangle size={16} className="text-amber-600" />
                    <span>{report.mismatchWarning || "Classification mismatch identified."}</span>
                  </div>
                </div>
              )}
            </div>

            {/* Metric Counters */}
            <div className="mt-6 grid grid-cols-2 sm:grid-cols-4 gap-4">
              <div className="rounded-2xl bg-gray-50 p-4 border border-gray-100">
                <span className="block text-xs font-medium text-gray-500">Spelling & Typos</span>
                <span className="font-display text-2xl font-bold text-gray-900 mt-1 block">
                  {report.counts?.spelling ?? 0}
                </span>
                <span className="text-[11px] text-gray-400">Technical terms preserved</span>
              </div>

              <div className="rounded-2xl bg-gray-50 p-4 border border-gray-100">
                <span className="block text-xs font-medium text-gray-500">Grammar & Style</span>
                <span className="font-display text-2xl font-bold text-gray-900 mt-1 block">
                  {report.counts?.grammar ?? 0}
                </span>
                <span className="text-[11px] text-gray-400">Readability optimized</span>
              </div>

              <div className="rounded-2xl bg-gray-50 p-4 border border-gray-100">
                <span className="block text-xs font-medium text-gray-500">Academic Review</span>
                <span className="font-display text-2xl font-bold text-amber-700 mt-1 block">
                  {report.counts?.academic ?? 0}
                </span>
                <span className="text-[11px] text-gray-400">Factual consistency check</span>
              </div>

              <div className="rounded-2xl bg-gray-50 p-4 border border-gray-100">
                <span className="block text-xs font-medium text-gray-500">Formatting Issues</span>
                <span className="font-display text-2xl font-bold text-gray-900 mt-1 block">
                  {report.counts?.formatting ?? 0}
                </span>
                <span className="text-[11px] text-gray-400">Paragraphs & structure</span>
              </div>
            </div>
          </div>

          {/* Interactive Issues List & Filter Tabs */}
          <div className="rounded-3xl bg-white p-6 sm:p-8 shadow-xl border border-gray-100">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-5 border-b border-gray-100">
              <div className="flex items-center gap-2">
                <Filter size={16} className="text-gray-500" />
                <h4 className="font-display text-lg font-bold text-gray-900">
                  Detected Observations & Corrections ({issuesState.length})
                </h4>
              </div>

              {/* Tabs */}
              <div className="flex flex-wrap gap-1 rounded-xl bg-gray-100 p-1">
                {[
                  { id: "all", label: "All" },
                  { id: "spelling", label: "Spelling" },
                  { id: "grammar", label: "Grammar" },
                  { id: "academic", label: "Academic" },
                  { id: "formatting", label: "Formatting" },
                ].map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`rounded-lg px-3 py-1 text-xs font-bold transition ${
                      activeTab === tab.id
                        ? "bg-white text-gray-900 shadow-sm"
                        : "text-gray-600 hover:text-gray-900"
                    }`}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Issue Cards */}
            <div className="mt-6 space-y-4">
              {filteredIssues.length === 0 ? (
                <div className="p-8 text-center bg-gray-50 rounded-2xl">
                  <CheckCircle2 size={32} className="mx-auto text-emerald-500" />
                  <p className="mt-2 text-sm font-semibold text-gray-800">
                    No issues identified under this filter.
                  </p>
                </div>
              ) : (
                filteredIssues.map((iss) => {
                  const isAccepted = iss.accepted;
                  const isRejected = iss.rejected;

                  return (
                    <div
                      key={iss.id}
                      className={`p-5 rounded-2xl border transition ${
                        isAccepted
                          ? "bg-emerald-50/50 border-emerald-300"
                          : isRejected
                          ? "bg-gray-50/80 border-gray-200 opacity-60"
                          : "bg-white border-gray-200 hover:border-gray-300 shadow-sm"
                      }`}
                    >
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-3">
                        <div className="flex items-center gap-2">
                          <span
                            className={`rounded-full px-2.5 py-0.5 text-[11px] font-bold ${
                              iss.category === "Academic Review"
                                ? "bg-amber-100 text-amber-900 border border-amber-300"
                                : iss.category === "Spelling"
                                ? "bg-blue-100 text-blue-900"
                                : iss.category === "Grammar"
                                ? "bg-purple-100 text-purple-900"
                                : "bg-gray-100 text-gray-800"
                            }`}
                          >
                            {iss.category}
                          </span>
                          <span className="text-xs text-gray-400">Page {iss.page || 1}</span>
                          <span className="text-xs text-gray-400">&bull;</span>
                          <span className="text-xs text-gray-500 font-mono">
                            Confidence: {Math.round((iss.confidence || 0.9) * 100)}%
                          </span>
                        </div>

                        {/* Accept / Reject Buttons */}
                        <div className="flex items-center gap-2">
                          <button
                            type="button"
                            onClick={() => toggleAccept(iss.id)}
                            className={`rounded-lg px-2.5 py-1 text-xs font-bold transition flex items-center gap-1 ${
                              isAccepted
                                ? "bg-emerald-600 text-white"
                                : "bg-emerald-50 text-emerald-700 hover:bg-emerald-100 border border-emerald-300"
                            }`}
                          >
                            <Check size={12} />
                            <span>{isAccepted ? "Accepted" : "Accept"}</span>
                          </button>

                          <button
                            type="button"
                            onClick={() => toggleReject(iss.id)}
                            className={`rounded-lg px-2.5 py-1 text-xs font-bold transition flex items-center gap-1 ${
                              isRejected
                                ? "bg-gray-700 text-white"
                                : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                            }`}
                          >
                            <X size={12} />
                            <span>{isRejected ? "Rejected" : "Reject"}</span>
                          </button>

                          <button
                            type="button"
                            onClick={() => {
                              setEditingIssueId(iss.id);
                              setCustomReplacement(iss.customText || iss.suggestion);
                            }}
                            className="rounded-lg p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-700"
                            title="Edit correction text"
                          >
                            <Edit3 size={14} />
                          </button>
                        </div>
                      </div>

                      {/* Content Comparison */}
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs mt-3 bg-gray-50/70 p-3.5 rounded-xl border border-gray-100">
                        <div>
                          <span className="text-[10px] font-bold uppercase tracking-wider text-red-500 block mb-1">
                            Original Text:
                          </span>
                          <div className="p-2 rounded bg-white border border-red-200 text-gray-800 line-through">
                            {iss.original}
                          </div>
                        </div>

                        <div>
                          <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-600 block mb-1">
                            Suggested Replacement:
                          </span>
                          <div className="p-2 rounded bg-white border border-emerald-300 text-emerald-950 font-medium">
                            {iss.customText || iss.suggestion}
                          </div>
                        </div>
                      </div>

                      {/* Editing modal / inline form */}
                      {editingIssueId === iss.id && (
                        <div className="mt-3 flex items-center gap-2">
                          <input
                            type="text"
                            value={customReplacement}
                            onChange={(e) => setCustomReplacement(e.target.value)}
                            className="input-field text-xs py-1.5"
                            placeholder="Enter custom correction..."
                          />
                          <button
                            type="button"
                            onClick={() => saveCustomReplacement(iss.id)}
                            className="rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-bold text-white hover:bg-emerald-700"
                          >
                            Save
                          </button>
                          <button
                            type="button"
                            onClick={() => setEditingIssueId(null)}
                            className="rounded-lg bg-gray-200 px-3 py-1.5 text-xs text-gray-700 hover:bg-gray-300"
                          >
                            Cancel
                          </button>
                        </div>
                      )}

                      {/* Academic Reason */}
                      <p className="mt-3 text-xs text-gray-600 leading-relaxed">
                        <span className="font-semibold text-gray-800">Reason:</span> {iss.reason}
                      </p>
                    </div>
                  );
                })
              )}
            </div>
          </div>

          {/* Corrected Preview & Download Suite */}
          <div className="rounded-3xl bg-white p-6 sm:p-8 shadow-xl border border-gray-100">
            <h4 className="font-display text-lg font-bold text-gray-900 mb-2">
              Preview Corrected Study Document
            </h4>
            <p className="text-xs text-gray-500 mb-4">
              Accepted corrections are integrated into a clean verified version without altering the original file.
            </p>

            {correctedPreview ? (
              <div className="rounded-2xl border border-gray-200 bg-gray-50 p-5 font-mono text-xs text-gray-800 max-h-72 overflow-y-auto whitespace-pre-wrap leading-relaxed">
                {correctedPreview}
              </div>
            ) : (
              <div className="rounded-2xl border border-dashed border-gray-300 bg-gray-50/50 p-6 text-center text-xs text-gray-500">
                Click &ldquo;Generate Corrected Version&rdquo; above to synthesize the modified text with all your accepted suggestions.
              </div>
            )}

            {/* Downloads & Publishing Suite */}
            <div className="mt-6 flex flex-wrap items-center justify-between gap-4 border-t border-gray-100 pt-6">
              <div className="flex flex-wrap items-center gap-3">
                <a
                  href={scanningBoothApi.getDownloadOriginalUrl(scanResult.scanId)}
                  target="_blank"
                  rel="noreferrer"
                  className="rounded-xl border border-gray-300 bg-white px-4 py-2 text-xs font-bold text-gray-700 hover:bg-gray-50 transition flex items-center gap-2 shadow-sm"
                >
                  <Download size={14} /> Download Original Document
                </a>

                <a
                  href={scanningBoothApi.getDownloadCorrectedUrl(scanResult.scanId)}
                  target="_blank"
                  rel="noreferrer"
                  className="rounded-xl border border-emerald-400 bg-emerald-50 px-4 py-2 text-xs font-bold text-emerald-900 hover:bg-emerald-100 transition flex items-center gap-2 shadow-sm"
                >
                  <Download size={14} /> Download Corrected (.txt)
                </a>
              </div>

              {/* Publish to CampusVerse button */}
              <button
                type="button"
                onClick={handleApproveAndPublish}
                disabled={publishing}
                className="btn-primary !px-6 !py-2.5 flex items-center gap-2 shadow-lg disabled:opacity-50"
              >
                {publishing ? (
                  <RefreshCw size={14} className="animate-spin" />
                ) : (
                  <Send size={14} />
                )}
                <span>Publish to CampusVerse Library</span>
              </button>
            </div>

            {/* Published Result Alert */}
            {publishedData && (
              <div
                className={`mt-6 rounded-2xl p-4 text-xs font-medium border flex items-center justify-between ${
                  publishedData.isAutoApproved
                    ? "bg-emerald-50 border-emerald-300 text-emerald-950"
                    : "bg-amber-50 border-amber-300 text-amber-950"
                }`}
              >
                <div className="flex items-center gap-2">
                  {publishedData.isAutoApproved ? (
                    <CheckCircle2 size={18} className="text-emerald-600" />
                  ) : (
                    <ShieldCheck size={18} className="text-amber-600" />
                  )}
                  <span>{publishedData.message}</span>
                </div>

                <Link
                  to={`/materials/${publishedData.materialId}`}
                  className="inline-flex items-center gap-1 rounded-lg bg-white px-3 py-1 font-bold text-gray-900 shadow hover:bg-gray-100 transition"
                >
                  <span>View Material</span>
                  <ArrowRight size={12} />
                </Link>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
