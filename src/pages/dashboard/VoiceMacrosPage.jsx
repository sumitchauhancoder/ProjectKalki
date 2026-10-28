import React, { useState, useEffect } from "react";
import { MacroIcon } from "../../components/common/Icons";

export default function VoiceMacrosPage() {
  const [macros, setMacros] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const [triggerPhrase, setTriggerPhrase] = useState("");
  const [actionType, setActionType] = useState("launch_app");
  const [actionPayload, setActionPayload] = useState("");
  const [saving, setSaving] = useState(false);

  const fetchMacros = async () => {
    try {
      setLoading(true);
      setError("");
      const res = await fetch("http://127.0.0.1:8000/macros");
      if (!res.ok) {
        throw new Error(`Failed to load macros: HTTP ${res.status}`);
      }
      const data = await res.json();
      setMacros(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(err.message || "Could not retrieve voice macros.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMacros();
  }, []);

  const handleCreateMacro = async (e) => {
    e.preventDefault();
    if (!triggerPhrase.trim() || !actionPayload.trim()) {
      setError("Trigger phrase and action payload are required.");
      return;
    }

    try {
      setSaving(true);
      setError("");
      setSuccess("");

      const res = await fetch("http://127.0.0.1:8000/macros", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          trigger_phrase: triggerPhrase.trim(),
          action_type: actionType,
          action_payload: actionPayload.trim(),
        }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Failed to create macro.");
      }

      setSuccess(`Macro "${data.trigger}" created successfully.`);
      setTriggerPhrase("");
      setActionPayload("");
      setActionType("launch_app");
      fetchMacros();
    } catch (err) {
      setError(err.message || "Failed to create voice macro.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div style={{ maxWidth: "1000px", margin: "0 auto", display: "flex", flexDirection: "column", gap: "24px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <h2 style={{ fontSize: "20px", fontWeight: "600", marginBottom: "4px" }}>Voice Macros</h2>
          <p style={{ fontSize: "14px", color: "var(--text-secondary)" }}>
            Configure custom spoken shortcut triggers and automation actions.
          </p>
        </div>
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

      {/* Create Macro Form */}
      <div className="card">
        <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "16px" }}>
          <MacroIcon size={18} />
          <h3 style={{ fontSize: "15px", fontWeight: "600" }}>Create New Macro</h3>
        </div>

        <form onSubmit={handleCreateMacro} style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1.5fr auto", gap: "12px", alignItems: "end" }}>
          <div>
            <label style={{ display: "block", fontSize: "12px", fontWeight: "500", color: "var(--text-secondary)", marginBottom: "6px" }}>
              Trigger Phrase
            </label>
            <input
              type="text"
              placeholder="e.g. open notepad"
              value={triggerPhrase}
              onChange={(e) => setTriggerPhrase(e.target.value)}
              required
            />
          </div>

          <div>
            <label style={{ display: "block", fontSize: "12px", fontWeight: "500", color: "var(--text-secondary)", marginBottom: "6px" }}>
              Action Type
            </label>
            <select value={actionType} onChange={(e) => setActionType(e.target.value)}>
              <option value="launch_app">launch_app</option>
              <option value="hotkey">hotkey</option>
              <option value="type_text">type_text</option>
            </select>
          </div>

          <div>
            <label style={{ display: "block", fontSize: "12px", fontWeight: "500", color: "var(--text-secondary)", marginBottom: "6px" }}>
              Action Payload
            </label>
            <input
              type="text"
              placeholder="e.g. notepad.exe or ctrl+s"
              value={actionPayload}
              onChange={(e) => setActionPayload(e.target.value)}
              required
            />
          </div>

          <button type="submit" className="btn btn-primary" disabled={saving}>
            {saving ? "Adding..." : "Add Macro"}
          </button>
        </form>
      </div>

      {/* Existing Macros Table */}
      <div className="card" style={{ padding: 0, overflow: "hidden" }}>
        <div style={{ padding: "16px 20px", borderBottom: "1px solid var(--border)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <h3 style={{ fontSize: "15px", fontWeight: "600" }}>Configured Macros ({macros.length})</h3>
          <button className="btn btn-secondary" style={{ fontSize: "12px", padding: "4px 8px" }} onClick={fetchMacros} disabled={loading}>
            Refresh
          </button>
        </div>

        <div style={{ overflowX: "auto" }}>
          <table className="table" style={{ margin: 0 }}>
            <thead>
              <tr>
                <th>ID</th>
                <th>Trigger Phrase</th>
                <th>Action Type</th>
                <th>Action Payload</th>
                <th>Created At</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan="5" style={{ textAlign: "center", padding: "24px", color: "var(--text-muted)" }}>
                    Loading macros...
                  </td>
                </tr>
              ) : macros.length === 0 ? (
                <tr>
                  <td colSpan="5" style={{ textAlign: "center", padding: "24px", color: "var(--text-muted)" }}>
                    No voice macros configured yet. Add your first macro above.
                  </td>
                </tr>
              ) : (
                macros.map((m) => (
                  <tr key={m.id}>
                    <td style={{ color: "var(--text-muted)", fontSize: "12px" }}>#{m.id}</td>
                    <td style={{ fontWeight: "500" }}>"{m.trigger_phrase}"</td>
                    <td>
                      <span className="badge badge-neutral">{m.action_type}</span>
                    </td>
                    <td style={{ fontFamily: "monospace", fontSize: "12px" }}>{m.action_payload}</td>
                    <td style={{ color: "var(--text-secondary)", fontSize: "12px" }}>
                      {m.created_at ? new Date(m.created_at).toLocaleDateString() : "—"}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
