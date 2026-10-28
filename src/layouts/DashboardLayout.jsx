import React from "react";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useTheme } from "../context/ThemeContext";
import {
  TerminalIcon,
  MicIcon,
  MacroIcon,
  LogIcon,
  MemoryIcon,
  SettingsIcon,
  ShieldIcon,
  SunIcon,
  MoonIcon,
  LogoutIcon,
  UserIcon
} from "../components/common/Icons";

export const DashboardLayout = () => {
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const location = useLocation();
  const navigate = useNavigate();

  const handleSignOut = () => {
    logout();
    navigate("/login");
  };

  const navItems = [
    { to: "/dashboard", label: "Control Center", icon: <TerminalIcon size={18} />, end: true },
    { to: "/dashboard/voice", label: "Voice Control", icon: <MicIcon size={18} /> },
    { to: "/dashboard/macros", label: "Voice Macros", icon: <MacroIcon size={18} /> },
    { to: "/dashboard/logs", label: "Audit Logs", icon: <LogIcon size={18} /> },
    { to: "/dashboard/memory", label: "Chat Memory", icon: <MemoryIcon size={18} /> },
    { to: "/dashboard/settings", label: "API Settings", icon: <SettingsIcon size={18} /> },
  ];

  // Derive current page title from path
  const getPageTitle = () => {
    const path = location.pathname;
    if (path === "/dashboard") return "Control Center";
    if (path.startsWith("/dashboard/voice")) return "Voice Control";
    if (path.startsWith("/dashboard/macros")) return "Voice Macros";
    if (path.startsWith("/dashboard/logs")) return "Audit Logs";
    if (path.startsWith("/dashboard/memory")) return "Chat Memory";
    if (path.startsWith("/dashboard/settings")) return "API Settings";
    return "Dashboard";
  };

  return (
    <div className="dashboard-container" style={{ display: "flex", minHeight: "100vh", backgroundColor: "var(--bg)" }}>
      {/* Sidebar */}
      <aside className="dashboard-sidebar" style={{
        width: "220px",
        borderRight: "1px solid var(--border)",
        backgroundColor: "var(--bg-secondary)",
        display: "flex",
        flexDirection: "column",
        flexShrink: 0,
        height: "100vh",
        position: "sticky",
        top: 0
      }}>
        {/* Sidebar Header */}
        <div style={{
          padding: "20px 16px",
          borderBottom: "1px solid var(--border)",
          display: "flex",
          flexDirection: "column",
          gap: "4px"
        }}>
          <Link to="/dashboard" style={{
            fontSize: "16px",
            fontWeight: "700",
            letterSpacing: "1px",
            color: "var(--text-primary)"
          }}>
            KALKI
          </Link>
          <div style={{
            display: "flex",
            alignItems: "center",
            gap: "6px",
            fontSize: "12px",
            color: "var(--text-secondary)",
            overflow: "hidden"
          }}>
            <UserIcon size={14} />
            <span style={{ textOverflow: "ellipsis", overflow: "hidden", whiteSpace: "nowrap" }}>
              {user?.username || user?.name || "User"}
            </span>
            {user?.role === "admin" && (
              <span className="badge badge-admin" style={{ fontSize: "9px", padding: "1px 4px" }}>
                Admin
              </span>
            )}
          </div>
        </div>

        {/* Navigation Links */}
        <nav style={{ padding: "12px 8px", display: "flex", flexDirection: "column", gap: "2px", flex: 1, overflowY: "auto" }}>
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              style={({ isActive }) => ({
                display: "flex",
                alignItems: "center",
                gap: "10px",
                padding: "8px 12px",
                borderRadius: "var(--radius-btn)",
                fontSize: "13px",
                fontWeight: isActive ? "600" : "500",
                color: isActive ? "var(--accent)" : "var(--text-secondary)",
                backgroundColor: isActive ? "var(--bg)" : "transparent",
                border: isActive ? "1px solid var(--border)" : "1px solid transparent",
                transition: "var(--transition)"
              })}
            >
              {item.icon}
              <span className="sidebar-text">{item.label}</span>
            </NavLink>
          ))}

          {/* Admin link if role == 'admin' */}
          {user?.role === "admin" && (
            <div style={{ marginTop: "16px", paddingTop: "12px", borderTop: "1px solid var(--border)" }}>
              <NavLink
                to="/admin"
                style={({ isActive }) => ({
                  display: "flex",
                  alignItems: "center",
                  gap: "10px",
                  padding: "8px 12px",
                  borderRadius: "var(--radius-btn)",
                  fontSize: "13px",
                  fontWeight: "600",
                  color: isActive ? "var(--accent-text)" : "var(--accent)",
                  backgroundColor: isActive ? "var(--accent)" : "rgba(192, 57, 43, 0.08)",
                  transition: "var(--transition)"
                })}
              >
                <ShieldIcon size={18} />
                <span className="sidebar-text">Admin Panel</span>
              </NavLink>
            </div>
          )}
        </nav>

        {/* Sidebar Footer */}
        <div style={{
          padding: "12px 8px",
          borderTop: "1px solid var(--border)",
          display: "flex",
          flexDirection: "column",
          gap: "4px"
        }}>
          <button
            onClick={toggleTheme}
            className="btn btn-outline btn-sm"
            style={{ width: "100%", justifyContent: "flex-start", gap: "10px", border: "none" }}
          >
            {theme === "dark" ? <SunIcon size={16} /> : <MoonIcon size={16} />}
            <span className="sidebar-text">{theme === "dark" ? "Light Mode" : "Dark Mode"}</span>
          </button>
          <button
            onClick={handleSignOut}
            className="btn btn-outline btn-sm"
            style={{ width: "100%", justifyContent: "flex-start", gap: "10px", border: "none", color: "var(--danger)" }}
          >
            <LogoutIcon size={16} />
            <span className="sidebar-text">Sign Out</span>
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0, paddingBottom: "70px" }} className="main-content-wrapper">
        {/* Top bar with Breadcrumbs */}
        <header style={{
          height: "56px",
          borderBottom: "1px solid var(--border)",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "0 24px",
          backgroundColor: "var(--bg)"
        }}>
          <div>
            <div style={{ fontSize: "11px", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.5px" }}>
              Dashboard / {getPageTitle()}
            </div>
            <h1 style={{ fontSize: "16px", fontWeight: "600", color: "var(--text-primary)" }}>
              {getPageTitle()}
            </h1>
          </div>
        </header>

        {/* Page View */}
        <main style={{ padding: "24px", flex: 1 }}>
          <Outlet />
        </main>
      </div>

      {/* Bottom Nav for Mobile */}
      <nav className="mobile-bottom-nav">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            className={({ isActive }) => `mobile-nav-item ${isActive ? "active" : ""}`}
            title={item.label}
          >
            {item.icon}
          </NavLink>
        ))}
        {user?.role === "admin" && (
          <NavLink to="/admin" className="mobile-nav-item" title="Admin">
            <ShieldIcon size={18} />
          </NavLink>
        )}
      </nav>

      {/* Responsive Styles */}
      <style>{`
        .mobile-bottom-nav {
          display: none;
        }

        @media (max-width: 640px) {
          .dashboard-sidebar {
            display: none !important;
          }
          .main-content-wrapper {
            padding-bottom: 70px !important;
          }
          .mobile-bottom-nav {
            display: flex;
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            height: 56px;
            background-color: var(--bg-secondary);
            border-top: 1px solid var(--border);
            justify-content: space-around;
            align-items: center;
            z-index: 1000;
          }
          .mobile-nav-item {
            color: var(--text-secondary);
            padding: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
          }
          .mobile-nav-item.active {
            color: var(--accent);
          }
        }
      `}</style>
    </div>
  );
};

export default DashboardLayout;
