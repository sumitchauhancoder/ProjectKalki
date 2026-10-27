import React from "react";
import "./Dashboard.css";

export default function Dashboard({
  currentUser,
  onLogout,
  activeTab,
  setActiveTab,
  status,
  transcript,
  manualCommand,
  setManualCommand,
  handleManualSubmit,
  triggerBackendVoice,
  listening,
  screenSharing,
  startScreenCapture,
  stopScreenCapture,
  analyzeCurrentFrame,
  handleAnalyzeAndClick,
  canvasRef,
  videoRef,
  visionAnalysis,
  macros,
  newTrigger,
  setNewTrigger,
  newActionType,
  setNewActionType,
  newPayloadVal,
  setNewPayloadVal,
  handleAddMacro,
  auditLogs,
  fetchAuditLogs,
  chatHistory,
  fetchChatHistory,
}) {
  return (
    <div className="dashboard-container">
      {/* Sidebar Navigation */}
      <aside className="dashboard-sidebar">
        <div className="sidebar-brand">
          <span className="pulse-dot"></span>
          <h2>KALKI CORE</h2>
        </div>

        <nav className="sidebar-nav">
          <button
            type="button"
            className={activeTab === "controls" ? "nav-item active" : "nav-item"}
            onClick={() => setActiveTab("controls")}
          >
            Control Center
          </button>
          <button
            type="button"
            className={activeTab === "macros" ? "nav-item active" : "nav-item"}
            onClick={() => setActiveTab("macros")}
          >
            Voice Macros <span className="badge-count">{macros.length}</span>
          </button>
          <button
            type="button"
            className={activeTab === "logs" ? "nav-item active" : "nav-item"}
            onClick={() => {
              setActiveTab("logs");
              fetchAuditLogs();
            }}
          >
            Audit Logs <span className="badge-count">{auditLogs.length}</span>
          </button>
          <button
            type="button"
            className={activeTab === "chat" ? "nav-item active" : "nav-item"}
            onClick={() => {
              setActiveTab("chat");
              fetchChatHistory();
            }}
          >
            Chat Memory <span className="badge-count">{chatHistory.length}</span>
          </button>
        </nav>

        <div className="sidebar-footer">
          <div className="user-info">
            <span className="user-label">Operator</span>
            <span className="user-name">{currentUser?.username || "Admin"}</span>
          </div>
          <button type="button" className="btn-logout" onClick={onLogout}>
            Sign Out
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="dashboard-main">
        {/* Status Header Banner */}
        <div className="status-banner">
          <div className="status-info">
            <span className="status-label">ENGINE STATUS</span>
            <span className="status-value">{status}</span>
          </div>
          <div className="status-info">
            <span className="status-label">LAST INPUT</span>
            <span className="status-value highlight">{transcript || "None"}</span>
          </div>
        </div>

        {/* --- CONTROL CENTER TAB --- */}
        {activeTab === "controls" && (
          <div className="module-content">
            <div className="module-header">
              <h2>Control Center</h2>
              <p>Execute text or voice commands and manage real-time computer vision streams.</p>
            </div>

            <form onSubmit={handleManualSubmit} className="command-form">
              <input
                type="text"
                value={manualCommand}
                onChange={(e) => setManualCommand(e.target.value)}
                placeholder="Type command (e.g., 'open calculator')..."
                className="command-input"
              />
              <button type="submit" className="btn-primary-red">
                Execute
              </button>
            </form>

            <div className="action-buttons-grid">
              <button
                type="button"
                onClick={triggerBackendVoice}
                disabled={listening}
                className="btn-secondary"
              >
                {listening ? "Listening (4s)..." : "Speak Command"}
              </button>

              <button
                type="button"
                onClick={screenSharing ? stopScreenCapture : startScreenCapture}
                className="btn-secondary"
              >
                {screenSharing ? "Stop Screen Share" : "Start Screen Share"}
              </button>

              <button
                type="button"
                onClick={analyzeCurrentFrame}
                disabled={!screenSharing}
                className="btn-secondary"
              >
                Analyze Frame (OpenCV)
              </button>

              <button
                type="button"
                onClick={handleAnalyzeAndClick}
                className="btn-primary-red"
              >
                Analyze & Target Click
              </button>
            </div>

            <canvas ref={canvasRef} style={{ display: "none" }} />

            {screenSharing && (
              <div className="media-preview-container">
                <h3>Active Screen Feed</h3>
                <video ref={videoRef} autoPlay playsInline muted className="screen-video" />
              </div>
            )}

            {visionAnalysis && (
              <div className="analysis-box">
                <h3>OpenCV Analysis Results</h3>
                <pre>{JSON.stringify(visionAnalysis, null, 2)}</pre>
              </div>
            )}
          </div>
        )}

        {/* --- VOICE MACROS TAB --- */}
        {activeTab === "macros" && (
          <div className="module-content">
            <div className="module-header">
              <h2>Voice Macros Manager</h2>
              <p>Register custom local trigger phrases mapped to applications, hotkeys, or text.</p>
            </div>

            <form onSubmit={handleAddMacro} className="macro-form">
              <input
                type="text"
                placeholder="Trigger Phrase (e.g., 'dev mode')"
                value={newTrigger}
                onChange={(e) => setNewTrigger(e.target.value)}
                className="form-input"
                required
              />
              <select
                value={newActionType}
                onChange={(e) => setNewActionType(e.target.value)}
                className="form-select"
              >
                <option value="launch_app">Launch Application</option>
                <option value="hotkey">Keyboard Hotkey</option>
                <option value="type_text">Type Text</option>
              </select>
              <input
                type="text"
                placeholder="Payload (e.g., 'calc.exe')"
                value={newPayloadVal}
                onChange={(e) => setNewPayloadVal(e.target.value)}
                className="form-input"
                required
              />
              <button type="submit" className="btn-primary-red">
                Add Macro
              </button>
            </form>

            <div className="list-container">
              <h3>Registered Macros</h3>
              {macros.length === 0 ? (
                <p className="empty-text">No custom macros registered yet.</p>
              ) : (
                <ul className="item-list">
                  {macros.map((m) => (
                    <li key={m.id} className="list-item">
                      <div>
                        <strong>"{m.trigger_phrase}"</strong> &rarr;{" "}
                        <code>{m.action_type}</code>
                      </div>
                      <span className="payload-badge">{JSON.stringify(m.action_payload)}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        )}

        {/* --- AUDIT LOGS TAB --- */}
        {activeTab === "logs" && (
          <div className="module-content">
            <div className="module-header flex-between">
              <div>
                <h2>System Audit Logs</h2>
                <p>Inspect execution history and telemetry payloads stored in PostgreSQL.</p>
              </div>
              <button type="button" onClick={fetchAuditLogs} className="btn-secondary">
                Refresh Logs
              </button>
            </div>

            <div className="code-container">
              <pre>{JSON.stringify(auditLogs, null, 2)}</pre>
            </div>
          </div>
        )}

        {/* --- CHAT MEMORY TAB --- */}
        {activeTab === "chat" && (
          <div className="module-content">
            <div className="module-header flex-between">
              <div>
                <h2>PostgreSQL Chat Memory</h2>
                <p>Review multi-turn conversational history across sessions.</p>
              </div>
              <button type="button" onClick={fetchChatHistory} className="btn-secondary">
                Refresh History
              </button>
            </div>

            <div className="chat-history-container">
              {chatHistory.length === 0 ? (
                <p className="empty-text">No chat history found.</p>
              ) : (
                chatHistory.map((msg, idx) => (
                  <div key={idx} className="chat-message-row">
                    <div className="chat-meta">
                      <span className={msg.role === "user" ? "role-user" : "role-ai"}>
                        {msg.role === "user" ? "USER" : "KALKI"}
                      </span>
                      <span className="chat-time">{msg.timestamp}</span>
                    </div>
                    <div className="chat-text">{msg.content}</div>
                  </div>
                ))
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}