import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Download, FileText, ArrowRight, Clock } from "lucide-react";
import { historyApi, materialsApi } from "../services/endpoints";
import { useToast } from "../context/ToastContext";
import Loader from "../components/Loader";
import { EmptyState } from "../components/EmptyState";

export default function DownloadHistory() {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const { showToast } = useToast();

  useEffect(() => {
    historyApi
      .list()
      .then((res) => setHistory(res.data.history || []))
      .catch(() => setHistory([]))
      .finally(() => setLoading(false));
  }, []);

  const handleReDownload = async (materialId) => {
    try {
      const res = await materialsApi.download(materialId);
      window.open(res.data.url, "_blank");
      showToast("Download started", "success");
    } catch {
      showToast("Could not download file.", "error");
    }
  };

  return (
    <div className="mx-auto max-w-5xl px-4 py-10 sm:px-6">
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gray-100 text-gray-800">
          <Download size={20} />
        </div>
        <div>
          <h1 className="font-display text-3xl font-bold text-white drop-shadow-xs">Download History</h1>
          <p className="mt-0.5 text-sm text-white/90 font-medium drop-shadow-2xs">
            Keep track of past notes and guides you've downloaded on this device.
          </p>
        </div>
      </div>

      {loading ? (
        <div className="py-20">
          <Loader label="Loading download history..." />
        </div>
      ) : history.length === 0 ? (
        <div className="mt-8">
          <EmptyState
            icon={Download}
            title="No downloads recorded yet"
            message="When you download notes and study guides, they'll appear here for instant re-download."
            action={
              <Link to="/categories" className="btn-primary mt-4">
                Browse categories <ArrowRight size={16} />
              </Link>
            }
          />
        </div>
      ) : (
        <div className="mt-8 card overflow-hidden">
          <div className="divide-y divide-gray-100 dark:divide-gray-800">
            {history.map((item) => (
              <div
                key={item.id}
                className="flex flex-col justify-between gap-4 p-5 transition hover:bg-gray-50 dark:hover:bg-gray-800/40 sm:flex-row sm:items-center"
              >
                <div className="flex items-start gap-4">
                  <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-gray-100 text-gray-700">
                    <FileText size={22} />
                  </div>
                  <div>
                    <h3 className="font-semibold text-gray-900 dark:text-gray-100">
                      {item.title}
                    </h3>
                    <p className="mt-0.5 text-xs text-gray-500 dark:text-gray-400">
                      {item.subject} • {item.fileSize || "4.2 MB"}
                    </p>
                    <div className="mt-1 flex items-center gap-1 text-[11px] text-gray-400">
                      <Clock size={12} /> Downloaded{" "}
                      {new Date(item.downloadedAt || Date.now()).toLocaleDateString()}{" "}
                      at{" "}
                      {new Date(item.downloadedAt || Date.now()).toLocaleTimeString([], {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleReDownload(item.materialId)}
                    className="btn-secondary !py-2 text-xs"
                  >
                    <Download size={14} /> Download again
                  </button>
                  {item.materialId && (
                    <Link
                      to={`/materials/${item.materialId}`}
                      className="btn-secondary !p-2"
                      title="View details"
                    >
                      <ArrowRight size={14} />
                    </Link>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
