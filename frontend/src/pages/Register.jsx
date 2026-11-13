import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Eye, EyeOff, BookOpen, ArrowLeft, AlertCircle } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";

export default function Register() {
  const [form, setForm] = useState({
    name: "",
    email: "",
    department: "",
    password: "",
    confirmPassword: "",
  });
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const { register } = useAuth();
  const { showToast } = useToast();
  const navigate = useNavigate();

  const update = (key) => (e) => {
    setForm((f) => ({ ...f, [key]: e.target.value }));
    if (error) setError("");
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    const cleanName = form.name.trim();
    const cleanEmail = form.email.trim().toLowerCase();

    if (!cleanName || !cleanEmail || !form.password) {
      setError("Please fill in all required fields.");
      return;
    }

    if (cleanName.length < 2) {
      setError("Full name must be at least 2 characters long.");
      return;
    }

    // Basic email regex format check
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(cleanEmail)) {
      setError("Please enter a valid email address.");
      return;
    }

    if (form.password.length < 6) {
      setError("Password must be at least 6 characters long.");
      return;
    }

    if (form.password !== form.confirmPassword) {
      setError("Passwords do not match. Please re-check both fields.");
      return;
    }

    setError("");
    setLoading(true);

    try {
      await register({
        full_name: cleanName,
        name: cleanName,
        email: cleanEmail,
        department: form.department.trim(),
        password: form.password,
        confirm_password: form.confirmPassword,
      });

      showToast("Account created successfully — welcome to CampusVerse!", "success");
      navigate("/dashboard");
    } catch (err) {
      let serverError = "Could not create your account. Please try again.";
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
        className="absolute inset-0 scale-110 bg-cover bg-center blur-md"
        style={{ backgroundImage: "url('/image_1.jpg')" }}
      />
      <div className="absolute inset-0 bg-black/20" />

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
              Join thousands of students already sharing notes.
            </h2>
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
              <h1 className="font-display text-3xl font-bold text-gray-900 dark:text-white">Create your account</h1>
              <p className="mt-1 text-sm text-gray-600 dark:text-gray-300">
                Start exploring and sharing study materials.
              </p>
            </div>

            <form onSubmit={handleSubmit} noValidate className="space-y-3.5">
              <div>
                <label className="mb-1.5 block text-xs font-semibold text-gray-700 dark:text-gray-200">
                  Full name *
                </label>
                <input
                  value={form.name}
                  onChange={update("name")}
                  placeholder="e.g. Bhumika Ravi"
                  className="input-field"
                  disabled={loading}
                  required
                />
              </div>

              <div>
                <label className="mb-1.5 block text-xs font-semibold text-gray-700 dark:text-gray-200">
                  Email address *
                </label>
                <input
                  type="email"
                  value={form.email}
                  onChange={update("email")}
                  placeholder="you@college.edu"
                  className="input-field"
                  disabled={loading}
                  required
                />
              </div>

              <div>
                <label className="mb-1.5 block text-xs font-semibold text-gray-700 dark:text-gray-200">
                  Department
                </label>
                <input
                  value={form.department}
                  onChange={update("department")}
                  placeholder="e.g. Computer Science"
                  className="input-field"
                  disabled={loading}
                />
              </div>

              <div>
                <label className="mb-1.5 block text-xs font-semibold text-gray-700 dark:text-gray-200">
                  Password *
                </label>
                <div className="relative">
                  <input
                    type={showPassword ? "text" : "password"}
                    value={form.password}
                    onChange={update("password")}
                    placeholder="At least 6 characters"
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

              <div>
                <label className="mb-1.5 block text-xs font-semibold text-gray-700 dark:text-gray-200">
                  Confirm password *
                </label>
                <input
                  type={showPassword ? "text" : "password"}
                  value={form.confirmPassword}
                  onChange={update("confirmPassword")}
                  placeholder="Re-enter your password"
                  className="input-field"
                  disabled={loading}
                  required
                />
              </div>

              {error && (
                <div className="flex items-center gap-1.5 text-xs font-medium text-red-600 bg-red-50 p-2.5 rounded-lg border border-red-200">
                  <AlertCircle size={14} className="shrink-0 text-red-500" />
                  <span>{error}</span>
                </div>
              )}

              <button
                type="submit"
                disabled={loading}
                className="btn-primary w-full !py-3 flex items-center justify-center gap-2 disabled:opacity-60 disabled:cursor-not-allowed"
              >
                {loading ? "Creating account..." : "Create account"}
              </button>
            </form>

            <p className="mt-6 text-center text-xs text-gray-600 dark:text-gray-300">
              Already have an account?{" "}
              <Link to="/login" className="font-semibold text-brand-700 hover:underline dark:text-brand-300">
                Log in
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}