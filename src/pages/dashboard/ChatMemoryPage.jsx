import React, { useState, useEffect } from "react";
import { useAuth } from "../../context/AuthContext";
import { MemoryIcon, TrashIcon } from "../../components/common/Icons";

export default function ChatMemoryPage() {
  const { token } = useAuth();
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [clearing, setClearing] = useState(false);
  const [error, setError] = useState("");
  const [notification, setNotification] = useState("");
  const [showConfirm, setShowConfirm] = useState(false);

  const fetchHistory = async () => {
    try {
      setLoading(true);
      setError("");
      const res = await fetch("http://127.0.0.1:8000/chat-history");
      if (!res.ok) {
        throw new Error(`Failed to load chat history: HTTP ${res.status}`);
      }
      const data = await res.json();
      setMessages(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(err.message || "Failed to load chat memory.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, []);

  const handleClearMemory = async () => {
    setShowConfirm(false);
    try {
      setClearing(true);
      setError("");
      setNotification("");

      const headers = { "Content-Type": "application/json" };
      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      }

      const res = await fetch("http://127.0.0.1:8000/chat-memory/clear", {
        method: "POST",
        headers,
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Failed to clear chat memory.");
      }

      setNotification(`Successfully cleared ${data.deleted_count ?? 0} conversational memory records.`);
      fetchHistory();
    } catch (err) {
      setError(err.message || "Could not clear memory.");
    } finally {
      setClearing(false);
    }
  };

  return (
    <div style={{ maxWidth: "900px", margin: "0 auto", display: "flex", flexDirection: "column", gap: "24px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <h2 style={{ fontSize: "20px", fontWeight: "600", marginBottom: "4px" }}>Chat Memory</h2>
          <p style={{ fontSize: "14px", color: "var(--text-secondary)" }}>
            Inspect persisted conversation memory used for multi-turn assistant context.
          </p>
        </div>

        <div style={{ display: "flex", gap: "10px" }}>
          <button className="btn btn-secondary" onClick={fetchHistory} disabled={loading} style={{ fontSize: "13px" }}>
            Refresh
          </button>
          <button
            className="btn btn-danger"
            onClick={() => setShowConfirm(true)}
            disabled={clearing || messages.length === 0}
            style={{ fontSize: "13px", display: "flex", alignItems: "center", gap: "6px" }}
          >
            <TrashIcon size={14} />
            <span>Clear Memory</span>
          </button>
        </div>
      </div>

      {error && (
        <div style={{ padding: "10px 14px", background: "rgba(231,76,60,0.1)", border: "1px solid var(--danger)", borderRadius: "4px", color: "var(--danger)", fontSize: "13px" }}>
          {error}
        </div>
      )}

      {notification && (
        <div style={{ padding: "10px 14px", background: "rgba(39,174,96,0.1)", border: "1px solid var(--success)", borderRadius: "4px", color: "var(--success)", fontSize: "13px" }}>
          {notification}
        </div>
      )}

      {/* Confirmation Modal */}
      {showConfirm && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0,0,0,0.5)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
            padding: "16px",
          }}
        >
          <div className="card" style={{ maxWidth: "420px", width: "100%", padding: "24px", boxShadow: "0 8px 30px rgba(0,0,0,0.2)" }}>
            <h3 style={{ fontSize: "16px", fontWeight: "600", marginBottom: "8px" }}>Clear Chat Memory?</h3>
            <p style={{ fontSize: "14px", color: "var(--text-secondary)", marginBottom: "20px", lineHeight: "1.5" }}>
              Are you sure you want to delete all stored conversation messages? This action cannot be undone and will reset KALKI's short-term context.
            </p>
            <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px" }}>
              <button className="btn btn-secondary" onClick={() => setShowConfirm(false)}>
                Cancel
              </button>
              <button className="btn btn-danger" onClick={handleClearMemory}>
                Yes, Clear
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Message List */}
      <div className="card" style={{ padding: 0, overflow: "hidden" }}>
        <div style={{ padding: "16px 20px", borderBottom: "1px solid var(--border)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <h3 style={{ fontSize: "15px", fontWeight: "600" }}>Stored Session Messages ({messages.length})</h3>
          <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>Session #1</span>
        </div>

        {loading ? (
          <div style={{ textAlign: "center", padding: "36px", color: "var(--text-muted)", fontSize: "14px" }}>
            Loading memory history...
          </div>
        ) : messages.length === 0 ? (
          <div style={{ textAlign: "center", padding: "48px 24px" }}>
            <div style={{ color: "var(--text-muted)", marginBottom: "12px", display: "inline-flex" }}>
              <MemoryIcon size={36} />
            </div>
            <p style={{ fontSize: "14px", fontWeight: "500", color: "var(--text-primary)", marginBottom: "4px" }}>
              No messages in memory
            </p>
            <p style={{ fontSize: "13px", color: "var(--text-secondary)" }}>
              Commands and replies you execute in the Control Center will be remembered here.
            </p>
          </div>
        ) : (
          <div style={{ divideY: "1px solid var(--border)", maxHeight: "600px", overflowY: "auto" }}>
            {messages.map((m, idx) => {
              const isUser = m.role === "user";
              return (
                <div
                  key={idx}
                  style={{
                    padding: "16px 20px",
                    borderBottom: idx !== messages.length - 1 ? "1px solid var(--border)" : "none",
                    background: isUser ? "transparent" : "var(--bg-secondary)",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "6px", alignItems: "center" }}>
                    <span className={`badge ${isUser ? "badge-primary" : "badge-neutral"}`} style={{ textTransform: "uppercase" }}>
                      {m.role}
                    </span>
                    <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                      {m.timestamp ? new Date(m.timestamp).toLocaleTimeString() : ""}
                    </span>
                  </div>
                  <div style={{ fontSize: "14px", color: "var(--text-primary)", whiteSpace: "pre-wrap", lineHeight: "1.5" }}>
                    {m.content}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
