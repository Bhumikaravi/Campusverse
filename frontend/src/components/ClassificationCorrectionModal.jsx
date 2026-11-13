import { useState } from "react";
import { Sparkles, Check, X } from "lucide-react";
import Modal from "./Modal";
import { classifierApi } from "../services/endpoints";
import { useToast } from "../context/ToastContext";

export default function ClassificationCorrectionModal({
  isOpen,
  onClose,
  materialId,
  currentBranch,
  currentSubject,
  currentTopic,
  onSuccess
}) {
  const { showToast } = useToast();
  const [branch, setBranch] = useState(currentBranch || "");
  const [subject, setSubject] = useState(currentSubject || "");
  const [topic, setTopic] = useState(currentTopic || "");
  const [reason, setReason] = useState("");
  const [saving, setSaving] = useState(false);

  const handleSave = async (e) => {
    e.preventDefault();
    if (!branch.trim() || !subject.trim()) {
      showToast("Branch and Subject are required.", "error");
      return;
    }

    setSaving(true);
    try {
      const res = await classifierApi.correct(materialId, {
        branch: branch.trim(),
        subject: subject.trim(),
        topic: topic.trim() || undefined,
        reason: reason.trim() || "User adjusted classification"
      });
      showToast("Classification updated successfully!", "success");
      if (onSuccess) onSuccess(res.data.classification);
      onClose();
    } catch (err) {
      showToast(err.friendlyMessage || "Failed to update classification.", "error");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Correct Academic Classification">
      <form onSubmit={handleSave} className="space-y-4 text-gray-800 text-sm">
        <p className="text-xs text-gray-600">
          Adjust the academic classification if the automated prediction needs refinement.
        </p>

        <div>
          <label className="block text-xs font-bold text-gray-700 uppercase tracking-wider mb-1">
            Academic Branch / Department *
          </label>
          <input
            type="text"
            value={branch}
            onChange={(e) => setBranch(e.target.value)}
            className="input-field w-full"
            placeholder="e.g. Computer Science, Mechanical Engineering"
            required
          />
        </div>

        <div>
          <label className="block text-xs font-bold text-gray-700 uppercase tracking-wider mb-1">
            Subject *
          </label>
          <input
            type="text"
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
            className="input-field w-full"
            placeholder="e.g. Artificial Intelligence, Data Structures"
            required
          />
        </div>

        <div>
          <label className="block text-xs font-bold text-gray-700 uppercase tracking-wider mb-1">
            Primary Topic (Optional)
          </label>
          <input
            type="text"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            className="input-field w-full"
            placeholder="e.g. Neural Networks, Sorting Algorithms"
          />
        </div>

        <div>
          <label className="block text-xs font-bold text-gray-700 uppercase tracking-wider mb-1">
            Reason for Correction
          </label>
          <textarea
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            rows={2}
            className="input-field w-full resize-none text-xs"
            placeholder="Brief reason for adjusting the classification..."
          />
        </div>

        <div className="flex justify-end gap-2 border-t border-gray-100 pt-3">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg bg-gray-100 hover:bg-gray-200 text-gray-700 text-xs font-semibold"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={saving}
            className="btn-primary !px-4 !py-1.5 !text-xs flex items-center gap-1.5"
          >
            <Check size={14} />
            {saving ? "Saving..." : "Save Classification"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
