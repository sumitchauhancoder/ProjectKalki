import React from "react";
import { MicIcon } from "../../components/common/Icons";

export default function VoiceControlPage() {
  return (
    <div style={{ maxWidth: "600px", margin: "40px auto", textAlign: "center" }}>
      <div className="card" style={{ padding: "48px 24px" }}>
        <div
          style={{
            width: "64px",
            height: "64px",
            borderRadius: "50%",
            background: "var(--bg-secondary)",
            border: "1px solid var(--border)",
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            marginBottom: "20px",
            color: "var(--accent)",
          }}
        >
          <MicIcon size={32} />
        </div>
        <h2 style={{ fontSize: "20px", fontWeight: "600", marginBottom: "8px" }}>Voice Control</h2>
        <p style={{ color: "var(--text-secondary)", fontSize: "14px", marginBottom: "24px", lineHeight: "1.5" }}>
          Wake word detection and always-on hands-free voice commands are coming soon to Project KALKI.
        </p>
        <div
          style={{
            display: "inline-block",
            padding: "8px 16px",
            background: "var(--bg-secondary)",
            border: "1px solid var(--border)",
            borderRadius: "4px",
            fontSize: "12px",
            color: "var(--text-muted)",
          }}
        >
          Status: Planned for Next Iteration
        </div>
      </div>
    </div>
  );
}
