import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Bookmark, ArrowRight } from "lucide-react";
import { bookmarksApi } from "../services/endpoints";
import MaterialCard from "../components/MaterialCard";
import Loader from "../components/Loader";
import { EmptyState } from "../components/EmptyState";
import { useToast } from "../context/ToastContext";

export default function Bookmarks() {
  const [materials, setMaterials] = useState([]);
  const [loading, setLoading] = useState(true);
  const { showToast } = useToast();

  const loadBookmarks = () => {
    setLoading(true);
    bookmarksApi
      .list()
      .then((res) => setMaterials(res.data.materials || []))
      .catch(() => setMaterials([]))
      .finally(() => setLoading(false));
  };

  useEffect(loadBookmarks, []);

  const handleToggleBookmark = async (id) => {
    try {
      await bookmarksApi.toggle(id);
      setMaterials((prev) => prev.filter((m) => m.id !== id));
      showToast("Removed from bookmarks", "info");
    } catch {
      showToast("Could not update bookmark.", "error");
    }
  };

  return (
    <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6">
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gray-100 text-gray-800">
          <Bookmark size={20} />
        </div>
        <div>
          <h1 className="font-display text-3xl font-bold text-white drop-shadow-xs">Saved Bookmarks</h1>
          <p className="mt-0.5 text-sm text-white/90 font-medium drop-shadow-2xs">
            Study guides and question papers you have saved for fast revision.
          </p>
        </div>
      </div>

      {loading ? (
        <div className="py-20">
          <Loader label="Loading your bookmarks..." />
        </div>
      ) : materials.length === 0 ? (
        <div className="mt-8">
          <EmptyState
            icon={Bookmark}
            title="No bookmarks yet"
            message="Click the bookmark icon on any study material to quickly save it for exam prep."
            action={
              <Link to="/categories" className="btn-primary mt-4">
                Browse categories <ArrowRight size={16} />
              </Link>
            }
          />
        </div>
      ) : (
        <div className="mt-8 grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {materials.map((m) => (
            <MaterialCard
              key={m.id}
              material={m}
              onToggleBookmark={handleToggleBookmark}
            />
          ))}
        </div>
      )}
    </div>
  );
}
