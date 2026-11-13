import axios from "axios";

// Configurable API Base URL (supports VITE_API_BASE_URL, VITE_API_URL, or relative /api via Vite proxy)
let rawBase =
  import.meta.env.VITE_API_BASE_URL ||
  import.meta.env.VITE_API_URL ||
  "/api";

rawBase = String(rawBase).trim().replace(/\/+$/, "");

// If an absolute backend URL was provided (e.g. https://campusverse-api.onrender.com) without /api, append /api
if (rawBase.startsWith("http://") || rawBase.startsWith("https://")) {
  if (!rawBase.endsWith("/api")) {
    rawBase = `${rawBase}/api`;
  }
}

const api = axios.create({
  baseURL: rawBase,
  headers: { "Content-Type": "application/json" },
  withCredentials: true,
});

// Attach the auth token to every request automatically
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("cv-token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
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
    if (!error.response || error.code === "ERR_NETWORK") {
      friendlyMessage = "Cannot connect to server. Please check your internet connection or verify the backend server is running.";
    } else if (error.response?.data?.detail) {
      friendlyMessage = typeof error.response.data.detail === "string"
        ? error.response.data.detail
        : JSON.stringify(error.response.data.detail);
    } else if (error.response?.status === 404) {
      friendlyMessage = "Requested resource was not found.";
    } else if (error.response?.status === 403) {
      friendlyMessage = "You do not have permission to perform this action.";
    } else if (error.response?.status >= 500) {
      friendlyMessage = "Internal server error. Please try again shortly.";
    }
    error.friendlyMessage = friendlyMessage;

    return Promise.reject(error);
  }
);

export default api;
