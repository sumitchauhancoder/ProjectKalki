import React from "react";
import { Outlet, Link, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useTheme } from "../context/ThemeContext";
import { ShieldIcon, SunIcon, MoonIcon, ArrowLeftIcon, UsersIcon } from "../components/common/Icons";

export default function AdminLayout() {
  const { user } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const location = useLocation();

  const isCurrent = (path) => {
    if (path === "/admin" && location.pathname === "/admin") return true;
    if (path !== "/admin" && location.pathname.startsWith(path)) return true;
    return false;
  };

  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column", background: "var(--bg)" }}>
      {/* Admin Top Navbar */}
      <header
        style={{
          height: "56px",
          borderBottom: "1px solid var(--border)",
          background: "var(--bg-secondary)",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "0 24px",
          position: "sticky",
          top: 0,
          zIndex: 100,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "24px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px", fontWeight: "700", fontSize: "16px", color: "var(--accent)" }}>
            <ShieldIcon size={20} />
            <span>KALKI Admin</span>
          </div>

          <nav style={{ display: "flex", gap: "8px" }}>
            <Link
              to="/admin"
              style={{
                fontSize: "13px",
                fontWeight: "500",
                padding: "6px 12px",
                borderRadius: "4px",
                textDecoration: "none",
                color: isCurrent("/admin") ? "var(--accent)" : "var(--text-secondary)",
                background: isCurrent("/admin") ? "var(--bg)" : "transparent",
                border: isCurrent("/admin") ? "1px solid var(--border)" : "1px solid transparent",
              }}
            >
              Overview
            </Link>
            <Link
              to="/admin/users"
              style={{
                fontSize: "13px",
                fontWeight: "500",
                padding: "6px 12px",
                borderRadius: "4px",
                textDecoration: "none",
                color: isCurrent("/admin/users") ? "var(--accent)" : "var(--text-secondary)",
                background: isCurrent("/admin/users") ? "var(--bg)" : "transparent",
                border: isCurrent("/admin/users") ? "1px solid var(--border)" : "1px solid transparent",
              }}
            >
              Users & RBAC
            </Link>
          </nav>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
          <span style={{ fontSize: "13px", color: "var(--text-secondary)" }}>
            Logged in as <strong style={{ color: "var(--text-primary)" }}>{user?.username || "Admin"}</strong>
          </span>

          <button
            onClick={toggleTheme}
            className="btn btn-secondary"
            style={{ padding: "6px", display: "flex", alignItems: "center" }}
            title="Toggle theme"
          >
            {theme === "dark" ? <SunIcon size={14} /> : <MoonIcon size={14} />}
          </button>

          <Link
            to="/dashboard"
            className="btn btn-secondary"
            style={{ fontSize: "12px", display: "flex", alignItems: "center", gap: "6px", textDecoration: "none" }}
          >
            <ArrowLeftIcon size={14} />
            <span>Back to Dashboard</span>
          </Link>
        </div>
      </header>

      {/* Main Content Area */}
      <main style={{ flex: 1, padding: "32px 24px", maxWidth: "1200px", width: "100%", margin: "0 auto" }}>
        <Outlet />
      </main>
    </div>
  );
}
