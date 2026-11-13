import { useState } from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import { ShieldCheck, Eye, EyeOff, ArrowLeft, AlertCircle, KeyRound, Lock } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import api from "../services/api";

export default function AdminLogin() {
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const { setUser } = useAuth();
  const { showToast } = useToast();
  const navigate = useNavigate();
  const location = useLocation();
  const from = location.state?.from?.pathname || "/admin";

  const handleFillDemoAdmin = () => {
    setIdentifier("admin@campusverse.edu");
    setPassword("Admin@123");
    setError("");
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const cleanId = identifier.trim();

    if (!cleanId || !password) {
      setError("Please enter your administrator email and password.");
      return;
    }

    setError("");
    setLoading(true);

    try {
      const res = await api.post("/auth/admin-login", {
        email: cleanId,
        password: password,
      });

      const { token, user: adminUser } = res.data;
      if (token) localStorage.setItem("cv-token", token);
      if (adminUser) {
        localStorage.setItem("cv-user", JSON.stringify(adminUser));
        setUser(adminUser);
      }

      showToast(`Welcome back, ${adminUser?.name || "Administrator"}!`, "success");
      navigate(from, { replace: true });
    } catch (err) {
      let serverError = "Invalid administrator credentials. Please check your login details.";
      if (err.response?.data) {
        const d = err.response.data;
        if (typeof d.detail === "string") {
          serverError = d.detail;
        } else if (Array.isArray(d.detail)) {
          serverError = d.detail.map((item) => item.msg || item.message).join(", ");
        } else if (d.message) {
          serverError = d.message;
        }
      } else if (err.code === "ERR_NETWORK" || !err.response) {
        serverError = "Cannot connect to backend server. Please verify FastAPI is running on http://localhost:5000.";
      }
      setError(serverError);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-slate-950 p-4">
      {/* Background with Dark Architectural Feel */}
      <div
        className="absolute inset-0 bg-cover bg-center opacity-25 filter blur-xs"
        style={{ backgroundImage: "url('/image_1.jpg')" }}
      />
      <div className="absolute inset-0 bg-gradient-to-tr from-slate-950 via-slate-900/90 to-amber-950/30" />

      <div className="relative z-10 w-full max-w-md overflow-hidden rounded-3xl border border-amber-500/20 bg-slate-900/85 p-8 shadow-2xl backdrop-blur-2xl sm:p-10 text-white">
        {/* Navigation Link */}
        <Link
          to="/login"
          className="mb-6 flex items-center justify-center gap-1.5 text-xs font-medium text-slate-400 hover:text-white transition"
        >
          <ArrowLeft size={14} /> Back to Student Login
        </Link>

        {/* Header */}
        <div className="mb-6 text-center">
          <div className="mx-auto mb-3 flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-amber-500 to-amber-700 text-slate-950 shadow-lg shadow-amber-500/20">
            <ShieldCheck size={28} />
          </div>
          <span className="inline-block rounded-full border border-amber-500/30 bg-amber-500/10 px-3 py-1 text-[11px] font-semibold tracking-wide text-amber-300">
            Administrator Portal
          </span>
          <h1 className="mt-3 font-display text-2xl font-bold tracking-tight text-white">
            Moderator Access
          </h1>
          <p className="mt-1 text-xs text-slate-400">
            Review, approve, and manage academic study materials.
          </p>
        </div>

        {/* Demo Quick-Fill Pill */}
        <div className="mb-5 rounded-xl border border-amber-500/25 bg-amber-500/10 p-3 text-xs text-amber-200">
          <div className="flex items-center justify-between">
            <span className="font-semibold flex items-center gap-1 text-amber-300">
              <KeyRound size={13} /> Default Admin
            </span>
            <button
              type="button"
              onClick={handleFillDemoAdmin}
              className="rounded bg-amber-500/20 px-2 py-0.5 text-[11px] font-bold text-amber-300 hover:bg-amber-500/40 transition"
            >
              Fill Credentials
            </button>
          </div>
          <p className="mt-1 font-mono text-[11px] text-amber-100/90">
            admin@campusverse.edu / Admin@123
          </p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} noValidate className="space-y-4">
          <div>
            <label className="mb-1.5 block text-xs font-semibold text-slate-300">
              Admin Email or Username
            </label>
            <input
              type="text"
              placeholder="admin@campusverse.edu"
              value={identifier}
              onChange={(e) => {
                setIdentifier(e.target.value);
                if (error) setError("");
              }}
              className="w-full rounded-xl border border-slate-700 bg-slate-800/80 px-4 py-2.5 text-sm text-white placeholder-slate-500 focus:border-amber-500 focus:outline-none focus:ring-1 focus:ring-amber-500 transition"
              disabled={loading}
              required
            />
          </div>

          <div>
            <label className="mb-1.5 block text-xs font-semibold text-slate-300">
              Password
            </label>
            <div className="relative">
              <input
                type={showPassword ? "text" : "password"}
                placeholder="••••••••••••"
                value={password}
                onChange={(e) => {
                  setPassword(e.target.value);
                  if (error) setError("");
                }}
                className="w-full rounded-xl border border-slate-700 bg-slate-800/80 px-4 py-2.5 pr-11 text-sm text-white placeholder-slate-500 focus:border-amber-500 focus:outline-none focus:ring-1 focus:ring-amber-500 transition"
                disabled={loading}
                required
              />
              <button
                type="button"
                onClick={() => setShowPassword((s) => !s)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white"
                tabIndex={-1}
              >
                {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </div>

          {error && (
            <div className="flex items-center gap-2 rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-xs text-red-300">
              <AlertCircle size={15} className="shrink-0 text-red-400" />
              <span>{error}</span>
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-xl bg-gradient-to-r from-amber-500 to-amber-600 py-3 text-sm font-bold text-slate-950 shadow-lg shadow-amber-500/25 hover:from-amber-400 hover:to-amber-500 focus:outline-none focus:ring-2 focus:ring-amber-500 disabled:cursor-not-allowed disabled:opacity-60 transition"
          >
            {loading ? "Authenticating Admin..." : "Log in to Admin Dashboard"}
          </button>
        </form>

        <div className="mt-6 border-t border-slate-800 pt-4 text-center">
          <p className="text-[11px] text-slate-400 flex items-center justify-center gap-1">
            <Lock size={12} className="text-amber-400" /> Secured with Argon2 encryption & role-based access
          </p>
        </div>
      </div>
    </div>
  );
}
