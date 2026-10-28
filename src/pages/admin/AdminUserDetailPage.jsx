import React, { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { ArrowLeftIcon, ShieldIcon, UserIcon } from "../../components/common/Icons";

export default function AdminUserDetailPage() {
  const { id } = useParams();
  const { user: currentUser, token } = useAuth();

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [actionLoading, setActionLoading] = useState(false);

  const fetchUserDetail = async () => {
    try {
      setLoading(true);
      setError("");
      const headers = { "Content-Type": "application/json" };
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const res = await fetch(`http://127.0.0.1:8000/admin/users/${id}`, { headers });
      if (!res.ok) {
        throw new Error(`Failed to load user: HTTP ${res.status}`);
      }
      const json = await res.json();
      setData(json);
    } catch (err) {
      setError(err.message || "Could not retrieve user details.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUserDetail();
  }, [id, token]);

  const handleToggleRole = async () => {
    if (!data?.user) return;
    const currentRole = data.user.role || "user";
    const nextRole = currentRole === "admin" ? "user" : "admin";

    try {
      setActionLoading(true);
      setError("");
      setSuccess("");

      const headers = { "Content-Type": "application/json" };
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const res = await fetch(`http://127.0.0.1:8000/admin/users/${id}/role`, {
        method: "POST",
        headers,
        body: JSON.stringify({ role: nextRole }),
      });

      const resJson = await res.json();
      if (!res.ok) {
        throw new Error(resJson.detail || "Failed to change user role.");
      }

      setSuccess(`User role successfully changed to ${nextRole}.`);
      fetchUserDetail();
    } catch (err) {
      setError(err.message || "Failed to update user role.");
    } finally {
      setActionLoading(false);
    }
  };

  const handleToggleStatus = async () => {
    if (!data?.user) return;
    const currentStatus = data.user.status || "active";
    const nextStatus = currentStatus === "active" ? "disabled" : "active";

    if (data.user.id === currentUser?.id && nextStatus === "disabled") {
      setError("You cannot disable your own administrator account.");
      return;
    }

    try {
      setActionLoading(true);
      setError("");
      setSuccess("");

      const headers = { "Content-Type": "application/json" };
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const res = await fetch(`http://127.0.0.1:8000/admin/users/${id}/status`, {
        method: "POST",
        headers,
        body: JSON.stringify({ status: nextStatus }),
      });

      const resJson = await res.json();
      if (!res.ok) {
        throw new Error(resJson.detail || "Failed to change user status.");
      }

      setSuccess(`User status successfully changed to ${nextStatus}.`);
      fetchUserDetail();
    } catch (err) {
      setError(err.message || "Failed to update user status.");
    } finally {
      setActionLoading(false);
    }
  };

  if (loading) {
    return (
      <div style={{ padding: "40px 0", textAlign: "center", color: "var(--text-muted)" }}>
        Loading user account details...
      </div>
    );
  }

  if (error && !data) {
    return (
      <div style={{ maxWidth: "600px", margin: "40px auto" }}>
        <div style={{ padding: "16px", background: "rgba(231,76,60,0.1)", border: "1px solid var(--danger)", borderRadius: "4px", color: "var(--danger)", marginBottom: "16px" }}>
          {error}
        </div>
        <Link to="/admin/users" className="btn btn-secondary" style={{ textDecoration: "none", display: "inline-flex", alignItems: "center", gap: "6px" }}>
          <ArrowLeftIcon size={14} />
          <span>Back to Users Directory</span>
        </Link>
      </div>
    );
  }

  const { user, logs } = data;
  const isSelf = user.id === currentUser?.id;
  const isAdmin = user.role === "admin";
  const isActive = user.status === "active";

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      <div>
        <Link
          to="/admin/users"
          style={{
            fontSize: "13px",
            color: "var(--text-secondary)",
            textDecoration: "none",
            display: "inline-flex",
            alignItems: "center",
            gap: "6px",
            marginBottom: "12px",
          }}
        >
          <ArrowLeftIcon size={14} />
          <span>Back to Users Directory</span>
        </Link>

        <h1 style={{ fontSize: "22px", fontWeight: "700" }}>
          User Profile: {user.name || user.username}
        </h1>
      </div>

      {error && (
        <div style={{ padding: "10px 14px", background: "rgba(231,76,60,0.1)", border: "1px solid var(--danger)", borderRadius: "4px", color: "var(--danger)", fontSize: "13px" }}>
          {error}
        </div>
      )}

      {success && (
        <div style={{ padding: "10px 14px", background: "rgba(39,174,96,0.1)", border: "1px solid var(--success)", borderRadius: "4px", color: "var(--success)", fontSize: "13px" }}>
          {success}
        </div>
      )}

      {/* User Info & Actions Card */}
      <div className="card" style={{ padding: "24px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "16px", borderBottom: "1px solid var(--border)", paddingBottom: "20px", marginBottom: "20px" }}>
          <div>
            <div style={{ fontSize: "18px", fontWeight: "600", display: "flex", alignItems: "center", gap: "10px" }}>
              <span>{user.name || "No display name"}</span>
              <span className={`badge ${isAdmin ? "badge-primary" : "badge-neutral"}`}>{user.role}</span>
              <span className={`badge ${isActive ? "badge-success" : "badge-danger"}`}>{user.status}</span>
            </div>
            <div style={{ fontSize: "14px", color: "var(--text-muted)", marginTop: "4px" }}>
              @{user.username} &bull; {user.email}
            </div>
          </div>

          <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
            <button
              onClick={handleToggleRole}
              disabled={actionLoading}
              className="btn btn-secondary"
              style={{ fontSize: "13px" }}
            >
              {isAdmin ? "Demote to User" : "Promote to Admin"}
            </button>

            <button
              onClick={handleToggleStatus}
              disabled={actionLoading || (isSelf && isActive)}
              className={`btn ${isActive ? "btn-secondary" : "btn-primary"}`}
              style={{ fontSize: "13px", color: isActive ? "var(--danger)" : "var(--accent-text)" }}
              title={isSelf && isActive ? "Cannot disable your own account" : ""}
            >
              {isActive ? "Disable Account" : "Enable Account"}
            </button>
          </div>
        </div>

        {/* Metadata Details */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "16px" }}>
          <div>
            <div style={{ fontSize: "12px", color: "var(--text-secondary)", marginBottom: "4px" }}>Account ID</div>
            <div style={{ fontSize: "14px", fontWeight: "500" }}>#{user.id}</div>
          </div>
          <div>
            <div style={{ fontSize: "12px", color: "var(--text-secondary)", marginBottom: "4px" }}>Registered Date</div>
            <div style={{ fontSize: "14px", fontWeight: "500" }}>
              {user.created_at ? new Date(user.created_at).toLocaleString() : "—"}
            </div>
          </div>
          <div>
            <div style={{ fontSize: "12px", color: "var(--text-secondary)", marginBottom: "4px" }}>Last Login</div>
            <div style={{ fontSize: "14px", fontWeight: "500" }}>
              {user.last_login ? new Date(user.last_login).toLocaleString() : "Never"}
            </div>
          </div>
        </div>
      </div>

      {/* Recent User Actions / Audit Logs */}
      <div className="card" style={{ padding: 0, overflow: "hidden" }}>
        <div style={{ padding: "16px 20px", borderBottom: "1px solid var(--border)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <h3 style={{ fontSize: "15px", fontWeight: "600" }}>Recent Audit Logs (Last 50)</h3>
            <p style={{ fontSize: "12px", color: "var(--text-secondary)", margin: 0 }}>
              Command actions without message text content for user privacy.
            </p>
          </div>
        </div>

        <div style={{ overflowX: "auto" }}>
          <table className="table" style={{ margin: 0 }}>
            <thead>
              <tr>
                <th>ID</th>
                <th>Timestamp</th>
                <th>Action Type</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {!logs || logs.length === 0 ? (
                <tr>
                  <td colSpan="4" style={{ textAlign: "center", padding: "28px", color: "var(--text-muted)" }}>
                    No audit records logged for this account.
                  </td>
                </tr>
              ) : (
                logs.map((log) => {
                  const isSuccess = (log.status || "").toLowerCase().includes("success");
                  return (
                    <tr key={log.id}>
                      <td style={{ color: "var(--text-muted)", fontSize: "12px" }}>#{log.id}</td>
                      <td style={{ fontSize: "12px", whiteSpace: "nowrap", color: "var(--text-secondary)" }}>
                        {log.timestamp ? new Date(log.timestamp).toLocaleString() : "—"}
                      </td>
                      <td style={{ fontFamily: "monospace", fontSize: "13px" }}>{log.action_type}</td>
                      <td>
                        <span className={`badge ${isSuccess ? "badge-success" : "badge-danger"}`}>
                          {log.status}
                        </span>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
