import { useState } from "react";
import { Link, NavLink, useNavigate } from "react-router-dom";
import {
  BookOpen,
  Menu,
  X,
  LayoutDashboard,
  Upload,
  Bookmark,
  User,
  LogOut,
  ShieldCheck,
  Bot,
  Search,
  MessageSquare,
  Sparkles,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";

const navLinks = [
  { to: "/categories", label: "Categories" },
  { to: "/search", label: "AI Search" },
  { to: "/chat", label: "Chat With Notes" },
];

export default function Navbar() {
  const [open, setOpen] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const { user, logout, isAdmin } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    setMenuOpen(false);
    navigate("/");
  };

  const linkClass = ({ isActive }) =>
    `text-sm font-medium transition hover:text-white ${
      isActive ? "text-white font-bold" : "text-white/80"
    }`;

  return (
    <header className="sticky top-0 z-40 border-b border-white/20 bg-[#3e362e]/95 backdrop-blur text-white shadow-md">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3 sm:px-6">
        <Link to="/" className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#93785b] text-white shadow-sm">
            <BookOpen size={17} />
          </div>
          <span className="font-display text-lg font-bold text-white">CampusVerse</span>
        </Link>

        <nav className="hidden items-center gap-6 md:flex">
          {navLinks.map((l) => (
            <NavLink key={l.to} to={l.to} className={linkClass}>
              {l.label}
            </NavLink>
          ))}
          {user && (
            <NavLink to="/dashboard" className={linkClass}>
              Dashboard
            </NavLink>
          )}
          {isAdmin && (
            <NavLink to="/admin" className={linkClass}>
              Admin
            </NavLink>
          )}
        </nav>

        <div className="flex items-center gap-2">
          {user ? (
            <div className="relative hidden md:block">
              <button
                onClick={() => setMenuOpen((o) => !o)}
                className="flex items-center gap-2 rounded-full border border-white/30 bg-white/10 py-1 pl-1 pr-3 hover:bg-white/20 shadow-sm text-white"
              >
                <div className="flex h-7 w-7 items-center justify-center rounded-full bg-white text-xs font-bold text-[#3e362e]">
                  {user.name?.[0]?.toUpperCase() || "U"}
                </div>
                <span className="text-sm font-medium text-white">{user.name?.split(" ")[0]}</span>
              </button>

              {menuOpen && (
                <div className="card animate-scale-in absolute right-0 mt-2 w-52 overflow-hidden p-1.5 shadow-xl bg-white text-gray-900 border border-brand-200">
                  <Link onClick={() => setMenuOpen(false)} to="/dashboard" className="menu-item">
                    <LayoutDashboard size={16} /> Dashboard
                  </Link>
                  <Link onClick={() => setMenuOpen(false)} to="/upload" className="menu-item">
                    <Upload size={16} /> Upload Material
                  </Link>
                  <Link onClick={() => setMenuOpen(false)} to="/chat" className="menu-item">
                    <MessageSquare size={16} /> Chat With Notes
                  </Link>
                  <Link onClick={() => setMenuOpen(false)} to="/search" className="menu-item">
                    <Search size={16} /> Semantic Search
                  </Link>
                  <Link onClick={() => setMenuOpen(false)} to="/bookmarks" className="menu-item">
                    <Bookmark size={16} /> Bookmarks
                  </Link>
                  <Link onClick={() => setMenuOpen(false)} to="/profile" className="menu-item">
                    <User size={16} /> Profile
                  </Link>
                  {isAdmin && (
                    <Link onClick={() => setMenuOpen(false)} to="/admin" className="menu-item">
                      <ShieldCheck size={16} /> Admin Panel
                    </Link>
                  )}
                  <button onClick={handleLogout} className="menu-item w-full text-red-600 hover:bg-red-50">
                    <LogOut size={16} /> Logout
                  </button>
                </div>
              )}
            </div>
          ) : (
            <div className="hidden items-center gap-2 md:flex">
              <Link to="/login" className="btn-secondary !bg-white/10 !text-white !border-white/30 hover:!bg-white/20 !px-4 !py-2">
                Log in
              </Link>
              <Link to="/register" className="btn-primary !bg-[#93785b] hover:!bg-[#865d36] !text-white !border-none !px-4 !py-2 shadow-sm">
                Sign up
              </Link>
            </div>
          )}

          <button
            onClick={() => setOpen((o) => !o)}
            className="rounded-lg p-2 text-white hover:bg-white/10 md:hidden"
          >
            {open ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>
      </div>

      {/* Mobile menu */}
      {open && (
        <div className="animate-fade-in space-y-1 border-t border-white/20 bg-[#3e362e] px-4 py-3 md:hidden">
          {navLinks.map((l) => (
            <Link key={l.to} to={l.to} onClick={() => setOpen(false)} className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-white/90 hover:bg-white/10">
              {l.label}
            </Link>
          ))}
          {user ? (
            <>
              <Link to="/dashboard" onClick={() => setOpen(false)} className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-white/90 hover:bg-white/10">
                Dashboard
              </Link>
              <Link to="/upload" onClick={() => setOpen(false)} className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-white/90 hover:bg-white/10">
                Upload Material
              </Link>
              <Link to="/bookmarks" onClick={() => setOpen(false)} className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-white/90 hover:bg-white/10">
                Bookmarks
              </Link>
              <Link to="/profile" onClick={() => setOpen(false)} className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-white/90 hover:bg-white/10">
                Profile
              </Link>
              {isAdmin && (
                <Link to="/admin" onClick={() => setOpen(false)} className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-white/90 hover:bg-white/10">
                  Admin Panel
                </Link>
              )}
              <button onClick={handleLogout} className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-red-400 hover:bg-white/10 w-full">
                Logout
              </button>
            </>
          ) : (
            <div className="flex gap-2 pt-2">
              <Link to="/login" onClick={() => setOpen(false)} className="btn-secondary !bg-white/10 !text-white !border-white/30 flex-1">
                Log in
              </Link>
              <Link to="/register" onClick={() => setOpen(false)} className="btn-primary !bg-[#93785b] flex-1">
                Sign up
              </Link>
            </div>
          )}
        </div>
      )}
    </header>
  );
}
