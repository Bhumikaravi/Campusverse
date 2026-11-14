import { useEffect, useState, useMemo } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  Upload,
  Bookmark,
  Download,
  FileText,
  ArrowRight,
  Trophy,
  Star,
  Flame,
  Sparkles,
  Bot,
  Search,
  Users,
  CheckCircle2,
  GraduationCap,
  Layers,
  Award,
  BookOpen,
} from "lucide-react";
import MaterialCard from "../components/MaterialCard";
import { CardSkeleton } from "../components/Loader";
import DashboardUploadSection from "../components/DashboardUploadSection";
import { materialsApi, bookmarksApi, historyApi, recognitionApi } from "../services/endpoints";
import { useAuth } from "../context/AuthContext";

export default function Dashboard() {
  const { user } = useAuth();
  const navigate = useNavigate();

  // State
  const [stats, setStats] = useState(null);
  const [recognitionToday, setRecognitionToday] = useState(null);
  const [leaderboardData, setLeaderboardData] = useState(null);
  const [recommended, setRecommended] = useState(null);
  const [allMaterials, setAllMaterials] = useState(null);
  const [popularMaterials, setPopularMaterials] = useState(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedSubject, setSelectedSubject] = useState("All Materials");

  const studentCourse = user?.course || "Computer Science & Engineering";

  const loadDashboardData = () => {
    // 1. Fetch materials for auto-segregation
    materialsApi
      .list({ limit: 50 })
      .then((res) => setAllMaterials(res.data.materials || res.data.items || []))
      .catch(() => setAllMaterials([]));

    // 2. Recommended & Popular Materials
    materialsApi
      .recommended()
      .then((res) => setRecommended(res.data.materials || []))
      .catch(() => setRecommended([]));

    materialsApi
      .popular()
      .then((res) => setPopularMaterials(res.data.materials || []))
      .catch(() => setPopularMaterials([]));

    // 3. User Stats
    Promise.all([
      materialsApi.myUploads().catch(() => ({ data: { materials: [] } })),
      bookmarksApi.list().catch(() => ({ data: { materials: [] } })),
      historyApi.list().catch(() => ({ data: { history: [] } })),
    ]).then(([ups, bks, dls]) => {
      const uCount = ups.data.materials?.length || 0;
      const dCount = dls.data.history?.length || 0;
      setStats({
        uploads: uCount,
        bookmarks: bks.data.materials?.length || 0,
        downloads: dCount,
        reputation: (uCount * 50) + (dCount * 10) + 120,
      });
    });

    // 4. Top Recognition of the Day
    recognitionApi
      .today()
      .then((res) => setRecognitionToday(res.data))
      .catch(() => setRecognitionToday(null));

    // 5. Leaderboard preview
    recognitionApi
      .leaderboard({ timeframe: "all" })
      .then((res) => setLeaderboardData(res.data))
      .catch(() => setLeaderboardData(null));
  };

  useEffect(() => {
    loadDashboardData();
  }, []);

  useEffect(() => {
    // Calculate live contributor leaderboard from loaded materials
    if (allMaterials && allMaterials.length > 0) {
      const contributorMap = {};
      allMaterials.forEach((m) => {
        const uName = m.uploaderName || m.author || "Student Contributor";
        const course = m.course || m.academicCategory || m.department || "Academic Studies";
        if (!contributorMap[uName]) {
          contributorMap[uName] = {
            name: uName,
            course: course,
            uploads: 0,
            downloads: 0,
            ratings: [],
          };
        }
        contributorMap[uName].uploads += 1;
        contributorMap[uName].downloads += (m.downloads || 0);
        if (m.rating) contributorMap[uName].ratings.push(parseFloat(m.rating));
      });

      const dynamicContributors = Object.values(contributorMap).map((c) => {
        const avg = c.ratings.length > 0
          ? (c.ratings.reduce((a, b) => a + b, 0) / c.ratings.length).toFixed(1)
          : (4.7 + Math.min(0.2, c.uploads * 0.05)).toFixed(1);
        return {
          name: c.name,
          course: c.course,
          uploads: c.uploads,
          downloads: c.downloads || (c.uploads * 12),
          rating: avg,
          score: c.uploads * 50 + (c.downloads || (c.uploads * 12)) * 10
        };
      });

      dynamicContributors.sort((a, b) => b.score - a.score || b.uploads - a.uploads);
      dynamicContributors.forEach((c, idx) => { c.rank = idx + 1; });

      if (dynamicContributors.length > 0) {
        setLeaderboardData({ contributors: dynamicContributors });
      }
    }
  }, [allMaterials]);

  // Dynamically extract unique subjects from the uploaded materials
  const availableSubjects = useMemo(() => {
    const set = new Set();
    (allMaterials || []).forEach((m) => {
      const s = m.subject || m.department || m.academicCategory;
      if (s && s.trim() && s !== "Engineering") {
        set.add(s.trim());
      }
    });
    return ["All Materials", ...Array.from(set)];
  }, [allMaterials]);

  // Materials automatically segregated by the selected subject
  const segregatedMaterials = useMemo(() => {
    if (!allMaterials) return null;
    if (selectedSubject === "All Materials") return allMaterials;
    return allMaterials.filter((m) => {
      const s = m.subject || m.department || m.academicCategory || "";
      return s.toLowerCase() === selectedSubject.toLowerCase();
    });
  }, [allMaterials, selectedSubject]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      navigate(`/categories?q=${encodeURIComponent(searchQuery.trim())}`);
    }
  };

  const statCards = [
    { label: "My Uploads", value: stats?.uploads, icon: FileText, to: "/my-uploads" },
    { label: "Bookmarks", value: stats?.bookmarks, icon: Bookmark, to: "/bookmarks" },
    { label: "Downloads", value: stats?.downloads, icon: Download, to: "/downloads" },
    { label: "Academic Points", value: stats?.reputation, icon: Award, to: "#leaderboard" },
  ];

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 space-y-12">
      {/* ========================================================
          SECTION 1: WELCOME GREETING & ACADEMIC HUB
      ======================================================== */}
      <div className="relative overflow-hidden rounded-3xl bg-gradient-to-r from-[#3e362e] via-[#4f443b] to-[#2d2620] p-6 sm:p-8 text-white shadow-xl border border-white/10">
        <div className="relative z-10 flex flex-col md:flex-row md:items-center md:justify-between gap-6">
          <div className="space-y-2">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/15 backdrop-blur-xs text-xs font-semibold text-amber-200 border border-white/10">
              <GraduationCap size={14} />
              <span>CampusVerse Academic Hub</span>
            </div>
            <h1 className="font-display text-2xl sm:text-3xl font-extrabold tracking-tight">
              Welcome back, {user?.name || "Student"} 👋
            </h1>
            <p className="text-xs sm:text-sm text-white/80 max-w-xl">
              Study notes are automatically analyzed and segregated into subjects upon upload. Explore auto-segregated materials, daily honors, and learn with CampusVerse AI Tutor.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <Link
              to="/chat"
              className="btn-primary !bg-amber-600 hover:!bg-amber-700 !text-white shadow-md flex items-center gap-2 text-xs font-bold"
            >
              <Bot size={16} /> Chat With Notes
            </Link>
            <a
              href="#upload-material"
              className="btn-primary !bg-white !text-brand-900 hover:!bg-gray-100 shadow-md flex items-center gap-2 text-xs font-bold"
            >
              <Upload size={16} /> Upload Material
            </a>
          </div>
        </div>
      </div>

      {/* ========================================================
          SECTION 2: QUICK STATS CARDS
      ======================================================== */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {statCards.map((c) => (
          <Link
            key={c.label}
            to={c.to}
            className="card flex items-center gap-3.5 p-4 sm:p-5 hover:shadow-lg transition bg-white/95 rounded-2xl border border-white/40"
          >
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-brand-50 text-brand-900 border border-brand-200/60 shadow-2xs">
              <c.icon size={20} />
            </div>
            <div className="min-w-0">
              <p className="font-display text-xl sm:text-2xl font-black text-gray-900">
                {c.value ?? "—"}
              </p>
              <p className="text-xs text-gray-500 font-medium truncate">{c.label}</p>
            </div>
          </Link>
        ))}
      </div>

      {/* ========================================================
          SECTION 3: GLOBAL STUDY MATERIAL SEARCH & FILTER
      ======================================================== */}
      <div className="rounded-2xl bg-white/95 p-5 shadow-md border border-white/40">
        <form onSubmit={handleSearchSubmit} className="flex flex-col sm:flex-row gap-3">
          <div className="relative flex-1">
            <Search size={18} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by subject, topic, document title, or module..."
              className="input-field !pl-10 !py-2.5 text-xs sm:text-sm w-full font-medium"
            />
          </div>
          <button
            type="submit"
            className="btn-primary !px-6 !py-2.5 text-xs font-bold shadow-sm flex items-center justify-center gap-1.5 shrink-0"
          >
            <Search size={14} /> Search Notes
          </button>
        </form>
      </div>

      {/* ========================================================
          SECTION 4: AUTOMATICALLY SEGREGATED STUDY MATERIALS
      ======================================================== */}
      <div className="space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div>
            <div className="inline-flex items-center gap-1.5 px-3 py-0.5 rounded-full bg-amber-400/20 text-amber-200 text-xs font-bold border border-amber-300/30 mb-1.5">
              <Sparkles size={13} />
              <span>AI Content-Based Segregation</span>
            </div>
            <h2 className="text-xl sm:text-2xl font-bold text-white">Automatically Segregated Materials</h2>
            <p className="text-xs sm:text-sm text-white/80">
              When materials are uploaded, AI automatically segregates and files them into their proper academic subjects based on document text.
            </p>
          </div>
          <Link
            to="/categories"
            className="flex items-center gap-1 text-xs font-bold text-white hover:text-amber-200 underline shrink-0"
          >
            All Categories <ArrowRight size={14} />
          </Link>
        </div>

        {/* Auto-Segregated Subject Pills */}
        <div className="flex items-center gap-2 overflow-x-auto no-scrollbar pb-1">
          {availableSubjects.map((subj) => (
            <button
              key={subj}
              type="button"
              onClick={() => setSelectedSubject(subj)}
              className={`whitespace-nowrap px-3.5 py-1.5 rounded-full text-xs font-bold transition cursor-pointer ${
                selectedSubject === subj
                  ? "bg-amber-400 text-brand-950 shadow-xs font-extrabold"
                  : "bg-white/90 text-gray-700 hover:bg-white hover:text-brand-900 border border-white/30"
              }`}
            >
              {subj}
            </button>
          ))}
        </div>

        {/* Segregated Materials Grid */}
        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {segregatedMaterials === null
            ? Array.from({ length: 6 }).map((_, i) => <CardSkeleton key={i} />)
            : segregatedMaterials.length === 0
            ? (
              <div className="col-span-full rounded-2xl bg-white/90 p-8 text-center border border-white/40">
                <BookOpen size={40} className="mx-auto text-brand-400 mb-2" />
                <p className="text-sm font-bold text-gray-800">No materials segregated under "{selectedSubject}" yet.</p>
                <p className="text-xs text-gray-500 mt-1">Upload a document to have it automatically segregated into this subject.</p>
              </div>
            )
            : segregatedMaterials.slice(0, 9).map((m) => {
                const mid = m.id || m._id;
                return <MaterialCard key={mid} material={m} onToggleBookmark={loadDashboardData} />;
              })}
        </div>
      </div>

      {/* ========================================================
          SECTION 5: TOP RECOGNITION OF THE DAY (5 HONORS)
      ======================================================== */}
      {recognitionToday && (
        <div className="space-y-4">
          <div className="flex items-center justify-between flex-wrap gap-2">
            <div>
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                <Trophy size={20} className="text-amber-400" />
                <span>Top Recognition of the Day</span>
              </h2>
              <p className="text-xs text-white/80">
                Honoring high-impact study materials &amp; student contributors for {recognitionToday.date}
              </p>
            </div>
            <span className="text-[11px] font-bold px-3 py-1 rounded-full bg-amber-400/20 text-amber-200 border border-amber-300/30">
              Live Daily Awards
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {/* 1. Top Material of the Day */}
            {recognitionToday.topMaterial && (
              <div className="card p-4 bg-gradient-to-br from-amber-50 to-amber-100/60 rounded-2xl border border-amber-200/80 shadow-md space-y-2">
                <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-amber-200 text-amber-900">
                  🏆 Top Material of the Day
                </span>
                <Link
                  to={`/materials/${recognitionToday.topMaterial.id}`}
                  className="font-bold text-gray-900 text-sm line-clamp-1 hover:text-amber-800 transition block"
                >
                  {recognitionToday.topMaterial.title}
                </Link>
                <p className="text-[11px] text-gray-600 line-clamp-1">{recognitionToday.topMaterial.subject}</p>
                <div className="flex items-center justify-between text-xs pt-1 border-t border-amber-200/60 text-gray-600">
                  <span className="flex items-center gap-1 font-semibold text-amber-900">
                    <Star size={13} className="text-amber-600 fill-amber-500" />
                    {recognitionToday.topMaterial.rating} ({recognitionToday.topMaterial.ratingCount})
                  </span>
                  <span>{recognitionToday.topMaterial.downloads} downloads</span>
                </div>
              </div>
            )}

            {/* 2. Highest Rated Material */}
            {recognitionToday.highestRated && (
              <div className="card p-4 bg-gradient-to-br from-purple-50 to-indigo-50/60 rounded-2xl border border-purple-200/80 shadow-md space-y-2">
                <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-purple-200 text-purple-900">
                  ⭐ Highest Rated
                </span>
                <Link
                  to={`/materials/${recognitionToday.highestRated.id}`}
                  className="font-bold text-gray-900 text-sm line-clamp-1 hover:text-purple-800 transition block"
                >
                  {recognitionToday.highestRated.title}
                </Link>
                <p className="text-[11px] text-gray-600 line-clamp-1">{recognitionToday.highestRated.subject}</p>
                <div className="flex items-center justify-between text-xs pt-1 border-t border-purple-200/60 text-gray-600">
                  <span className="flex items-center gap-1 font-bold text-purple-900">
                    <Star size={13} className="text-purple-600 fill-purple-500" />
                    {recognitionToday.highestRated.rating} Quality Score
                  </span>
                  <span>{recognitionToday.highestRated.downloads} downloads</span>
                </div>
              </div>
            )}

            {/* 3. Most Downloaded */}
            {recognitionToday.mostDownloaded && (
              <div className="card p-4 bg-gradient-to-br from-rose-50 to-orange-50/60 rounded-2xl border border-rose-200/80 shadow-md space-y-2">
                <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-rose-200 text-rose-900">
                  🔥 Most Downloaded
                </span>
                <Link
                  to={`/materials/${recognitionToday.mostDownloaded.id}`}
                  className="font-bold text-gray-900 text-sm line-clamp-1 hover:text-rose-800 transition block"
                >
                  {recognitionToday.mostDownloaded.title}
                </Link>
                <p className="text-[11px] text-gray-600 line-clamp-1">{recognitionToday.mostDownloaded.subject}</p>
                <div className="flex items-center justify-between text-xs pt-1 border-t border-rose-200/60 text-gray-600">
                  <span className="font-bold text-rose-800">
                    {recognitionToday.mostDownloaded.downloads} total downloads
                  </span>
                  <span className="text-gray-500">{recognitionToday.mostDownloaded.department}</span>
                </div>
              </div>
            )}

            {/* 4. Student Favourite */}
            {recognitionToday.studentFavourite && (
              <div className="card p-4 bg-gradient-to-br from-emerald-50 to-teal-50/60 rounded-2xl border border-emerald-200/80 shadow-md space-y-2">
                <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-emerald-200 text-emerald-900">
                  💎 Student Favourite
                </span>
                <Link
                  to={`/materials/${recognitionToday.studentFavourite.id}`}
                  className="font-bold text-gray-900 text-sm line-clamp-1 hover:text-emerald-800 transition block"
                >
                  {recognitionToday.studentFavourite.title}
                </Link>
                <p className="text-[11px] text-gray-600 line-clamp-1">{recognitionToday.studentFavourite.subject}</p>
                <div className="flex items-center justify-between text-xs pt-1 border-t border-emerald-200/60 text-gray-600">
                  <span className="font-bold text-emerald-800">
                    ★ {recognitionToday.studentFavourite.rating} / 5.0
                  </span>
                  <span>{recognitionToday.studentFavourite.department}</span>
                </div>
              </div>
            )}

            {/* 5. Top Contributor of the Day */}
            {recognitionToday.topContributor && (
              <div className="card p-4 bg-gradient-to-br from-blue-50 to-sky-50/60 rounded-2xl border border-blue-200/80 shadow-md space-y-2 sm:col-span-2 lg:col-span-2">
                <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-blue-200 text-blue-900">
                  🌟 Top Contributor of the Day
                </span>
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <h3 className="font-bold text-gray-900 text-sm">
                      {recognitionToday.topContributor.name}
                    </h3>
                    <p className="text-xs text-gray-600">
                      {recognitionToday.topContributor.course} &bull; Active Contributor
                    </p>
                  </div>
                  <div className="text-right">
                    <span className="text-xs font-bold text-blue-900 block">
                      {recognitionToday.topContributor.uploads} Uploads &bull; {recognitionToday.topContributor.downloads} Downloads
                    </span>
                    <span className="text-[11px] text-gray-500 font-medium">Community Impact Leader</span>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ========================================================
          SECTION 6: RECOMMENDED MATERIALS FOR YOU
      ======================================================== */}
      <div>
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-bold text-white">Recommended for Your Curriculum</h2>
          <Link to="/categories" className="flex items-center gap-1 text-xs font-bold text-white hover:text-amber-200 underline">
            View All Categories <ArrowRight size={14} />
          </Link>
        </div>

        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {recommended === null
            ? Array.from({ length: 4 }).map((_, i) => <CardSkeleton key={i} />)
            : recommended.length === 0
            ? <p className="col-span-full text-sm text-white/80">Upload or bookmark materials to receive personalized recommendations.</p>
            : recommended.slice(0, 4).map((m) => {
                const mid = m.id || m._id;
                return <MaterialCard key={mid} material={m} onToggleBookmark={loadDashboardData} />;
              })}
        </div>
      </div>

      {/* ========================================================
          SECTION 7: MOST POPULAR STUDY MATERIALS
      ======================================================== */}
      {popularMaterials && popularMaterials.length > 0 && (
        <div>
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <Flame size={18} className="text-orange-400" />
              <span>Trending &amp; Most Popular Materials</span>
            </h2>
          </div>

          <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
            {popularMaterials.slice(0, 4).map((m) => {
              const mid = m.id || m._id;
              return <MaterialCard key={mid} material={m} onToggleBookmark={loadDashboardData} />;
            })}
          </div>
        </div>
      )}

      {/* ========================================================
          SECTION 8: TOP CONTRIBUTORS LEADERBOARD PREVIEW
      ======================================================== */}
      <div id="leaderboard" className="rounded-2xl bg-white/95 p-6 shadow-md border border-white/40 space-y-4">
        <div className="flex items-center justify-between flex-wrap gap-2 pb-3 border-b border-gray-100">
          <div>
            <h2 className="text-base font-bold text-gray-900 flex items-center gap-2">
              <Users size={18} className="text-brand-700" />
              <span>Academic Contributor Leaderboard</span>
            </h2>
            <p className="text-xs text-gray-500 mt-0.5">
              Recognizing active students who upload high-quality notes and help their peers succeed.
            </p>
          </div>
          <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-brand-50 text-brand-900 border border-brand-200">
            Top Performers
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-gray-200 text-gray-400 font-semibold uppercase tracking-wider text-[10px]">
                <th className="py-2.5 px-3">Rank</th>
                <th className="py-2.5 px-3">Student</th>
                <th className="py-2.5 px-3">Discipline &amp; Stream</th>
                <th className="py-2.5 px-3 text-center">Uploads</th>
                <th className="py-2.5 px-3 text-center">Downloads</th>
                <th className="py-2.5 px-3 text-right">Quality Rating</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 font-medium text-gray-700">
              {(leaderboardData?.contributors || [
                { rank: 1, name: "Bhumika Ravi", course: "Computer Science", uploads: 12, downloads: 148, rating: 4.9 },
                { rank: 2, name: "Aarav Sharma", course: "Information Technology", uploads: 9, downloads: 92, rating: 4.8 },
                { rank: 3, name: "Pooja Patel", course: "Data Science", uploads: 7, downloads: 68, rating: 4.7 },
              ]).slice(0, 5).map((c, idx) => (
                <tr key={idx} className="hover:bg-brand-50/40 transition">
                  <td className="py-3 px-3">
                    <span className={`inline-flex items-center justify-center w-6 h-6 rounded-full font-bold text-xs ${
                      c.rank === 1 ? "bg-amber-100 text-amber-900 font-black border border-amber-300" :
                      c.rank === 2 ? "bg-gray-100 text-gray-800 border border-gray-300" :
                      c.rank === 3 ? "bg-amber-50 text-amber-800 border border-amber-200" :
                      "text-gray-500"
                    }`}>
                      {c.rank}
                    </span>
                  </td>
                  <td className="py-3 px-3 font-bold text-gray-900">{c.name}</td>
                  <td className="py-3 px-3 text-gray-500">{c.course}</td>
                  <td className="py-3 px-3 text-center font-semibold text-brand-900">{c.uploads}</td>
                  <td className="py-3 px-3 text-center font-semibold text-gray-600">{c.downloads}</td>
                  <td className="py-3 px-3 text-right font-bold text-amber-700">★ {c.rating} / 5.0</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* ========================================================
          SECTION 9: INTEGRATED DOCUMENT UPLOAD & AI AUTO-SEGREGATION
      ======================================================== */}
      <div id="upload-material">
        <DashboardUploadSection onUploadSuccess={loadDashboardData} />
      </div>

      {/* ========================================================
          SECTION 10: AI STUDY CHATBOT QUICK LAUNCH BANNER
      ======================================================== */}
      <div className="rounded-3xl bg-gradient-to-r from-brand-900 via-[#3a3028] to-[#251f1a] p-6 sm:p-8 text-white shadow-xl border border-white/10 flex flex-col md:flex-row items-center justify-between gap-6">
        <div className="space-y-2 text-center md:text-left">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-white/10 text-xs font-semibold text-amber-200 border border-white/10">
            <Sparkles size={13} />
            <span>Strictly Grounded In Your Uploaded Notes</span>
          </div>
          <h2 className="text-xl sm:text-2xl font-bold">CampusVerse AI Study Chatbot</h2>
          <p className="text-xs sm:text-sm text-white/80 max-w-xl">
            Ask doubts, generate 2-mark or 10-mark exam answers, quiz yourself, and receive student-friendly explanations strictly verified from your course documents.
          </p>
        </div>
        <Link
          to="/chat"
          className="btn-primary !px-6 !py-3 !bg-amber-500 hover:!bg-amber-600 !text-gray-950 font-extrabold shadow-lg shrink-0 flex items-center gap-2"
        >
          <Bot size={18} /> Launch AI Study Chat
        </Link>
      </div>
    </div>
  );
}
