import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { UsersIcon, ShieldIcon, TerminalIcon } from "../../components/common/Icons";

export default function AdminDashboardPage() {
  const { token } = useAuth();
  const [stats, setStats] = useState({
    total_users: 0,
    active_users: 0,
    disabled_users: 0,
    commands_today: 0,
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const fetchStats = async () => {
      try {
        setLoading(true);
        const headers = { "Content-Type": "application/json" };
        if (token) headers["Authorization"] = `Bearer ${token}`;

        const res = await fetch("http://127.0.0.1:8000/admin/stats", { headers });
        if (!res.ok) {
          throw new Error(`Failed to load admin stats: HTTP ${res.status}`);
        }
        const data = await res.json();
        setStats(data);
      } catch (err) {
        setError(err.message || "Failed to load admin dashboard statistics.");
      } finally {
        setLoading(false);
      }
    };

    fetchStats();
  }, [token]);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "28px" }}>
      <div>
        <h1 style={{ fontSize: "22px", fontWeight: "700", marginBottom: "4px" }}>Platform Overview</h1>
        <p style={{ fontSize: "14px", color: "var(--text-secondary)" }}>
          Real-time metrics, user status breakdown, and system command activity.
        </p>
      </div>

      {error && (
        <div style={{ padding: "10px 14px", background: "rgba(231,76,60,0.1)", border: "1px solid var(--danger)", borderRadius: "4px", color: "var(--danger)", fontSize: "13px" }}>
          {error}
        </div>
      )}

      {/* 4 KPI Stats Cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "16px" }}>
        <div className="card" style={{ padding: "20px" }}>
          <div style={{ fontSize: "13px", color: "var(--text-secondary)", marginBottom: "8px", fontWeight: "500" }}>
            Total Registered Users
          </div>
          <div style={{ fontSize: "28px", fontWeight: "700", color: "var(--text-primary)" }}>
            {loading ? "..." : stats.total_users}
          </div>
          <div style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "4px" }}>
            Neon Postgres / SQLite
          </div>
        </div>

        <div className="card" style={{ padding: "20px" }}>
          <div style={{ fontSize: "13px", color: "var(--text-secondary)", marginBottom: "8px", fontWeight: "500" }}>
            Active Accounts
          </div>
          <div style={{ fontSize: "28px", fontWeight: "700", color: "var(--success)" }}>
            {loading ? "..." : stats.active_users}
          </div>
          <div style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "4px" }}>
            Status: active
          </div>
        </div>

        <div className="card" style={{ padding: "20px" }}>
          <div style={{ fontSize: "13px", color: "var(--text-secondary)", marginBottom: "8px", fontWeight: "500" }}>
            Disabled Accounts
          </div>
          <div style={{ fontSize: "28px", fontWeight: "700", color: stats.disabled_users > 0 ? "var(--danger)" : "var(--text-primary)" }}>
            {loading ? "..." : stats.disabled_users}
          </div>
          <div style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "4px" }}>
            Status: disabled
          </div>
        </div>

        <div className="card" style={{ padding: "20px" }}>
          <div style={{ fontSize: "13px", color: "var(--text-secondary)", marginBottom: "8px", fontWeight: "500" }}>
            Commands Executed Today
          </div>
          <div style={{ fontSize: "28px", fontWeight: "700", color: "var(--accent)" }}>
            {loading ? "..." : stats.commands_today}
          </div>
          <div style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "4px" }}>
            Since midnight UTC/Local
          </div>
        </div>
      </div>

      {/* Quick Action Navigation */}
      <div className="card" style={{ padding: "24px" }}>
        <h3 style={{ fontSize: "16px", fontWeight: "600", marginBottom: "8px" }}>User Management & RBAC</h3>
        <p style={{ fontSize: "14px", color: "var(--text-secondary)", marginBottom: "16px", maxWidth: "600px", lineHeight: "1.5" }}>
          View all registered accounts, manage role permissions (User / Admin), enable or disable access, and audit individual command activities.
        </p>
        <Link to="/admin/users" className="btn btn-primary" style={{ textDecoration: "none", display: "inline-flex", alignItems: "center", gap: "8px" }}>
          <UsersIcon size={16} />
          <span>Manage User Accounts</span>
        </Link>
      </div>
    </div>
  );
}
