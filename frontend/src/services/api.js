import axios from "axios";

// Configurable API Base URL pointing to Supabase Edge Functions
const supabaseBase = import.meta.env.VITE_SUPABASE_URL
  ? `${import.meta.env.VITE_SUPABASE_URL.replace(/\/+$/, "")}/functions/v1/api`
  : null;

let rawBase =
  import.meta.env.VITE_API_BASE_URL ||
  import.meta.env.VITE_API_URL ||
  supabaseBase ||
  "https://eeklurlqjcdcspmjlwlc.supabase.co/functions/v1/api";

rawBase = String(rawBase).trim().replace(/\/+$/, "");

const api = axios.create({
  baseURL: rawBase,
  timeout: 6000, // 6-second timeout so page never hangs
  headers: { "Content-Type": "application/json" },
  withCredentials: false,
});

// Attach the Supabase auth token and apikey to every request automatically
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("cv-token");
  const anonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;

  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  } else if (anonKey) {
    config.headers.Authorization = `Bearer ${anonKey}`;
  }

  if (anonKey) {
    config.headers["apikey"] = anonKey;
  }

  return config;
});

// Centralized handling for expired/invalid sessions on protected endpoints
api.interceptors.response.use(
  (res) => res,
  (error) => {
    const url = error.config?.url || "";
    const isAuthEndpoint = url.includes("/auth/login") || url.includes("/auth/register");

    if (error.response?.status === 401 && !isAuthEndpoint) {
      localStorage.removeItem("cv-token");
      localStorage.removeItem("cv-user");
      if (window.location.pathname !== "/login" && window.location.pathname !== "/register") {
        window.location.href = "/login";
      }
    }

    // Attach user-friendly errorMessage property for components
    let friendlyMessage = "An unexpected error occurred. Please try again.";
    if (!error.response || error.code === "ERR_NETWORK" || error.code === "ECONNABORTED") {
      friendlyMessage = "Cannot connect to server. Please check your internet connection or verify the backend server is running.";
    } else if (error.response?.data?.detail) {
      friendlyMessage = error.response.data.detail;
    } else if (error.response?.data?.error) {
      friendlyMessage = error.response.data.error;
    } else if (error.response?.status === 403) {
      friendlyMessage = "Access forbidden. You do not have permission to perform this action.";
    } else if (error.response?.status >= 500) {
      friendlyMessage = "Server error occurred. Please try again later.";
    }

    error.errorMessage = friendlyMessage;
    return Promise.reject(error);
  }
);

export default api;
