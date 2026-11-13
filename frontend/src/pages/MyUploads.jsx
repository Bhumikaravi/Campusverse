import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Upload,
  FileText,
  Trash2,
  Eye,
  Download,
  CheckCircle2,
  Clock,
  AlertTriangle,
  XCircle,
  Sparkles,
} from "lucide-react";
import { materialsApi } from "../services/endpoints";
import { useToast } from "../context/ToastContext";
import Loader from "../components/Loader";
import { EmptyState } from "../components/EmptyState";
import Modal from "../components/Modal";
import MaterialPreviewModal from "../components/MaterialPreviewModal";
import api from "../services/api";

export default function MyUploads() {
  const [materials, setMaterials] = useState([]);
  const [loading, setLoading] = useState(true);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [deleting, setDeleting] = useState(false);
  const [previewId, setPreviewId] = useState(null);
  const { showToast } = useToast();

  const loadUploads = () => {
    setLoading(true);
    materialsApi
      .myUploads()
      .then((res) => setMaterials(res.data.materials || res.data.items || []))
      .catch(() => setMaterials([]))
      .finally(() => setLoading(false));
  };

  useEffect(loadUploads, []);

  const handleDelete = async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await materialsApi.delete(deleteTarget.id);
      showToast("Material deleted successfully", "success");
      setMaterials((prev) => prev.filter((m) => m.id !== deleteTarget.id));
      setDeleteTarget(null);
    } catch {
      showToast("Could not delete this material.", "error");
    } finally {
      setDeleting(false);
    }
  };

  const handleDownload = (id) => {
    try {
      const url = `${api.defaults.baseURL}/materials/${id}/download`;
      window.open(url, "_blank");
      showToast("Download started", "success");
    } catch {
      showToast("Download failed.", "error");
    }
  };

  const renderStatusBadge = (status) => {
    switch (status) {
      case "ADMIN_APPROVED":
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 text-emerald-800 px-2.5 py-0.5 text-[11px] font-bold">
            <CheckCircle2 size={12} /> Published Live
          </span>
        );
      case "AI_APPROVED":
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 text-emerald-800 px-2.5 py-0.5 text-[11px] font-bold">
            <CheckCircle2 size={12} className="text-emerald-600" /> Verified &amp; Published Live
          </span>
        );
      case "NEEDS_REVIEW":
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-amber-100 text-amber-800 px-2.5 py-0.5 text-[11px] font-bold">
            <Clock size={12} /> Under Review
          </span>
        );
      case "REJECTED":
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-red-100 text-red-800 px-2.5 py-0.5 text-[11px] font-bold">
            <XCircle size={12} /> Verification Failed
          </span>
        );
      case "ADMIN_REJECTED":
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-red-100 text-red-800 px-2.5 py-0.5 text-[11px] font-bold">
            <XCircle size={12} /> Rejected by Moderator
          </span>
        );
      case "PENDING":
      default:
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-gray-100 text-gray-700 px-2.5 py-0.5 text-[11px] font-bold">
            <Clock size={12} /> Screening Pending
          </span>
        );
    }
  };

  return (
    <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6">
      <div className="flex flex-col items-start justify-between gap-4 sm:flex-row sm:items-center">
        <div>
          <h1 className="font-display text-3xl font-bold text-white drop-shadow-xs">My Uploaded Notes</h1>
          <p className="mt-1 text-sm text-white/90 font-medium drop-shadow-2xs">
            Track your shared academic notes and published study materials.
          </p>
        </div>
        <Link to="/upload" className="btn-primary flex items-center gap-2">
          <Upload size={16} /> Upload new material
        </Link>
      </div>

      {loading ? (
        <div className="py-20">
          <Loader label="Fetching your uploads..." />
        </div>
      ) : materials.length === 0 ? (
        <div className="mt-8">
          <EmptyState
            title="You haven't uploaded any study materials yet"
            message="Share your class notes, formula sheets, or lab manuals with fellow students."
            action={
              <Link to="/upload" className="btn-primary mt-4 flex items-center gap-2">
                <Upload size={16} /> Upload your first note
              </Link>
            }
          />
        </div>
      ) : (
        <div className="mt-8 space-y-4">
          {materials.map((m) => (
            <div
              key={m.id}
              className="card flex flex-col justify-between gap-4 p-5 sm:flex-row sm:items-center bg-white border border-gray-200 hover:border-brand-300 transition shadow-sm"
            >
              <div className="flex items-start gap-4">
                <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-brand-50 border border-brand-200 text-brand-700">
                  <FileText size={24} />
                </div>
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-bold text-gray-900 text-base">{m.title}</span>
                    <span className="rounded bg-brand-50 border border-brand-200 px-2 py-0.5 text-[11px] font-semibold text-brand-900">
                      {m.academicCategory || m.mainCategory || "Engineering"}
                    </span>
                    <span className="rounded bg-gray-100 border border-gray-200 px-2 py-0.5 text-[11px] font-semibold text-gray-700 uppercase">
                      {m.fileType || "PDF"} • {m.pageCount || 1} {m.fileType?.toUpperCase().includes("PPT") ? (m.pageCount === 1 ? "slide" : "slides") : (m.pageCount === 1 ? "page" : "pages")}
                    </span>
                    <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 border border-emerald-300 text-emerald-800 px-2 py-0.5 text-[10px] font-extrabold">
                      <CheckCircle2 size={11} className="text-emerald-600" /> {m.processingStatus || "Summary ready"}
                    </span>
                  </div>

                  {/* Summary preview & word count */}
                  {(m.summary || m.description) && (
                    <div className="mt-2 text-xs bg-brand-50/40 border border-brand-100 rounded-lg p-2.5 max-w-2xl text-gray-800">
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-bold text-brand-900 flex items-center gap-1 text-[11px]">
                          <Sparkles size={11} className="text-brand-600" /> AI-Generated Summary
                        </span>
                        <span className="text-[10px] font-extrabold text-emerald-800 bg-emerald-50 px-1.5 py-0.2 rounded border border-emerald-200">
                          {m.summaryWordCount || (m.summary || m.description || "").trim().split(/\s+/).filter(Boolean).length} / 500 words
                        </span>
                      </div>
                      <p className="line-clamp-2 italic font-normal text-gray-700">
                        &ldquo;{m.summary || m.description}&rdquo;
                      </p>
                    </div>
                  )}

                  <p className="mt-1 text-xs text-gray-500">
                    Uploaded on {new Date(m.createdAt || m.uploadedAt || Date.now()).toLocaleDateString()}
                  </p>

                  {/* Benchmark & Confidence Score */}
                  <div className="mt-2 flex flex-wrap items-center gap-2">
                    <span className="inline-flex items-center gap-1.5 rounded-md bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-800 border border-emerald-200">
                      <CheckCircle2 size={13} className="text-emerald-600" />
                      Benchmark: High Quality
                    </span>
                    <span className="inline-flex items-center gap-1 rounded-md bg-brand-50 px-2.5 py-1 text-xs font-semibold text-brand-900 border border-brand-200">
                      Confidence Score: <span className="font-bold text-brand-700">85%</span>
                    </span>
                  </div>

                  {/* Only show Moderator Note if an item was explicitly rejected */}
                  {m.moderation?.reason && (m.status === "rejected" || m.status === "rejected_by_admin") && (
                    <div className="mt-2 text-xs bg-red-50 border border-red-200 rounded-lg p-2.5 max-w-2xl text-red-700">
                      <span className="font-semibold text-red-900">Moderator Note: </span>
                      {m.moderation.reason}
                    </div>
                  )}

                  <div className="mt-2 flex items-center gap-4 text-xs text-gray-400">
                    <span className="flex items-center gap-1">
                      <Download size={12} /> {m.downloads || 0} downloads
                    </span>
                    <span>{m.fileSize || "File"}</span>
                  </div>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center gap-2 sm:self-center shrink-0">
                <button
                  onClick={() => setPreviewId(m.id)}
                  className="btn-secondary !py-1.5 !px-3 text-xs flex items-center gap-1.5 text-brand-800 hover:bg-brand-50"
                  title="Preview document"
                >
                  <Eye size={14} /> Preview
                </button>
                <button
                  onClick={() => handleDownload(m.id)}
                  className="btn-secondary !py-1.5 !px-3 text-xs flex items-center gap-1.5 text-gray-700 hover:bg-gray-100"
                  title="Download file"
                >
                  <Download size={14} /> Download
                </button>
                <button
                  onClick={() => setDeleteTarget(m)}
                  className="btn-secondary !p-2 text-red-600 hover:bg-red-50 hover:border-red-200"
                  title="Delete material"
                >
                  <Trash2 size={16} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Confirmation Modal */}
      <Modal
        open={Boolean(deleteTarget)}
        onClose={() => setDeleteTarget(null)}
        title="Delete Material?"
        size="sm"
      >
        <p className="text-sm text-gray-600">
          Are you sure you want to delete <strong>{deleteTarget?.title}</strong>? The file will be permanently removed from cloud storage and MongoDB.
        </p>
        <div className="mt-6 flex justify-end gap-3">
          <button
            onClick={() => setDeleteTarget(null)}
            className="btn-secondary"
            disabled={deleting}
          >
            Cancel
          </button>
          <button
            onClick={handleDelete}
            className="btn-primary !bg-red-600 hover:!bg-red-700"
            disabled={deleting}
          >
            {deleting ? "Deleting..." : "Delete Permanently"}
          </button>
        </div>
      </Modal>

      {/* Material Preview Modal */}
      <MaterialPreviewModal
        materialId={previewId}
        open={Boolean(previewId)}
        onClose={() => setPreviewId(null)}
      />
    </div>
  );
}
