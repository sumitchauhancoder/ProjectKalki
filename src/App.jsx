import React, { useState, useEffect, useRef } from "react";

export default function App() {
  const [activeTab, setActiveTab] = useState("controls");
  const [transcript, setTranscript] = useState("");
  const [manualCommand, setManualCommand] = useState("");
  const [status, setStatus] = useState("Idle");
  const [listening, setListening] = useState(false);
  const [screenSharing, setScreenSharing] = useState(false);
  const [visionAnalysis, setVisionAnalysis] = useState(null);

  const [macros, setMacros] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);
  const [newTrigger, setNewTrigger] = useState("");
  const [newActionType, setNewActionType] = useState("launch_app");
  const [newPayloadVal, setNewPayloadVal] = useState("calc.exe");

  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const streamRef = useRef(null);

  useEffect(() => {
    fetchMacros();
    fetchAuditLogs();
  }, []);

  const fetchMacros = async () => {
    try {
      const res = await fetch("http://127.0.0.1:8000/macros");
      const data = await res.json();
      setMacros(data);
    } catch (err) {
      console.error("Failed to fetch macros:", err);
    }
  };

  const fetchAuditLogs = async () => {
    try {
      const res = await fetch("http://127.0.0.1:8000/audit-logs");
      const data = await res.json();
      setAuditLogs(data);
    } catch (err) {
      console.error("Failed to fetch audit logs:", err);
    }
  };

  const handleAddMacro = async (e) => {
    e.preventDefault();
    if (!newTrigger.trim()) return;

    let payloadObj = {};
    if (newActionType === "launch_app") payloadObj = { path: newPayloadVal };
    else if (newActionType === "hotkey")
      payloadObj = { keys: newPayloadVal.split("+") };
    else if (newActionType === "type_text")
      payloadObj = { text: newPayloadVal };

    try {
      const res = await fetch("http://127.0.0.1:8000/macros", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          trigger_phrase: newTrigger,
          action_type: newActionType,
          action_payload: payloadObj,
        }),
      });
      if (res.ok) {
        setNewTrigger("");
        fetchMacros();
        setStatus("Macro registered in PostgreSQL");
      }
    } catch (err) {
      console.error("Failed to add macro:", err);
    }
  };

  const triggerBackendVoice = async () => {
    setListening(true);
    setStatus("Listening via Python Core Mic (4s)...");
    try {
      const response = await fetch("http://127.0.0.1:8000/listen-voice", {
        method: "POST",
      });
      const data = await response.json();

      if (data.transcript) setTranscript(data.transcript);

      const responseText =
        data.reply || data.executed || data.message || "Speech processed";
      setStatus(`KALKI: ${responseText}`);
      fetchAuditLogs();
    } catch (err) {
      console.error("Voice listening error:", err);
      setStatus("Failed to access backend voice service");
    } finally {
      setListening(false);
    }
  };

  const sendCommandToBackend = async (commandText) => {
    setStatus("KALKI: Thinking...");
    try {
      const response = await fetch("http://127.0.0.1:8000/execute-command", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command: commandText }),
      });
      const data = await response.json();

      const responseText =
        data.reply || data.executed || data.message || "Command processed.";
      setStatus(`KALKI: ${responseText}`);
      fetchAuditLogs();
    } catch (err) {
      console.error("Error sending command:", err);
      setStatus("KALKI: Failed to reach backend core");
    }
  };

  const handleManualSubmit = (e) => {
    e.preventDefault();
    if (!manualCommand.trim()) return;
    sendCommandToBackend(manualCommand);
    setTranscript(manualCommand);
    setManualCommand("");
  };

  const startScreenCapture = async () => {
    try {
      const stream = await navigator.mediaDevices.getDisplayMedia({
        video: true,
        audio: false,
      });
      streamRef.current = stream;
      setScreenSharing(true);
      setStatus("Screen Capture Active");

      setTimeout(() => {
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          videoRef.current.play().catch((err) => console.error(err));
        }
      }, 100);

      stream.getVideoTracks()[0].onended = () => {
        setScreenSharing(false);
        setStatus("Screen Share Ended");
      };
    } catch (err) {
      setStatus(`Screen capture error: ${err.message}`);
    }
  };

  const stopScreenCapture = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    setScreenSharing(false);
    setStatus("Screen Share Stopped");
  };

  const analyzeCurrentFrame = async () => {
    if (!videoRef.current || !canvasRef.current || !screenSharing) return;

    const video = videoRef.current;
    const canvas = canvasRef.current;
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    const ctx = canvas.getContext("2d");
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    const base64Image = canvas.toDataURL("image/jpeg", 0.85);

    try {
      setStatus("Analyzing screen frame with OpenCV...");
      const response = await fetch("http://127.0.0.1:8000/process-frame", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ image_base64: base64Image }),
      });

      const data = await response.json();
      setVisionAnalysis(data);
      setStatus("Frame Analysis Complete");
    } catch (err) {
      setStatus("Failed to process frame on backend");
    }
  };

  return (
    <div
      style={{
        padding: "2rem",
        fontFamily: "system-ui, sans-serif",
        color: "#1a1a1a",
      }}
    >
      <h1>KALKI Assistant Core</h1>

      <div
        style={{
          display: "flex",
          gap: "1rem",
          borderBottom: "2px solid #e4e4e7",
          marginBottom: "1.5rem",
        }}
      >
        <button
          onClick={() => setActiveTab("controls")}
          style={{
            padding: "0.6rem 1.2rem",
            cursor: "pointer",
            borderBottom:
              activeTab === "controls" ? "2px solid #2563eb" : "none",
            fontWeight: activeTab === "controls" ? "bold" : "normal",
          }}
        >
          Control Center
        </button>
        <button
          onClick={() => setActiveTab("macros")}
          style={{
            padding: "0.6rem 1.2rem",
            cursor: "pointer",
            borderBottom: activeTab === "macros" ? "2px solid #2563eb" : "none",
            fontWeight: activeTab === "macros" ? "bold" : "normal",
          }}
        >
          Voice Macros ({macros.length})
        </button>
        <button
          onClick={() => setActiveTab("logs")}
          style={{
            padding: "0.6rem 1.2rem",
            cursor: "pointer",
            borderBottom: activeTab === "logs" ? "2px solid #2563eb" : "none",
            fontWeight: activeTab === "logs" ? "bold" : "normal",
          }}
        >
          Audit Logs ({auditLogs.length})
        </button>
      </div>

      <div
        style={{
          padding: "1rem",
          background: "#f4f4f5",
          borderRadius: "8px",
          marginBottom: "1.5rem",
        }}
      >
        <p>
          Engine Status: <strong>{status}</strong>
        </p>
        <p>
          Last Command: <em>{transcript || "None"}</em>
        </p>
      </div>

      {activeTab === "controls" && (
        <>
          <form
            onSubmit={handleManualSubmit}
            style={{ display: "flex", gap: "0.5rem", marginBottom: "1.5rem" }}
          >
            <input
              type="text"
              value={manualCommand}
              onChange={(e) => setManualCommand(e.target.value)}
              placeholder="Type command (e.g., 'you have to open calculator')..."
              style={{
                flex: 1,
                padding: "0.6rem",
                fontSize: "1rem",
                borderRadius: "4px",
                border: "1px solid #ccc",
              }}
            />
            <button
              type="submit"
              style={{
                padding: "0.6rem 1.2rem",
                fontSize: "1rem",
                cursor: "pointer",
              }}
            >
              Execute
            </button>
          </form>

          <div style={{ display: "flex", gap: "1rem", marginBottom: "1.5rem" }}>
            <button
              onClick={triggerBackendVoice}
              disabled={listening}
              style={{
                padding: "0.6rem 1.2rem",
                fontSize: "1rem",
                cursor: listening ? "not-allowed" : "pointer",
              }}
            >
              {listening ? "Listening (4s)..." : "Speak Command"}
            </button>

            <button
              onClick={screenSharing ? stopScreenCapture : startScreenCapture}
              style={{
                padding: "0.6rem 1.2rem",
                fontSize: "1rem",
                cursor: "pointer",
              }}
            >
              {screenSharing ? "Stop Screen Share" : "Start Screen Share"}
            </button>

            <button
              onClick={analyzeCurrentFrame}
              disabled={!screenSharing}
              style={{
                padding: "0.6rem 1.2rem",
                fontSize: "1rem",
                cursor: screenSharing ? "pointer" : "not-allowed",
              }}
            >
              Analyze Frame (OpenCV)
            </button>
          </div>

          <canvas ref={canvasRef} style={{ display: "none" }} />

          {screenSharing && (
            <div style={{ marginTop: "1rem" }}>
              <h3>Active Screen Feed</h3>
              <video
                ref={videoRef}
                autoPlay
                playsInline
                muted
                style={{
                  width: "100%",
                  maxHeight: "400px",
                  borderRadius: "8px",
                  border: "1px solid #ccc",
                  backgroundColor: "#000",
                }}
              />
            </div>
          )}

          {visionAnalysis && (
            <div
              style={{
                marginTop: "1.5rem",
                padding: "1rem",
                background: "#eef2ff",
                borderRadius: "8px",
              }}
            >
              <h3>OpenCV Analysis Results</h3>
              <pre
                style={{
                  background: "#1e293b",
                  color: "#f8fafc",
                  padding: "1rem",
                  borderRadius: "6px",
                }}
              >
                {JSON.stringify(visionAnalysis, null, 2)}
              </pre>
            </div>
          )}
        </>
      )}

      {activeTab === "macros" && (
        <div>
          <h3>Add Voice Macro to PostgreSQL</h3>
          <form
            onSubmit={handleAddMacro}
            style={{
              display: "flex",
              gap: "0.5rem",
              marginBottom: "1.5rem",
              flexWrap: "wrap",
            }}
          >
            <input
              type="text"
              placeholder="Trigger Phrase (e.g., 'dev mode')"
              value={newTrigger}
              onChange={(e) => setNewTrigger(e.target.value)}
              style={{ padding: "0.5rem", flex: 1 }}
              required
            />
            <select
              value={newActionType}
              onChange={(e) => setNewActionType(e.target.value)}
              style={{ padding: "0.5rem" }}
            >
              <option value="launch_app">Launch Application</option>
              <option value="hotkey">Keyboard Hotkey</option>
              <option value="type_text">Type Text</option>
            </select>
            <input
              type="text"
              placeholder="Payload (e.g., 'calc.exe' or 'win+r')"
              value={newPayloadVal}
              onChange={(e) => setNewPayloadVal(e.target.value)}
              style={{ padding: "0.5rem", flex: 1 }}
              required
            />
            <button
              type="submit"
              style={{ padding: "0.5rem 1rem", cursor: "pointer" }}
            >
              Add Macro
            </button>
          </form>

          <h3>Registered Voice Macros</h3>
          <ul>
            {macros.map((m) => (
              <li key={m.id} style={{ marginBottom: "0.5rem" }}>
                <strong>"{m.trigger_phrase}"</strong> $\rightarrow${" "}
                <code>{m.action_type}</code> ({JSON.stringify(m.action_payload)}
                )
              </li>
            ))}
          </ul>
        </div>
      )}

      {activeTab === "logs" && (
        <div>
          <h3>Recent PostgreSQL Audit Logs</h3>
          <button
            onClick={fetchAuditLogs}
            style={{
              padding: "0.4rem 0.8rem",
              marginBottom: "1rem",
              cursor: "pointer",
            }}
          >
            Refresh Logs
          </button>
          <pre
            style={{
              background: "#1e293b",
              color: "#f8fafc",
              padding: "1rem",
              borderRadius: "6px",
              maxHeight: "400px",
              overflowY: "auto",
            }}
          >
            {JSON.stringify(auditLogs, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}
