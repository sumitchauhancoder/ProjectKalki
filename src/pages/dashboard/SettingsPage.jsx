import React, { useState, useEffect } from "react";
import { SettingsIcon, EyeIcon, EyeOffIcon } from "../../components/common/Icons";

export default function SettingsPage() {
  const [geminiKey, setGeminiKey] = useState("");
  const [groqKey, setGroqKey] = useState("");
  const [voiceLang, setVoiceLang] = useState("en-IN");

  const [showGemini, setShowGemini] = useState(false);
  const [showGroq, setShowGroq] = useState(false);

  const [loading, setLoading] = useState(true);
  const [savingKeys, setSavingKeys] = useState(false);
  const [savingPrefs, setSavingPrefs] = useState(false);

  const [keyNotice, setKeyNotice] = useState({ type: "", message: "" });
  const [prefNotice, setPrefNotice] = useState({ type: "", message: "" });

  useEffect(() => {
    const fetchSettings = async () => {
      try {
        setLoading(true);
        const res = await fetch("http://127.0.0.1:8000/settings");
        if (res.ok) {
          const data = await res.json();
          if (data.gemini_api_key) setGeminiKey(data.gemini_api_key);
          if (data.groq_api_key) setGroqKey(data.groq_api_key);
          if (data.voice_language) setVoiceLang(data.voice_language);
        }
      } catch (err) {
        setKeyNotice({ type: "error", message: "Failed to load current settings." });
      } finally {
        setLoading(false);
      }
    };

    fetchSettings();
  }, []);

  const handleSaveKeys = async (e) => {
    e.preventDefault();
    try {
      setSavingKeys(true);
      setKeyNotice({ type: "", message: "" });

      const res = await fetch("http://127.0.0.1:8000/settings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          gemini_api_key: geminiKey,
          groq_api_key: groqKey,
        }),
      });

      if (!res.ok) throw new Error("Failed to save API keys.");
      setKeyNotice({ type: "success", message: "API credentials saved locally on device." });
    } catch (err) {
      setKeyNotice({ type: "error", message: err.message || "Failed to update API keys." });
    } finally {
      setSavingKeys(false);
    }
  };

  const handleSavePrefs = async (e) => {
    e.preventDefault();
    try {
      setSavingPrefs(true);
      setPrefNotice({ type: "", message: "" });

      const res = await fetch("http://127.0.0.1:8000/settings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          voice_language: voiceLang,
        }),
      });

      if (!res.ok) throw new Error("Failed to save preferences.");
      setPrefNotice({ type: "success", message: "Preferences updated successfully." });
    } catch (err) {
      setPrefNotice({ type: "error", message: err.message || "Failed to update preferences." });
    } finally {
      setSavingPrefs(false);
    }
  };

  return (
    <div style={{ maxWidth: "800px", margin: "0 auto", display: "flex", flexDirection: "column", gap: "24px" }}>
      <div>
        <h2 style={{ fontSize: "20px", fontWeight: "600", marginBottom: "4px" }}>Settings</h2>
        <p style={{ fontSize: "14px", color: "var(--text-secondary)" }}>
          Manage your local API integrations, keys, and speech preferences.
        </p>
      </div>

      {/* API Keys Section */}
      <div className="card">
        <h3 style={{ fontSize: "16px", fontWeight: "600", marginBottom: "6px" }}>LLM Providers & Keys</h3>
        <p style={{ fontSize: "13px", color: "var(--text-secondary)", marginBottom: "16px" }}>
          Project KALKI uses local execution and BYOK (Bring Your Own Key) architecture. Keys are stored on your device only in <code>%APPDATA%\KALKI\settings.json</code>.
        </p>

        {keyNotice.message && (
          <div
            style={{
              padding: "10px 14px",
              marginBottom: "16px",
              borderRadius: "4px",
              fontSize: "13px",
              background: keyNotice.type === "success" ? "rgba(39,174,96,0.1)" : "rgba(231,76,60,0.1)",
              border: `1px solid ${keyNotice.type === "success" ? "var(--success)" : "var(--danger)"}`,
              color: keyNotice.type === "success" ? "var(--success)" : "var(--danger)",
            }}
          >
            {keyNotice.message}
          </div>
        )}

        <form onSubmit={handleSaveKeys} style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          <div>
            <label style={{ display: "block", fontSize: "13px", fontWeight: "500", marginBottom: "6px" }}>
              Groq API Key (Primary Provider)
            </label>
            <div style={{ position: "relative" }}>
              <input
                type={showGroq ? "text" : "password"}
                placeholder="gsk_..."
                value={groqKey}
                onChange={(e) => setGroqKey(e.target.value)}
                style={{ width: "100%", paddingRight: "40px" }}
              />
              <button
                type="button"
                onClick={() => setShowGroq(!showGroq)}
                style={{
                  position: "absolute",
                  right: "10px",
                  top: "50%",
                  transform: "translateY(-50%)",
                  background: "none",
                  border: "none",
                  color: "var(--text-muted)",
                  cursor: "pointer",
                  display: "flex",
                }}
              >
                {showGroq ? <EyeOffIcon size={16} /> : <EyeIcon size={16} />}
              </button>
            </div>
          </div>

          <div>
            <label style={{ display: "block", fontSize: "13px", fontWeight: "500", marginBottom: "6px" }}>
              Google Gemini API Key (Fallback Provider)
            </label>
            <div style={{ position: "relative" }}>
              <input
                type={showGemini ? "text" : "password"}
                placeholder="AIza..."
                value={geminiKey}
                onChange={(e) => setGeminiKey(e.target.value)}
                style={{ width: "100%", paddingRight: "40px" }}
              />
              <button
                type="button"
                onClick={() => setShowGemini(!showGemini)}
                style={{
                  position: "absolute",
                  right: "10px",
                  top: "50%",
                  transform: "translateY(-50%)",
                  background: "none",
                  border: "none",
                  color: "var(--text-muted)",
                  cursor: "pointer",
                  display: "flex",
                }}
              >
                {showGemini ? <EyeOffIcon size={16} /> : <EyeIcon size={16} />}
              </button>
            </div>
          </div>

          <div style={{ display: "flex", justifyContent: "flex-end" }}>
            <button type="submit" className="btn btn-primary" disabled={savingKeys || loading}>
              {savingKeys ? "Saving..." : "Save API Keys"}
            </button>
          </div>
        </form>
      </div>

      {/* Voice Preferences Section */}
      <div className="card">
        <h3 style={{ fontSize: "16px", fontWeight: "600", marginBottom: "6px" }}>Voice & Speech Preferences</h3>
        <p style={{ fontSize: "13px", color: "var(--text-secondary)", marginBottom: "16px" }}>
          Default spoken language and neural text-to-speech configuration.
        </p>

        {prefNotice.message && (
          <div
            style={{
              padding: "10px 14px",
              marginBottom: "16px",
              borderRadius: "4px",
              fontSize: "13px",
              background: prefNotice.type === "success" ? "rgba(39,174,96,0.1)" : "rgba(231,76,60,0.1)",
              border: `1px solid ${prefNotice.type === "success" ? "var(--success)" : "var(--danger)"}`,
              color: prefNotice.type === "success" ? "var(--success)" : "var(--danger)",
            }}
          >
            {prefNotice.message}
          </div>
        )}

        <form onSubmit={handleSavePrefs} style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          <div>
            <label style={{ display: "block", fontSize: "13px", fontWeight: "500", marginBottom: "6px" }}>
              Default Spoken Language
            </label>
            <select
              value={voiceLang}
              onChange={(e) => setVoiceLang(e.target.value)}
              style={{ width: "100%", maxWidth: "320px" }}
            >
              <option value="en-IN">English (India) — en-IN-NeerjaNeural</option>
              <option value="hi-IN">Hindi (India) — hi-IN-MadhurNeural</option>
              <option value="kn-IN">Kannada (India) — kn-IN-GaganNeural</option>
            </select>
          </div>

          <div style={{ display: "flex", justifyContent: "flex-end" }}>
            <button type="submit" className="btn btn-primary" disabled={savingPrefs || loading}>
              {savingPrefs ? "Saving..." : "Save Preferences"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
