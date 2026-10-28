import React from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { ThemeProvider } from "./context/ThemeContext";
import { AuthProvider } from "./context/AuthContext";

import ProtectedRoute from "./components/common/ProtectedRoute";
import AdminRoute from "./components/common/AdminRoute";

import LandingPage from "./pages/LandingPage";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import ForbiddenPage from "./pages/ForbiddenPage";

import DashboardLayout from "./layouts/DashboardLayout";
import ControlCenterPage from "./pages/dashboard/ControlCenterPage";
import VoiceControlPage from "./pages/dashboard/VoiceControlPage";
import VoiceMacrosPage from "./pages/dashboard/VoiceMacrosPage";
import AuditLogsPage from "./pages/dashboard/AuditLogsPage";
import ChatMemoryPage from "./pages/dashboard/ChatMemoryPage";
import SettingsPage from "./pages/dashboard/SettingsPage";

import AdminLayout from "./layouts/AdminLayout";
import AdminDashboardPage from "./pages/admin/AdminDashboardPage";
import AdminUsersPage from "./pages/admin/AdminUsersPage";
import AdminUserDetailPage from "./pages/admin/AdminUserDetailPage";

export default function App() {
  return (
    <BrowserRouter>
      <ThemeProvider>
        <AuthProvider>
          <Routes>
            {/* Public Routes */}
            <Route path="/" element={<LandingPage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route path="/403" element={<ForbiddenPage />} />

            {/* Authenticated Dashboard Routes */}
            <Route
              path="/dashboard"
              element={
                <ProtectedRoute>
                  <DashboardLayout />
                </ProtectedRoute>
              }
            >
              <Route index element={<ControlCenterPage />} />
              <Route path="voice" element={<VoiceControlPage />} />
              <Route path="macros" element={<VoiceMacrosPage />} />
              <Route path="logs" element={<AuditLogsPage />} />
              <Route path="memory" element={<ChatMemoryPage />} />
              <Route path="settings" element={<SettingsPage />} />
            </Route>

            {/* Role-Protected Admin Routes */}
            <Route
              path="/admin"
              element={
                <AdminRoute>
                  <AdminLayout />
                </AdminRoute>
              }
            >
              <Route index element={<AdminDashboardPage />} />
              <Route path="users" element={<AdminUsersPage />} />
              <Route path="users/:id" element={<AdminUserDetailPage />} />
            </Route>

            {/* Catch-all Fallback */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </AuthProvider>
      </ThemeProvider>
    </BrowserRouter>
  );
}
