import axios from "axios";

// Configurable API Base URL
// In production, fallback to relative "/api" so requests go to the same origin if no external URL is set
let rawBase = import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_URL;

if (!rawBase || rawBase.includes("localhost:5000")) {
  if (typeof window !== "undefined" && window.location.hostname !== "localhost" && window.location.hostname !== "127.0.0.1") {
    // We are on a deployed public URL (e.g. Railway or Render) -> use relative /api
    rawBase = "/api";
  } else {
    rawBase = "http://localhost:5000/api";
  }
}

rawBase = String(rawBase).trim().replace(/\/+$/, "");
if ((rawBase.startsWith("http://") || rawBase.startsWith("https://")) && !rawBase.endsWith("/api")) {
  rawBase = `${rawBase}/api`;
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
      friendlyMessage = error.response.data.detail;
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
