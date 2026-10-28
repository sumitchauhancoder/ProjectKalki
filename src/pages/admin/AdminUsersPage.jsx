import React, { useState, useEffect, useMemo } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { SearchIcon, UsersIcon } from "../../components/common/Icons";

export default function AdminUsersPage() {
  const { user: currentUser, token } = useAuth();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [searchTerm, setSearchTerm] = useState("");
  const [updatingId, setUpdatingId] = useState(null);

  const fetchUsers = async () => {
    try {
      setLoading(true);
      setError("");
      const headers = { "Content-Type": "application/json" };
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const res = await fetch("http://127.0.0.1:8000/admin/users", { headers });
      if (!res.ok) {
        throw new Error(`Failed to load users: HTTP ${res.status}`);
      }
      const data = await res.json();
      setUsers(data.users || []);
    } catch (err) {
      setError(err.message || "Failed to load registered users.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, [token]);

  const handleToggleStatus = async (user) => {
    if (user.id === currentUser?.id) {
      setError("You cannot disable your own administrator account.");
      return;
    }

    const nextStatus = user.status === "active" ? "disabled" : "active";
    try {
      setUpdatingId(user.id);
      setError("");
      setSuccess("");

      const headers = { "Content-Type": "application/json" };
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const res = await fetch(`http://127.0.0.1:8000/admin/users/${user.id}/status`, {
        method: "POST",
        headers,
        body: JSON.stringify({ status: nextStatus }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Failed to update user status.");
      }

      setSuccess(`User "${user.username}" status updated to ${nextStatus}.`);
      fetchUsers();
    } catch (err) {
      setError(err.message || "Could not update user status.");
    } finally {
      setUpdatingId(null);
    }
  };

  const filteredUsers = useMemo(() => {
    if (!searchTerm.trim()) return users;
    const term = searchTerm.toLowerCase();
    return users.filter(
      (u) =>
        (u.name || "").toLowerCase().includes(term) ||
        (u.username || "").toLowerCase().includes(term) ||
        (u.email || "").toLowerCase().includes(term)
    );
  }, [users, searchTerm]);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <h1 style={{ fontSize: "22px", fontWeight: "700", marginBottom: "4px" }}>User Directory & RBAC</h1>
          <p style={{ fontSize: "14px", color: "var(--text-secondary)" }}>
            Review registered accounts, toggle authorization access, and inspect profiles.
          </p>
        </div>

        <button className="btn btn-secondary" onClick={fetchUsers} disabled={loading} style={{ fontSize: "13px" }}>
          Refresh
        </button>
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

      {/* Filter toolbar */}
      <div className="card" style={{ padding: "16px 20px" }}>
        <div style={{ position: "relative", maxWidth: "360px" }}>
          <span style={{ position: "absolute", left: "10px", top: "50%", transform: "translateY(-50%)", color: "var(--text-muted)", display: "flex" }}>
            <SearchIcon size={14} />
          </span>
          <input
            type="text"
            placeholder="Search by name, username, or email..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={{ paddingLeft: "32px", width: "100%" }}
          />
        </div>
      </div>

      {/* Users Table */}
      <div className="card" style={{ padding: 0, overflow: "hidden" }}>
        <div style={{ overflowX: "auto" }}>
          <table className="table" style={{ margin: 0 }}>
            <thead>
              <tr>
                <th>User</th>
                <th>Email</th>
                <th>Role</th>
                <th>Status</th>
                <th>Last Login</th>
                <th>Commands</th>
                <th style={{ textAlign: "right" }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan="7" style={{ textAlign: "center", padding: "32px", color: "var(--text-muted)" }}>
                    Loading users...
                  </td>
                </tr>
              ) : filteredUsers.length === 0 ? (
                <tr>
                  <td colSpan="7" style={{ textAlign: "center", padding: "32px", color: "var(--text-muted)" }}>
                    No users found matching search criteria.
                  </td>
                </tr>
              ) : (
                filteredUsers.map((u) => {
                  const isAdmin = u.role === "admin";
                  const isActive = u.status === "active";
                  const isSelf = u.id === currentUser?.id;

                  return (
                    <tr key={u.id}>
                      <td>
                        <div style={{ fontWeight: "600", fontSize: "14px" }}>{u.name || u.username}</div>
                        <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>@{u.username}</div>
                      </td>
                      <td style={{ fontSize: "13px" }}>{u.email}</td>
                      <td>
                        <span className={`badge ${isAdmin ? "badge-primary" : "badge-neutral"}`}>
                          {u.role}
                        </span>
                      </td>
                      <td>
                        <span className={`badge ${isActive ? "badge-success" : "badge-danger"}`}>
                          {u.status}
                        </span>
                      </td>
                      <td style={{ fontSize: "12px", color: "var(--text-secondary)" }}>
                        {u.last_login ? new Date(u.last_login).toLocaleString() : "Never"}
                      </td>
                      <td style={{ fontSize: "13px" }}>{u.commands ?? 0}</td>
                      <td style={{ textAlign: "right" }}>
                        <div style={{ display: "inline-flex", gap: "8px", alignItems: "center" }}>
                          <Link
                            to={`/admin/users/${u.id}`}
                            className="btn btn-secondary"
                            style={{ fontSize: "12px", padding: "4px 8px", textDecoration: "none" }}
                          >
                            View
                          </Link>
                          <button
                            onClick={() => handleToggleStatus(u)}
                            disabled={isSelf || updatingId === u.id}
                            className={`btn ${isActive ? "btn-secondary" : "btn-primary"}`}
                            style={{
                              fontSize: "12px",
                              padding: "4px 8px",
                              color: isActive ? "var(--danger)" : "var(--accent-text)",
                            }}
                            title={isSelf ? "Cannot disable your own account" : ""}
                          >
                            {updatingId === u.id ? "..." : isActive ? "Disable" : "Enable"}
                          </button>
                        </div>
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
