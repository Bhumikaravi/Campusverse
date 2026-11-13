import { useEffect, useState, useMemo } from "react";
import { Link, useSearchParams } from "react-router-dom";
import {
  Code,
  Server,
  Cpu,
  Cog,
  Building,
  Zap,
  Sparkles,
  Calculator,
  BookOpen,
  ArrowRight,
  ArrowLeft,
  Layers,
  FileText,
  ChevronRight,
  GraduationCap,
  Search,
  Filter,
  CheckCircle2,
  FolderGit2,
  Stethoscope,
  Briefcase,
  Scale,
  FlaskConical,
  Palette,
  Coins,
} from "lucide-react";
import { categoriesApi, materialsApi, bookmarksApi } from "../services/endpoints";
import Loader, { CardSkeleton } from "../components/Loader";
import MaterialCard from "../components/MaterialCard";
import { EmptyState } from "../components/EmptyState";
import { useToast } from "../context/ToastContext";

const ICON_MAP = {
  Code,
  Server,
  Cpu,
  Cog,
  Building,
  Zap,
  Sparkles,
  Calculator,
  BookOpen,
  GraduationCap,
  Stethoscope,
  Briefcase,
  Scale,
  FlaskConical,
  Palette,
  Coins,
};

export default function Categories() {
  const [params, setParams] = useSearchParams();
  const selectedMainCat = params.get("category") || "";
  const selectedSub = params.get("sub") || "";
  const selectedSubtopic = params.get("topic") || "";
  const queryParam = params.get("q") || "";

  const [categories, setCategories] = useState([]);
  const [loadingCats, setLoadingCats] = useState(true);
  const [search, setSearch] = useState(queryParam || "");

  const [materials, setMaterials] = useState(null);
  const [loadingMaterials, setLoadingMaterials] = useState(false);
  const { showToast } = useToast();

  // Load category tree from backend
  useEffect(() => {
    categoriesApi
      .list()
      .then((res) => {
        setCategories(res.data.categories || []);
      })
      .catch(() => setCategories([]))
      .finally(() => setLoadingCats(false));
  }, []);

  // Sync search input when param changes
  useEffect(() => {
    if (queryParam) setSearch(queryParam);
  }, [queryParam]);

  // Current active main category object
  const activeCategoryObj = useMemo(() => {
    if (!selectedMainCat) return null;
    return categories.find(
      (c) =>
        (c.id && c.id.toLowerCase() === selectedMainCat.toLowerCase()) ||
        c.name.toLowerCase() === selectedMainCat.toLowerCase()
    );
  }, [categories, selectedMainCat]);

  // Current active subcategory object
  const activeSubcategoryObj = useMemo(() => {
    if (!activeCategoryObj || !selectedSub) return null;
    return (
      activeCategoryObj.subcategories?.find(
        (s) => s.name.toLowerCase() === selectedSub.toLowerCase()
      ) || null
    );
  }, [activeCategoryObj, selectedSub]);

  // Load materials when in subcategory or topic view, or searching
  useEffect(() => {
    if (selectedSub || selectedMainCat || queryParam) {
      setLoadingMaterials(true);
      const queryPayload = {};
      if (selectedMainCat) queryPayload.main_category = activeCategoryObj?.name || selectedMainCat;
      if (selectedSub) queryPayload.subcategory = selectedSub;
      if (selectedSubtopic) queryPayload.topic = selectedSubtopic;
      else if (queryParam) queryPayload.q = queryParam;

      materialsApi
        .list(queryPayload)
        .then((res) => {
          setMaterials(res.data.materials || res.data.items || []);
        })
        .catch(() => setMaterials([]))
        .finally(() => setLoadingMaterials(false));
    } else {
      setMaterials(null);
    }
  }, [selectedMainCat, selectedSub, selectedSubtopic, queryParam, activeCategoryObj]);

  const handleToggleBookmark = async (id) => {
    try {
      await bookmarksApi.toggle(id);
      setMaterials((prev) =>
        prev
          ? prev.map((m) =>
              m.id === id ? { ...m, bookmarked: !m.bookmarked } : m
            )
          : prev
      );
    } catch {
      showToast("Log in to bookmark materials.", "error");
    }
  };

  const clearToMain = () => {
    setParams({});
    setSearch("");
  };

  const selectMain = (cat) => {
    setParams({ category: cat.id || cat.name.toLowerCase() });
    setSearch("");
  };

  const selectSub = (subName) => {
    setParams({
      category: activeCategoryObj?.id || selectedMainCat,
      sub: subName,
    });
  };

  const selectTopic = (topicName) => {
    if (selectedSubtopic === topicName) {
      // Toggle off
      setParams({
        category: activeCategoryObj?.id || selectedMainCat,
        sub: selectedSub,
      });
    } else {
      setParams({
        category: activeCategoryObj?.id || selectedMainCat,
        sub: selectedSub,
        topic: topicName,
      });
    }
  };

  // Search filter across main categories and subcategories
  const searchResults = useMemo(() => {
    if (!search.trim()) return null;
    const term = search.toLowerCase();
    const matches = [];

    categories.forEach((cat) => {
      // Check main category match
      const catMatch =
        cat.name.toLowerCase().includes(term) ||
        cat.description?.toLowerCase().includes(term);

      // Check subcategories and subtopics
      (cat.subcategories || []).forEach((sub) => {
        const subMatch =
          sub.name.toLowerCase().includes(term) ||
          sub.description?.toLowerCase().includes(term);
        const matchedTopics = (sub.subtopics || []).filter((top) =>
          top.toLowerCase().includes(term)
        );

        if (catMatch || subMatch || matchedTopics.length > 0) {
          matches.push({
            mainCat: cat,
            subcat: sub,
            matchedTopics,
          });
        }
      });
    });

    return matches;
  }, [categories, search]);

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
      {/* Top Breadcrumb Navigation */}
      <nav className="mb-6 flex items-center flex-wrap gap-2 text-xs font-medium text-white/80">
        <button
          onClick={clearToMain}
          className="hover:text-white transition flex items-center gap-1 hover:underline"
        >
          <Layers size={14} /> Categories
        </button>

        {activeCategoryObj && (
          <>
            <ChevronRight size={13} className="text-white/40" />
            <button
              onClick={() => selectMain(activeCategoryObj)}
              className={`hover:text-white transition ${
                !selectedSub ? "text-white font-bold" : "hover:underline"
              }`}
            >
              {activeCategoryObj.name}
            </button>
          </>
        )}

        {selectedSub && (
          <>
            <ChevronRight size={13} className="text-white/40" />
            {selectedSubtopic ? (
              <button
                onClick={() =>
                  setParams({
                    category: activeCategoryObj?.id || selectedMainCat,
                    sub: selectedSub,
                  })
                }
                className="hover:text-white transition hover:underline"
              >
                {selectedSub}
              </button>
            ) : (
              <span className="text-white font-bold">{selectedSub}</span>
            )}
          </>
        )}

        {selectedSubtopic && (
          <>
            <ChevronRight size={13} className="text-white/40" />
            <span className="rounded bg-white/20 px-2 py-0.5 text-white font-semibold">
              {selectedSubtopic}
            </span>
          </>
        )}
      </nav>

      {/* Header & Search */}
      <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between border-b border-white/10 pb-6">
        <div>
          <span className="mb-2 inline-flex items-center gap-1.5 rounded-full bg-white/20 border border-white/30 px-3 py-1 text-xs font-semibold text-white backdrop-blur">
            <GraduationCap size={14} /> Curated Academic Knowledge Base
          </span>
          <h1 className="font-display text-3xl font-bold text-white tracking-tight">
            {selectedSub
              ? selectedSub
              : activeCategoryObj
              ? `${activeCategoryObj.name} Disciplines`
              : "Academic Categories & Disciplines"}
          </h1>
          <p className="mt-1 text-sm text-white/90 max-w-2xl">
            {selectedSub
              ? `Browse syllabus-aligned notes, lab experiments, manuals, and questions for ${selectedSub}.`
              : activeCategoryObj
              ? activeCategoryObj.description
              : "Explore peer-reviewed study notes, previous exam question banks, and textbook solutions categorized by faculty, branch, and topic."}
          </p>
        </div>

        {/* Search input */}
        <div className="w-full md:w-80">
          <div className="relative">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400" size={16} />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search branch, topic, or subject..."
              className="w-full rounded-xl border border-white/20 bg-white/90 py-2.5 pl-10 pr-4 text-sm text-gray-900 placeholder-gray-500 shadow-sm backdrop-blur focus:bg-white focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
            {search && (
              <button
                type="button"
                onClick={() => setSearch("")}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-gray-400 hover:text-gray-700"
              >
                Clear
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Global Search Results Mode */}
      {searchResults && (
        <div className="mt-6">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-white">
              Search Results for &ldquo;{search}&rdquo; ({searchResults.length} disciplines found)
            </h2>
            <button
              onClick={() => setSearch("")}
              className="text-xs text-white/80 hover:text-white underline"
            >
              Reset Search
            </button>
          </div>

          {searchResults.length === 0 ? (
            <div className="card p-8 text-center bg-white/95 rounded-2xl">
              <Search className="mx-auto text-gray-400" size={32} />
              <h3 className="mt-2 font-display text-base font-semibold text-gray-900">
                No disciplines found
              </h3>
              <p className="text-sm text-gray-500">
                We couldn&apos;t find branches matching &ldquo;{search}&rdquo;. Try another keyword.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {searchResults.map(({ mainCat, subcat, matchedTopics }, idx) => (
                <div
                  key={`${mainCat.id}-${subcat.name}-${idx}`}
                  className="card p-5 bg-white rounded-xl shadow-sm hover:shadow-md transition flex flex-col justify-between"
                >
                  <div>
                    <div className="flex items-center justify-between text-xs text-gray-500 mb-2">
                      <span className="font-semibold text-primary-600 uppercase tracking-wider">
                        {mainCat.name}
                      </span>
                      <span className="rounded-full bg-gray-100 px-2 py-0.5 font-medium">
                        {subcat.count || 0} materials
                      </span>
                    </div>
                    <h3 className="font-display text-base font-bold text-gray-900">
                      {subcat.name}
                    </h3>
                    <p className="mt-1 text-xs text-gray-500 line-clamp-2">
                      {subcat.description || "Course notes and subject materials."}
                    </p>

                    {matchedTopics.length > 0 && (
                      <div className="mt-3">
                        <span className="text-[10px] font-semibold uppercase text-gray-400">
                          Matching topics:
                        </span>
                        <div className="mt-1 flex flex-wrap gap-1">
                          {matchedTopics.slice(0, 3).map((top) => (
                            <span
                              key={top}
                              className="rounded bg-yellow-100 px-1.5 py-0.5 text-[11px] font-medium text-yellow-800"
                            >
                              {top}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>

                  <button
                    onClick={() => {
                      setParams({
                        category: mainCat.id || mainCat.name.toLowerCase(),
                        sub: subcat.name,
                      });
                      setSearch("");
                    }}
                    className="mt-4 flex items-center justify-between rounded-lg bg-gray-50 px-3 py-2 text-xs font-semibold text-gray-800 hover:bg-gray-100 transition"
                  >
                    <span>Explore branch notes</span>
                    <ArrowRight size={13} />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Loading Categories state */}
      {loadingCats && !searchResults && (
        <div className="py-24">
          <Loader label="Loading academic disciplines..." />
        </div>
      )}

      {/* LEVEL 3: Inside a Subcategory (Branch selected -> Show Subtopics + Materials) */}
      {!loadingCats && !searchResults && selectedSub && (
        <div className="mt-6 space-y-6">
          {/* Back button & Subcategory Summary Card */}
          <div className="flex items-center justify-between">
            <button
              onClick={() =>
                setParams({ category: activeCategoryObj?.id || selectedMainCat })
              }
              className="inline-flex items-center gap-2 rounded-lg border border-white/30 bg-white/10 px-3.5 py-1.5 text-xs font-semibold text-white backdrop-blur transition hover:bg-white/20"
            >
              <ArrowLeft size={14} /> Back to {activeCategoryObj?.name || "Disciplines"}
            </button>

            <Link
              to={`/upload?category=${encodeURIComponent(
                activeCategoryObj?.name || ""
              )}&sub=${encodeURIComponent(selectedSub)}`}
              className="inline-flex items-center gap-1.5 rounded-lg bg-white px-3.5 py-1.5 text-xs font-bold text-gray-900 shadow hover:bg-gray-100 transition"
            >
              <FolderGit2 size={14} /> Contribute Notes to this Branch
            </Link>
          </div>

          {/* Subtopics Pill Filter */}
          {activeSubcategoryObj?.subtopics &&
            activeSubcategoryObj.subtopics.length > 0 && (
              <div className="rounded-2xl bg-white/95 p-5 shadow backdrop-blur">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <Filter size={15} className="text-gray-600" />
                    <span className="text-xs font-bold uppercase tracking-wider text-gray-700">
                      Subtopics & Subjects in {selectedSub}
                    </span>
                  </div>
                  {selectedSubtopic && (
                    <button
                      onClick={() =>
                        setParams({
                          category: activeCategoryObj?.id || selectedMainCat,
                          sub: selectedSub,
                        })
                      }
                      className="text-xs font-semibold text-primary-600 hover:underline"
                    >
                      Show all {selectedSub} topics
                    </button>
                  )}
                </div>

                <div className="flex flex-wrap gap-2">
                  <button
                    onClick={() =>
                      setParams({
                        category: activeCategoryObj?.id || selectedMainCat,
                        sub: selectedSub,
                      })
                    }
                    className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                      !selectedSubtopic
                        ? "bg-gray-900 text-white shadow"
                        : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                    }`}
                  >
                    All Subtopics
                  </button>

                  {activeSubcategoryObj.subtopics.map((topic) => {
                    const isActive = selectedSubtopic === topic;
                    return (
                      <button
                        key={topic}
                        onClick={() => selectTopic(topic)}
                        className={`rounded-lg px-3 py-1.5 text-xs font-medium transition flex items-center gap-1.5 ${
                          isActive
                            ? "bg-primary-600 text-white shadow font-semibold"
                            : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                        }`}
                      >
                        {isActive && <CheckCircle2 size={12} />}
                        {topic}
                      </button>
                    );
                  })}
                </div>
              </div>
            )}

          {/* Materials Section */}
          <div>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                <FileText size={18} />
                <span>
                  {selectedSubtopic
                    ? `Materials for ${selectedSubtopic}`
                    : `All Materials in ${selectedSub}`}
                </span>
                <span className="rounded-full bg-white/20 px-2 py-0.5 text-xs font-normal">
                  {materials?.length ?? 0}
                </span>
              </h2>
            </div>

            {loadingMaterials ? (
              <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
                {Array.from({ length: 4 }).map((_, i) => (
                  <CardSkeleton key={i} />
                ))}
              </div>
            ) : !materials || materials.length === 0 ? (
              <div className="mt-4">
                <EmptyState
                  icon={FileText}
                  title="No study materials available for this topic yet."
                  message={
                    selectedSubtopic
                      ? `No study materials uploaded under "${selectedSubtopic}" yet. Be the first to share verified notes for this topic!`
                      : `No verified materials uploaded for ${selectedSub} yet. Be the first to upload!`
                  }
                  action={
                    <div className="flex flex-wrap gap-3 justify-center mt-4">
                      <Link
                        to={`/upload?category=${encodeURIComponent(
                          activeCategoryObj?.name || ""
                        )}&sub=${encodeURIComponent(
                          selectedSub
                        )}&topic=${encodeURIComponent(selectedSubtopic || "")}`}
                        className="btn-primary"
                      >
                        Upload Notes for this Topic
                      </Link>
                      <Link to="/dashboard" className="btn-secondary">
                        Scan on Dashboard
                      </Link>
                    </div>
                  }
                />
              </div>
            ) : (
              <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
                {materials.map((m) => (
                  <MaterialCard
                    key={m.id || m._id}
                    material={m}
                    onToggleBookmark={handleToggleBookmark}
                  />
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* LEVEL 2: Inside a Main Category (Show Subcategories e.g., 8 Engineering branches) */}
      {!loadingCats && !searchResults && activeCategoryObj && !selectedSub && (
        <div className="mt-6 space-y-6">
          <div className="flex items-center justify-between">
            <button
              onClick={clearToMain}
              className="inline-flex items-center gap-2 rounded-lg border border-white/30 bg-white/10 px-3.5 py-1.5 text-xs font-semibold text-white backdrop-blur transition hover:bg-white/20"
            >
              <ArrowLeft size={14} /> Back to All Academic Categories
            </button>

            <span className="text-xs text-white/80">
              {activeCategoryObj.subcategories?.length || 0} Specialized Branches
            </span>
          </div>

          {/* Subcategories Grid */}
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {(activeCategoryObj.subcategories || []).map((sub, index) => {
              return (
                <div
                  key={sub.name}
                  className="card group flex flex-col justify-between p-6 bg-white rounded-2xl shadow-sm hover:shadow-xl transition-all duration-200 border border-gray-100 hover:border-gray-300"
                >
                  <div>
                    {/* Badge and Branch Index */}
                    <div className="flex items-center justify-between text-xs text-gray-500 mb-3">
                      <span className="font-mono text-[11px] font-bold text-gray-400">
                        BRANCH #{String(index + 1).padStart(2, "0")}
                      </span>
                      <span className="rounded-full bg-primary-50 px-2.5 py-0.5 font-bold text-primary-700 text-xs">
                        {sub.count ?? 0} {sub.count === 1 ? "note" : "notes"}
                      </span>
                    </div>

                    <h2 className="font-display text-xl font-bold text-gray-900 group-hover:text-primary-700 transition">
                      {sub.name}
                    </h2>

                    <p className="mt-2 text-xs leading-relaxed text-gray-600 line-clamp-2">
                      {sub.description ||
                        `Comprehensive curriculum resources and lecture notes for ${sub.name}.`}
                    </p>

                    {/* Subtopics Preview */}
                    {sub.subtopics && sub.subtopics.length > 0 && (
                      <div className="mt-4 border-t border-gray-100 pt-3">
                        <span className="text-[11px] font-bold uppercase tracking-wider text-gray-400 block mb-2">
                          Key Subtopics ({sub.subtopics.length}):
                        </span>
                        <div className="flex flex-wrap gap-1.5 max-h-24 overflow-hidden">
                          {sub.subtopics.slice(0, 4).map((top) => (
                            <span
                              key={top}
                              className="rounded-md bg-gray-100 px-2 py-0.5 text-[11px] font-medium text-gray-700 hover:bg-gray-200 transition"
                            >
                              {top}
                            </span>
                          ))}
                          {sub.subtopics.length > 4 && (
                            <span className="rounded-md bg-primary-50 px-2 py-0.5 text-[11px] font-semibold text-primary-600">
                              +{sub.subtopics.length - 4} more
                            </span>
                          )}
                        </div>
                      </div>
                    )}
                  </div>

                  <div className="mt-6 border-t border-gray-100 pt-4 flex items-center justify-between">
                    <button
                      onClick={() => selectSub(sub.name)}
                      className="w-full flex items-center justify-center gap-2 rounded-xl bg-gray-900 px-4 py-2.5 text-xs font-bold text-white transition hover:bg-primary-600 shadow-sm"
                    >
                      <span>Explore {sub.name}</span>
                      <ArrowRight size={14} />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* LEVEL 1: Main Category Cards (Engineering, Medical, Science, etc.) */}
      {!loadingCats && !searchResults && !activeCategoryObj && !selectedSub && (
        <div className="mt-8 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {categories.map((cat) => {
            const Icon = ICON_MAP[cat.icon] || BookOpen;
            const branchCount = cat.subcategories?.length || 0;

            return (
              <button
                type="button"
                key={cat.id || cat.name}
                onClick={() => selectMain(cat)}
                className="card group flex flex-col justify-between p-6 text-left transition duration-200 hover:-translate-y-1 hover:shadow-xl cursor-pointer bg-white rounded-2xl relative overflow-hidden border border-gray-100 hover:border-primary-300"
              >
                <div className="absolute top-0 right-0 bg-primary-50 text-primary-700 text-[10px] font-bold px-3 py-1 rounded-bl-lg uppercase tracking-wider">
                  {branchCount} {branchCount === 1 ? "Branch" : "Branches"}
                </div>

                <div>
                  <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-gray-100 text-gray-800 transition group-hover:bg-gray-900 group-hover:text-white">
                    <Icon size={24} />
                  </div>

                  <h2 className="mt-4 font-display text-lg font-bold text-gray-900 group-hover:text-primary-700 transition">
                    {cat.name}
                  </h2>

                  <p className="mt-2 text-xs leading-relaxed text-gray-500 line-clamp-3">
                    {cat.description || "Course materials, practical files and exam guides."}
                  </p>
                </div>

                <div className="mt-6 flex items-center justify-between border-t border-gray-100 pt-4 text-xs font-semibold text-gray-500">
                  <span className="flex items-center gap-1 font-medium text-gray-700">
                    <Layers size={13} className="text-gray-400" />
                    {branchCount} {branchCount === 1 ? "branch" : "branches"}
                  </span>
                  <span className="flex items-center gap-1 text-primary-600 group-hover:underline">
                    Browse <ArrowRight size={13} />
                  </span>
                </div>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
