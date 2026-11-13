import { Routes, Route, Navigate } from "react-router-dom";
import Layout from "./components/Layout";
import ProtectedRoute from "./components/ProtectedRoute";

import Home from "./pages/Home";
import Login from "./pages/Login";
import Register from "./pages/Register";
import MaterialDetails from "./pages/MaterialDetails";
import Dashboard from "./pages/Dashboard";
import Upload from "./pages/Upload";
import MyUploads from "./pages/MyUploads";
import Bookmarks from "./pages/Bookmarks";
import DownloadHistory from "./pages/DownloadHistory";
import Profile from "./pages/Profile";
import Categories from "./pages/Categories";
import StudyBuddy from "./pages/StudyBuddy";
import ScanningBooth from "./pages/ScanningBooth";
import AdminDashboard from "./pages/AdminDashboard";
import AdminLogin from "./pages/AdminLogin";
import SemanticSearch from "./pages/SemanticSearch";
import ChatWithNotes from "./pages/ChatWithNotes";
import NotFound from "./pages/NotFound";
import ErrorBoundary from "./components/ErrorBoundary";

export default function App() {
  return (
    <ErrorBoundary>
      <Routes>
      {/* Auth routes without global navbar/footer */}
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/admin/login" element={<AdminLogin />} />

      <Route element={<Layout />}>
        <Route path="/" element={<Home />} />
        <Route path="/categories" element={<Categories />} />
        <Route path="/search" element={<SemanticSearch />} />
        <Route
          path="/chat"
          element={
            <ProtectedRoute>
              <ChatWithNotes />
            </ProtectedRoute>
          }
        />
        <Route path="/study-buddy" element={<Navigate to="/chat" replace />} />
        <Route path="/scanning-booth" element={<Navigate to="/dashboard" replace />} />
        <Route path="/materials/:id" element={<MaterialDetails />} />

        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <Dashboard />
            </ProtectedRoute>
          }
        />
        <Route
          path="/upload"
          element={
            <ProtectedRoute>
              <Upload />
            </ProtectedRoute>
          }
        />
        <Route
          path="/my-uploads"
          element={
            <ProtectedRoute>
              <MyUploads />
            </ProtectedRoute>
          }
        />
        <Route
          path="/bookmarks"
          element={
            <ProtectedRoute>
              <Bookmarks />
            </ProtectedRoute>
          }
        />
        <Route
          path="/downloads"
          element={
            <ProtectedRoute>
              <DownloadHistory />
            </ProtectedRoute>
          }
        />
        <Route
          path="/profile"
          element={
            <ProtectedRoute>
              <Profile />
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin"
          element={
            <ProtectedRoute adminOnly>
              <AdminDashboard />
            </ProtectedRoute>
          }
        />

        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
    </ErrorBoundary>
  );
}