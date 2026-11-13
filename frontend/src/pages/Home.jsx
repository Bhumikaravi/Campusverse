import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, BookOpen, Upload, Star, TrendingUp, Sparkles, Bot } from "lucide-react";
import SearchBar from "../components/SearchBar";
import MaterialCard from "../components/MaterialCard";
import { CardSkeleton } from "../components/Loader";
import { materialsApi } from "../services/endpoints";
import { useNavigate } from "react-router-dom";

export default function Home() {
  const navigate = useNavigate();
  const [popular, setPopular] = useState(null);
  const [recent, setRecent] = useState(null);
  const [stats, setStats] = useState([
    { label: "Study materials", value: "0" },
    { label: "Active students", value: "0" },
    { label: "Departments", value: "0" },
    { label: "Avg. rating", value: "0" },
  ]);

  useEffect(() => {
    materialsApi
      .popular()
      .then((res) => setPopular(res.data.materials))
      .catch(() => setPopular([]));
    materialsApi
      .recent()
      .then((res) => setRecent(res.data.materials))
      .catch(() => setRecent([]));
    materialsApi
      .stats()
      .then((res) => {
        const d = res.data || {};
        setStats([
          { label: "Study materials", value: String(d.studyMaterials ?? d.totalMaterials ?? 0) },
          { label: "Active students", value: "0" },
          { label: "Departments", value: String(d.departments ?? 0) },
          { label: "Avg. rating", value: "0" },
        ]);
      })
      .catch(() => {});
  }, []);

  const handleSearch = (q) => {
    if (q.trim()) navigate(`/categories?q=${encodeURIComponent(q)}`);
  };

  return (
    <div>
      {/* HERO */}
      <section className="relative overflow-hidden py-16 sm:py-24">
        <div className="relative z-10">
          <div className="mx-auto max-w-5xl px-4 text-center sm:px-6">
            <span className="mb-4 inline-block rounded-full bg-white/20 border border-white/30 px-3.5 py-1 text-xs font-semibold text-white backdrop-blur">
              Built by students, for students
            </span>
            <h1 className="font-display text-4xl font-bold leading-tight text-white sm:text-5xl md:text-6xl drop-shadow-sm">
              Learn. Share.
              <br />
              <span className="text-white/90">Grow together.</span>
            </h1>
            <p className="mx-auto mt-5 max-w-xl text-white/90 drop-shadow-sm">
              CampusVerse is where students discover, upload and rate notes, past
              papers and study guides across every department and semester.
            </p>

            <div className="mx-auto mt-8 max-w-xl">
              <SearchBar onChange={handleSearch} placeholder="Search for 'Data Structures notes'..." />
            </div>

            <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
              <Link to="/categories" className="btn-primary !bg-[#3e362e] hover:!bg-[#2a241e] !text-white shadow-md">
                Browse Categories <ArrowRight size={16} />
              </Link>
              <Link to="/dashboard" className="btn-secondary !bg-white/20 !text-white !border-white/40 hover:!bg-white/30 backdrop-blur">
                <Upload size={16} /> Upload on Dashboard
              </Link>
            </div>
          </div>

          <div className="mx-auto grid max-w-4xl grid-cols-2 gap-4 px-4 pt-12 sm:px-6 md:grid-cols-4">
            {stats.map((s) => (
              <div key={s.label} className="rounded-xl bg-white/20 border border-white/30 p-4 text-center backdrop-blur shadow-sm">
                <p className="font-display text-2xl font-bold text-white">{s.value}</p>
                <p className="text-xs text-white/80">{s.label}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* POPULAR MATERIALS */}
      <section className="mx-auto max-w-7xl px-4 py-14 sm:px-6">
        <div className="mb-6 flex items-center justify-between">
          <h2 className="flex items-center gap-2 text-xl font-bold text-white">
            <TrendingUp size={20} className="text-white" /> Popular this week
          </h2>
          <Link to="/categories" className="text-sm font-medium text-white/90 hover:text-white underline">
            View categories
          </Link>
        </div>

        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {popular === null
            ? Array.from({ length: 4 }).map((_, i) => <CardSkeleton key={i} />)
            : popular.length === 0
              ? (
                <p className="col-span-full text-sm text-white/80">
                  No materials yet — connect the backend to populate this section.
                </p>
              )
              : popular.map((m) => <MaterialCard key={m.id} material={m} />)}
        </div>
      </section>

      {/* RECENTLY ADDED */}
      <section className="mx-auto max-w-7xl px-4 pb-16 sm:px-6">
        <div className="mb-6 flex items-center justify-between">
          <h2 className="flex items-center gap-2 text-xl font-bold text-white">
            <Star size={20} className="text-white" /> Recently added
          </h2>
          <Link to="/categories" className="text-sm font-medium text-white/90 hover:text-white underline">
            View categories
          </Link>
        </div>

        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {recent === null
            ? Array.from({ length: 4 }).map((_, i) => <CardSkeleton key={i} />)
            : recent.length === 0
              ? (
                <p className="col-span-full text-sm text-white/80">
                  No materials yet — connect the backend to populate this section.
                </p>
              )
              : recent.map((m) => <MaterialCard key={m.id} material={m} />)}
        </div>
      </section>

      {/* CTA */}
      <section className="border-t border-black/20 bg-[#3e362e] py-16 text-center text-white">
        <BookOpen size={32} className="mx-auto mb-4 text-[#93785b]" />
        <h2 className="font-display text-2xl font-bold sm:text-3xl">Got notes worth sharing?</h2>
        <p className="mx-auto mt-2 max-w-md text-white/80">
          Upload your study material and help thousands of students on CampusVerse.
        </p>
        <Link to="/upload" className="btn-primary mt-6 inline-flex !bg-[#93785b] hover:!bg-[#865d36] !text-white shadow-md">
          Upload material <ArrowRight size={16} />
        </Link>
      </section>
    </div>
  );
}