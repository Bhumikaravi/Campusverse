import { useState } from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import { Eye, EyeOff, BookOpen, ArrowLeft, AlertCircle, ShieldCheck } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";

export default function Login() {
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [remember, setRemember] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const { login } = useAuth();
  const { showToast } = useToast();
  const navigate = useNavigate();
  const location = useLocation();
  const from = location.state?.from?.pathname || "/dashboard";

  const handleSubmit = async (e) => {
    e.preventDefault();
    const cleanId = identifier.trim();

    if (!cleanId || !password) {
      setError("Please enter your email/username and password.");
      return;
    }

    setError("");
    setLoading(true);

    try {
      await login(cleanId, password);
      showToast("Welcome back to CampusVerse!", "success");
      navigate(from, { replace: true });
    } catch (err) {
      let serverError = "Invalid email/username or password. Please try again.";
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
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-brand-950 p-4">
      <div
        className="absolute inset-0 bg-cover bg-center bg-no-repeat"
        style={{ backgroundImage: "url('/login-wallpaper.jpg')" }}
      />
      <div className="absolute inset-0 bg-black/25 backdrop-blur-[1px]" />

      <div className="relative z-10 grid w-full max-w-4xl overflow-hidden rounded-3xl border border-white/50 bg-white/10 shadow-2xl backdrop-blur-2xl md:grid-cols-2">
        <div className="flex flex-col items-center justify-center gap-10 border-b border-white/30 p-8 text-center text-white md:border-b-0 md:border-r">
          <div className="flex items-center gap-2">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-white/85 text-brand-900">
              <BookOpen size={20} />
            </div>
            <span className="font-display text-xl font-bold">CampusVerse</span>
          </div>

          <div className="max-w-xs">
            <h2 className="font-display text-3xl font-bold leading-tight drop-shadow">
              "Your campus. Your knowledge. One place.."
            </h2>
            <p className="mt-4 text-sm text-white/90 drop-shadow">
              Discover study materials and share what you know with fellow students.
            </p>
          </div>
        </div>

        <div className="flex items-center justify-center bg-white/55 p-8 backdrop-blur-xl dark:bg-gray-950/55 sm:p-10">
          <div className="w-full max-w-sm">
            <Link
              to="/"
              className="mb-6 flex items-center justify-center gap-1 text-sm font-medium text-gray-600 hover:text-gray-900 dark:text-gray-300 dark:hover:text-white"
            >
              <ArrowLeft size={14} /> Back to CampusVerse
            </Link>

            <div className="mb-6 text-center">
              <h1 className="font-display text-3xl font-bold text-gray-900 dark:text-white">Welcome back</h1>
              <p className="mt-1 text-sm text-gray-600 dark:text-gray-300">
                Log in to access your study materials.
              </p>
            </div>

            <form onSubmit={handleSubmit} noValidate className="space-y-4">
              <div>
                <label htmlFor="identifier" className="mb-1.5 block text-xs font-semibold text-gray-700 dark:text-gray-200">
                  Email address or Username
                </label>
                <input
                  id="identifier"
                  type="text"
                  placeholder="e.g. you@college.edu or bhumikaravi"
                  value={identifier}
                  onChange={(e) => {
                    setIdentifier(e.target.value);
                    if (error) setError("");
                  }}
                  className="input-field"
                  disabled={loading}
                  required
                />
              </div>

              <div>
                <label htmlFor="password" className="mb-1.5 block text-xs font-semibold text-gray-700 dark:text-gray-200">
                  Password
                </label>
                <div className="relative">
                  <input
                    id="password"
                    type={showPassword ? "text" : "password"}
                    placeholder="••••••••"
                    value={password}
                    onChange={(e) => {
                      setPassword(e.target.value);
                      if (error) setError("");
                    }}
                    className="input-field pr-11"
                    disabled={loading}
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((s) => !s)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                    tabIndex={-1}
                  >
                    {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
              </div>

              {error && (
                <div className="flex items-center gap-1.5 text-xs font-medium text-red-600 bg-red-50 p-2.5 rounded-lg border border-red-200">
                  <AlertCircle size={14} className="shrink-0 text-red-500" />
                  <span>{error}</span>
                </div>
              )}

              <div className="flex items-center justify-between pt-1">
                <label className="flex items-center gap-2 text-xs text-gray-700 dark:text-gray-300">
                  <input
                    type="checkbox"
                    checked={remember}
                    onChange={(e) => setRemember(e.target.checked)}
                    className="h-3.5 w-3.5 accent-brand-700"
                  />
                  Remember me
                </label>
                <Link to="/forgot-password" className="text-xs font-semibold text-brand-700 hover:underline dark:text-brand-300">
                  Forgot password?
                </Link>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="btn-primary w-full !py-3 flex items-center justify-center gap-2 disabled:opacity-60 disabled:cursor-not-allowed"
              >
                {loading ? "Logging in..." : "Login"}
              </button>
            </form>

            <p className="mt-5 text-center text-xs text-gray-600 dark:text-gray-300">
              Don't have an account?{" "}
              <Link to="/register" className="font-semibold text-brand-700 hover:underline dark:text-brand-300">
                Create an account
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}