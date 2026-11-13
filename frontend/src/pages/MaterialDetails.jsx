import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import {
  Download,
  Bookmark,
  FileText,
  User,
  Calendar,
  Eye,
  Sparkles,
  CheckCircle2,
  Clock,
  AlertCircle,
  RefreshCw,
  Bot,
  Edit3,
  Star,
} from "lucide-react";
import Loader from "../components/Loader";
import { ErrorState } from "../components/EmptyState";
import { StarDisplay, StarInput } from "../components/StarRating";
import MaterialCard from "../components/MaterialCard";
import MaterialPreviewModal from "../components/MaterialPreviewModal";
import ClassificationCorrectionModal from "../components/ClassificationCorrectionModal";
import ChapterSummarySection from "../components/ChapterSummarySection";
import { materialsApi, reviewsApi, bookmarksApi } from "../services/endpoints";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import api from "../services/api";

export default function MaterialDetails() {
  const { id } = useParams();
  const { user } = useAuth();
  const { showToast } = useToast();

  const [material, setMaterial] = useState(null);
  const [related, setRelated] = useState([]);
  const [status, setStatus] = useState("loading");

  const [myRating, setMyRating] = useState(0);
  const [submitting, setSubmitting] = useState(false);
  const [showPreview, setShowPreview] = useState(false);
  const [showCorrectionModal, setShowCorrectionModal] = useState(false);

  const load = () => {
    if (!id || id === "undefined" || id === "null") {
      setStatus("notFound");
      return;
    }
    setStatus("loading");
    Promise.all([
      materialsApi.detail(id),
      reviewsApi.getRating(id),
      materialsApi.recommended(),
      user ? reviewsApi.getMyRating(id).catch(() => ({ data: { userRating: 0 } })) : Promise.resolve({ data: { userRating: 0 } })
    ])
      .then(([detailRes, ratingRes, relatedRes, myRatingRes]) => {
        const mat = detailRes.data.material;
        if (ratingRes?.data) {
          mat.rating = ratingRes.data.averageRating ?? mat.rating ?? 5.0;
          mat.ratingCount = ratingRes.data.ratingCount ?? mat.ratingCount ?? 0;
        }
        setMaterial(mat);
        if (myRatingRes?.data?.userRating) {
          setMyRating(myRatingRes.data.userRating);
        }
        setRelated(relatedRes.data.materials?.slice(0, 4) || []);
        setStatus("idle");
      })
      .catch((err) => {
        if (err?.response?.status === 404) {
          setStatus("notFound");
        } else {
          setStatus("error");
        }
      });
  };

  useEffect(load, [id, user]);

  const handleRate = async (starValue) => {
    if (!user) return showToast("Log in to rate this study material.", "error");
    if (!id || id === "undefined") return;
    setMyRating(starValue);
    setSubmitting(true);
    try {
      const res = await reviewsApi.submitRating(id, starValue);
      setMaterial((prev) => ({
        ...prev,
        rating: res.data.averageRating ?? starValue,
        ratingCount: res.data.ratingCount ?? ((prev?.ratingCount || 0) + 1),
      }));
      showToast(`Rating recorded: ${starValue} / 5 stars`, "success");
    } catch {
      showToast("Could not submit your rating. Try again.", "error");
    } finally {
      setSubmitting(false);
    }
  };

  const handleDownload = () => {
    const validId = material?.id || material?._id || id;
    if (!validId || validId === "undefined") {
      showToast("Download unavailable for this material.", "error");
      return;
    }
    try {
      const token = localStorage.getItem("cv-token");
      const downloadUrl = `${api.defaults.baseURL}/materials/${validId}/download${token ? `?token=${encodeURIComponent(token)}` : ""}`;
      const link = document.createElement("a");
      link.href = downloadUrl;
      link.setAttribute("download", material?.originalName || `${material?.title || "study-material"}.${(material?.fileType || "pdf").toLowerCase()}`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      showToast("Download started", "success");
    } catch {
      showToast("Could not start the download. Try again.", "error");
    }
  };

  const handleBookmark = async () => {
    if (!user) return showToast("Log in to bookmark materials.", "error");
    const validId = material?.id || material?._id || id;
    try {
      await bookmarksApi.toggle(validId);
      setMaterial((m) => ({ ...m, bookmarked: !m.bookmarked }));
    } catch {
      showToast("Something went wrong.", "error");
    }
  };

  const isOwner = user && (String(material?.uploader) === String(user.id) || user.role === "admin" || user.role === "moderator");
  const activeMatId = material?.id || material?._id || id;

  if (!id || id === "undefined" || id === "null" || status === "notFound") {
    return (
      <div className="mx-auto max-w-3xl px-4 py-16 text-center">
        <div className="card p-8 bg-white/95 rounded-2xl shadow-md border border-white/40">
          <FileText size={48} className="mx-auto text-brand-400 mb-3" />
          <h2 className="text-xl font-bold text-gray-800">Study Material Not Found</h2>
          <p className="text-sm text-gray-500 mt-1 mb-5">
            The study material you are looking for is unavailable or the link is invalid.
          </p>
          <div className="flex items-center justify-center gap-3">
            <Link to="/categories" className="btn-primary !px-5 !py-2 text-xs font-bold shadow-sm inline-flex items-center gap-1.5">
              Browse Study Materials
            </Link>
            <Link to="/dashboard" className="btn-secondary !px-5 !py-2 text-xs font-bold shadow-sm inline-flex items-center gap-1.5">
              Back to Dashboard
            </Link>
          </div>
        </div>
      </div>
    );
  }

  if (status === "loading") return <div className="py-20"><Loader label="Loading material..." /></div>;
  if (status === "error") return <div className="mx-auto max-w-3xl px-4 py-16"><ErrorState onRetry={load} /></div>;

  return (
    <div className="mx-auto max-w-5xl px-4 py-10 sm:px-6">
      <div className="grid grid-cols-1 gap-8 md:grid-cols-3">
        {/* Preview */}
        <div className="md:col-span-2">
          <div className="card flex aspect-[4/3] items-center justify-center bg-white rounded-2xl shadow-md border border-white/40">
            {material.thumbnail ? (
              <img src={material.thumbnail} alt="" className="h-full w-full rounded-2xl object-cover" />
            ) : (
              <FileText size={64} className="text-brand-400" />
            )}
          </div>

          <div className="mt-5 flex flex-wrap items-center justify-between gap-3">
            <div>
              <h1 className="text-2xl font-bold text-white">{material.title}</h1>
              <p className="mt-1 text-sm text-white/90">
                Academic Category: <span className="font-semibold text-white">{material.academicCategory || material.mainCategory || "Engineering"}</span>
                {" • "}
                <span className="text-white/80">
                  {material.fileType || "PDF"} • {material.pageCount || 1} {material.fileType?.toUpperCase().includes("PPT") ? (material.pageCount === 1 ? "slide" : "slides") : (material.pageCount === 1 ? "page" : "pages")}
                </span>
              </p>
            </div>

            {/* Processing status badge */}
            <div>
              {material.processingStatus === "Summary ready" || !material.processingStatus ? (
                <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-100 text-emerald-800 px-3 py-1 text-xs font-extrabold shadow-sm">
                  <CheckCircle2 size={13} className="text-emerald-600" /> Summary ready
                </span>
              ) : material.processingStatus === "Generating summary" ? (
                <span className="inline-flex items-center gap-1.5 rounded-full bg-amber-100 text-amber-800 px-3 py-1 text-xs font-bold shadow-sm">
                  <RefreshCw size={13} className="animate-spin text-amber-600" /> Generating summary
                </span>
              ) : material.processingStatus === "Processing document" ? (
                <span className="inline-flex items-center gap-1.5 rounded-full bg-blue-100 text-blue-800 px-3 py-1 text-xs font-bold shadow-sm">
                  <RefreshCw size={13} className="animate-spin text-blue-600" /> Processing document
                </span>
              ) : material.processingStatus === "Processing failed" ? (
                <span className="inline-flex items-center gap-1.5 rounded-full bg-red-100 text-red-800 px-3 py-1 text-xs font-bold shadow-sm">
                  <AlertCircle size={13} className="text-red-600" /> Processing failed
                </span>
              ) : (
                <span className="inline-flex items-center gap-1.5 rounded-full bg-gray-100 text-gray-700 px-3 py-1 text-xs font-bold shadow-sm">
                  <Clock size={13} /> {material.processingStatus}
                </span>
              )}
            </div>
          </div>

          <div className="mt-3 flex items-center gap-4">
            <StarDisplay rating={material.rating || 0} count={material.ratingCount} size={16} />
            <span className="flex items-center gap-1 text-sm text-white/80">
              <Download size={14} /> {material.downloads || 0} downloads
            </span>
          </div>

          {/* FEATURE 1: Academic Branch & Subject Classification Card */}
          <div className="card mt-4 p-4 bg-white/95 rounded-2xl shadow-md border border-white/40 space-y-2.5">
            <div className="flex items-center justify-between flex-wrap gap-2 pb-2 border-b border-gray-100">
              <div className="flex items-center gap-2">
                <Sparkles size={16} className="text-brand-600" />
                <h3 className="text-xs font-bold uppercase tracking-wider text-brand-900">
                  Academic Classification
                </h3>
              </div>
              <div className="flex items-center gap-2">
                {material.classification?.confidence ? (
                  <span className="text-xs font-bold px-2.5 py-0.5 rounded-full bg-emerald-50 text-emerald-800 border border-emerald-200">
                    {Math.round(material.classification.confidence * 100)}% Confidence
                  </span>
                ) : (
                  <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-gray-100 text-gray-700">
                    Auto-classified
                  </span>
                )}
                {isOwner && (
                  <button
                    onClick={() => setShowCorrectionModal(true)}
                    className="text-xs text-brand-700 hover:text-brand-900 font-bold flex items-center gap-1 px-2.5 py-0.5 rounded-lg border border-brand-200 hover:bg-brand-50 transition"
                  >
                    <Edit3 size={12} />
                    <span>Correct</span>
                  </button>
                )}
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
              <div className="bg-gray-50/70 p-2.5 rounded-xl border border-gray-100">
                <span className="text-gray-400 block text-[10px] uppercase font-bold tracking-wider">Branch / Department</span>
                <strong className="text-gray-900 text-sm">
                  {material.classification?.branch || material.department || "Unable to classify"}
                </strong>
              </div>
              <div className="bg-gray-50/70 p-2.5 rounded-xl border border-gray-100">
                <span className="text-gray-400 block text-[10px] uppercase font-bold tracking-wider">Subject</span>
                <strong className="text-gray-900 text-sm">
                  {material.classification?.subject || material.subject || "Unable to classify"}
                </strong>
              </div>
            </div>

            {material.classification?.topics?.length > 0 && (
              <div className="pt-1">
                <span className="text-gray-500 block text-[11px] font-semibold mb-1">Identified Topics:</span>
                <div className="flex flex-wrap gap-1.5">
                  {material.classification.topics.map((t, idx) => (
                    <span
                      key={idx}
                      className="px-2.5 py-0.5 rounded-full bg-brand-50 border border-brand-200 text-brand-900 font-medium text-[11px]"
                    >
                      {t}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* AI-Generated Summary Container */}
          <div className="card mt-4 p-5 bg-white/95 rounded-2xl shadow-md border border-white/40">
            <div className="flex items-center justify-between pb-2 mb-2 border-b border-gray-100">
              <h3 className="text-xs font-bold uppercase tracking-wider text-brand-900 flex items-center gap-1.5">
                <Sparkles size={14} className="text-brand-600" />
                <span>AI-Generated Summary</span>
              </h3>
              <span className="text-xs font-extrabold text-emerald-800 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                {material.summaryWordCount || (material.summary || material.description || "").trim().split(/\s+/).filter(Boolean).length} / {material.maxSummaryWords || 500} words
              </span>
            </div>
            <p className="text-sm leading-relaxed text-gray-800 bg-brand-50/30 p-3.5 rounded-xl border border-brand-100/60 font-normal">
              {material.summary || material.description || "No summary available for this material."}
            </p>
          </div>

          {/* FEATURE 3: Chapter-Wise Summaries & Key Concepts Section */}
          <ChapterSummarySection
            materialId={id}
            materialTitle={material.title}
            subject={material.subject || material.classification?.subject}
            isOwnerOrAdmin={isOwner}
          />

          <div className="mt-6 flex items-center gap-3 border-t border-white/20 pt-5 text-sm text-white/80">
            <span className="flex items-center gap-1"><User size={14} /> {material.uploaderName || "Anonymous"}</span>
            <span className="flex items-center gap-1"><Calendar size={14} /> {material.uploadedAt ? new Date(material.uploadedAt).toLocaleDateString() : "—"}</span>
          </div>

          {/* Student Ratings & Evaluation Card (NO REVIEWS - RATINGS ONLY) */}
          <div className="mt-10 rounded-2xl bg-white/95 p-6 shadow-md border border-white/40">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-4 border-b border-gray-100">
              <div>
                <h2 className="text-base font-bold text-gray-900 flex items-center gap-2">
                  <Star className="text-amber-500 fill-amber-500" size={18} />
                  <span>Student Ratings & Quality Score</span>
                </h2>
                <p className="text-xs text-gray-500 mt-0.5">
                  Peer-evaluated academic rating based on accuracy, completeness, and clarity.
                </p>
              </div>
              <div className="flex items-center gap-3">
                <div className="text-right">
                  <div className="text-2xl font-black text-brand-900">
                    {Number(material.rating || 5.0).toFixed(1)}
                    <span className="text-xs font-semibold text-gray-400"> / 5.0</span>
                  </div>
                  <div className="text-[11px] text-gray-500 font-medium">
                    {material.ratingCount || 0} student {material.ratingCount === 1 ? "rating" : "ratings"}
                  </div>
                </div>
                <StarDisplay rating={material.rating || 5.0} size={18} />
              </div>
            </div>

            {/* Interactive Rating Widget for Authenticated Student */}
            <div className="mt-4 pt-2 flex flex-col sm:flex-row items-center justify-between gap-4 bg-brand-50/50 p-4 rounded-xl border border-brand-100">
              <div>
                <span className="text-xs font-bold text-gray-800 block">
                  {myRating > 0 ? "Your active rating:" : "Rate this study material:"}
                </span>
                <span className="text-[11px] text-gray-500">
                  {myRating > 0
                    ? `You gave this material ${myRating} star${myRating > 1 ? "s" : ""}. Click any star to update.`
                    : "Help fellow students by rating the accuracy and clarity of these notes."}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <StarInput
                  value={myRating}
                  onChange={(val) => handleRate(val)}
                  size={24}
                  disabled={submitting}
                />
                {submitting && <span className="text-xs text-gray-400 animate-pulse">Saving...</span>}
              </div>
            </div>
          </div>
        </div>

        {/* Sidebar actions */}
        <div>
          <div className="card sticky top-20 space-y-3 p-5 bg-white/95 rounded-2xl shadow-md border border-white/40">
            <Link
              to={`/chat?materialId=${activeMatId}`}
              className="btn-primary w-full !bg-[#93785b] hover:!bg-[#82674c] !text-white shadow-md flex items-center justify-center gap-2"
            >
              <Bot size={16} /> Chat With Notes
            </Link>
            <button
              onClick={() => setShowPreview(true)}
              className="btn-primary w-full !bg-brand-600 hover:!bg-brand-700 !text-white shadow-md flex items-center justify-center gap-2"
            >
              <Eye size={16} /> Preview Material
            </button>
            <button onClick={handleDownload} className="btn-secondary w-full !bg-[#3e362e] hover:!bg-[#28221c] !text-white shadow-md flex items-center justify-center gap-2">
              <Download size={16} /> Download
            </button>
            <button onClick={handleBookmark} className="btn-secondary w-full !bg-white !text-[#3e362e] !border-brand-200">
              <Bookmark size={16} className={material.bookmarked ? "fill-brand-600 text-brand-600" : ""} />
              {material.bookmarked ? "Bookmarked" : "Bookmark"}
            </button>
          </div>

          {related.length > 0 && (
            <div className="mt-6">
              <h3 className="mb-3 text-sm font-bold text-white">You might also like</h3>
              <div className="space-y-4">
                {related.map((m) => {
                  const relId = m.id || m._id;
                  return (
                    <Link key={relId} to={`/materials/${relId}`} className="card flex gap-3 p-3 bg-white/95 rounded-xl shadow-md hover:shadow-lg border border-white/40 transition">
                      <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-lg bg-brand-50 border border-brand-200">
                        <FileText size={20} className="text-brand-400" />
                      </div>
                      <div className="min-w-0">
                        <p className="truncate text-sm font-semibold text-gray-900">{m.title}</p>
                        <p className="text-xs text-gray-500">{m.subject}</p>
                      </div>
                    </Link>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      </div>

      <MaterialPreviewModal
        materialId={activeMatId}
        open={showPreview}
        onClose={() => setShowPreview(false)}
      />

      {showCorrectionModal && (
        <ClassificationCorrectionModal
          isOpen={showCorrectionModal}
          onClose={() => setShowCorrectionModal(false)}
          materialId={activeMatId}
          currentBranch={material.classification?.branch || material.department}
          currentSubject={material.classification?.subject || material.subject}
          currentTopic={material.classification?.topics?.[0] || material.topic}
          onSuccess={(updated) => {
            setMaterial((prev) => ({
              ...prev,
              department: updated.branch,
              subject: updated.subject,
              academicCategory: updated.branch,
              classification: updated,
            }));
          }}
        />
      )}
    </div>
  );
}
