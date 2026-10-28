import React, { useState, useEffect, useMemo } from "react";
import { LogIcon, SearchIcon } from "../../components/common/Icons";

export default function AuditLogsPage() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [searchTerm, setSearchTerm] = useState("");
  const [dateFilter, setDateFilter] = useState("");

  const fetchLogs = async () => {
    try {
      setLoading(true);
      setError("");
      const res = await fetch("http://127.0.0.1:8000/audit-logs?limit=100");
      if (!res.ok) {
        throw new Error(`Failed to load audit logs: HTTP ${res.status}`);
      }
      const data = await res.json();
      setLogs(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(err.message || "Failed to load audit logs.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, []);

  const filteredLogs = useMemo(() => {
    return logs.filter((log) => {
      const matchesSearch = searchTerm
        ? (log.command_input || "").toLowerCase().includes(searchTerm.toLowerCase()) ||
          (log.execution_status || "").toLowerCase().includes(searchTerm.toLowerCase())
        : true;

      const matchesDate = dateFilter
        ? (log.timestamp || "").startsWith(dateFilter)
        : true;

      return matchesSearch && matchesDate;
    });
  }, [logs, searchTerm, dateFilter]);

  return (
    <div style={{ maxWidth: "1100px", margin: "0 auto", display: "flex", flexDirection: "column", gap: "24px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <h2 style={{ fontSize: "20px", fontWeight: "600", marginBottom: "4px" }}>Audit Logs</h2>
          <p style={{ fontSize: "14px", color: "var(--text-secondary)" }}>
            Inspect system execution history, voice commands, and diagnostics telemetry.
          </p>
        </div>
        <button className="btn btn-secondary" onClick={fetchLogs} disabled={loading} style={{ fontSize: "13px" }}>
          Refresh
        </button>
      </div>

      {error && (
        <div style={{ padding: "10px 14px", background: "rgba(231,76,60,0.1)", border: "1px solid var(--danger)", borderRadius: "4px", color: "var(--danger)", fontSize: "13px" }}>
          {error}
        </div>
      )}

      {/* Filter toolbar */}
      <div className="card" style={{ padding: "16px 20px" }}>
        <div style={{ display: "flex", gap: "16px", flexWrap: "wrap", alignItems: "center" }}>
          <div style={{ flex: "1 1 240px", position: "relative" }}>
            <span style={{ position: "absolute", left: "10px", top: "50%", transform: "translateY(-50%)", color: "var(--text-muted)", display: "flex" }}>
              <SearchIcon size={14} />
            </span>
            <input
              type="text"
              placeholder="Filter by command or status..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              style={{ paddingLeft: "32px", width: "100%" }}
            />
          </div>

          <div style={{ flex: "0 0 200px" }}>
            <input
              type="date"
              value={dateFilter}
              onChange={(e) => setDateFilter(e.target.value)}
              style={{ width: "100%" }}
            />
          </div>

          {(searchTerm || dateFilter) && (
            <button
              className="btn btn-secondary"
              style={{ fontSize: "12px", padding: "6px 12px" }}
              onClick={() => {
                setSearchTerm("");
                setDateFilter("");
              }}
            >
              Clear Filters
            </button>
          )}
        </div>
      </div>

      {/* Logs Table */}
      <div className="card" style={{ padding: 0, overflow: "hidden" }}>
        <div style={{ overflowX: "auto" }}>
          <table className="table" style={{ margin: 0 }}>
            <thead>
              <tr>
                <th>ID</th>
                <th>Timestamp</th>
                <th>Command Input</th>
                <th>Status</th>
                <th>Telemetry / Latency</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan="5" style={{ textAlign: "center", padding: "28px", color: "var(--text-muted)" }}>
                    Loading audit logs...
                  </td>
                </tr>
              ) : filteredLogs.length === 0 ? (
                <tr>
                  <td colSpan="5" style={{ textAlign: "center", padding: "28px", color: "var(--text-muted)" }}>
                    No matching audit records found.
                  </td>
                </tr>
              ) : (
                filteredLogs.map((item) => {
                  const isSuccess = (item.execution_status || "").toLowerCase().includes("success");
                  const telemetry = item.telemetry_data ? JSON.stringify(item.telemetry_data) : "—";

                  return (
                    <tr key={item.id}>
                      <td style={{ color: "var(--text-muted)", fontSize: "12px" }}>#{item.id}</td>
                      <td style={{ fontSize: "12px", whiteSpace: "nowrap", color: "var(--text-secondary)" }}>
                        {item.timestamp ? new Date(item.timestamp).toLocaleString() : "—"}
                      </td>
                      <td style={{ fontWeight: "500", maxWidth: "340px", wordBreak: "break-word" }}>
                        {item.command_input || "—"}
                      </td>
                      <td>
                        <span className={`badge ${isSuccess ? "badge-success" : "badge-danger"}`}>
                          {item.execution_status || "unknown"}
                        </span>
                      </td>
                      <td style={{ fontSize: "12px", fontFamily: "monospace", color: "var(--text-muted)", maxWidth: "260px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={telemetry}>
                        {telemetry}
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
