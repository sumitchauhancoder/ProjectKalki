import React, { useState, useRef, useEffect } from "react";
import { API_BASE_URL } from "../../config";
import {
  MicIcon,
  StopIcon,
  PlayIcon,
  CameraIcon,
  TargetIcon,
  ChevronDownIcon,
  ChevronUpIcon
} from "../../components/common/Icons";

export const ControlCenterPage = () => {
  const [status, setStatus] = useState("System Ready");
  const [transcript, setTranscript] = useState("");
  const [manualCommand, setManualCommand] = useState("");
  const [listening, setListening] = useState(false);
  const [screenSharing, setScreenSharing] = useState(false);
  const [visionAnalysis, setVisionAnalysis] = useState(null);
  const [showVisionDetails, setShowVisionDetails] = useState(false);
  const [language, setLanguage] = useState("en-IN");

  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const streamRef = useRef(null);

  // Load language preference
  useEffect(() => {
    const fetchSettings = async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/settings`);
        if (res.ok) {
          const data = await res.json();
          if (data.language) setLanguage(data.language);
        }
      } catch (err) {
        // Fallback default
      }
    };
    fetchSettings();
  }, []);

  const handleLanguageChange = async (newLang) => {
    setLanguage(newLang);
    try {
      await fetch(`${API_BASE_URL}/settings`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ language: newLang })
      });
    } catch (err) {
      console.error("Failed to update language:", err);
    }
  };

  const handleStop = async () => {
    try {
      await fetch(`${API_BASE_URL}/stop`, { method: "POST" });
    } catch (err) {
      console.error("Stop command error:", err);
    }
    setStatus("Stopped.");
    setListening(false);
  };

  const sendStreamingCommand = async (commandText) => {
    setStatus("Thinking...");
    let receivedAnyText = false;
    let accumulatedText = "";

    try {
      const response = await fetch(`${API_BASE_URL}/chat-stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command: commandText })
      });

      if (!response.ok || !response.body) {
        throw new Error(`Server status ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop();

        for (const line of lines) {
          const trimmed = line.trim();
          if (trimmed.startsWith("data: ")) {
            const dataStr = trimmed.slice(6);
            if (dataStr === "[DONE]") continue;

            try {
              const parsed = JSON.parse(dataStr);
              if (parsed.status === "done") continue;
              if (parsed.text) {
                receivedAnyText = true;
                accumulatedText = accumulatedText
                  ? `${accumulatedText} ${parsed.text.trim()}`
                  : parsed.text.trim();
                setStatus(accumulatedText);
              }
            } catch (jsonErr) {
              if (dataStr && !dataStr.startsWith("{")) {
                receivedAnyText = true;
                accumulatedText = accumulatedText ? `${accumulatedText} ${dataStr}` : dataStr;
                setStatus(accumulatedText);
              }
            }
          }
        }
      }

      if (!receivedAnyText) {
        setStatus("Command completed with no text response.");
      }
    } catch (err) {
      setStatus(`Error: ${err.message}`);
    }
  };

  const handleManualSubmit = (e) => {
    e.preventDefault();
    if (!manualCommand.trim()) return;
    const cmd = manualCommand.trim();
    setTranscript(cmd);
    setManualCommand("");
    sendStreamingCommand(cmd);
  };

  const triggerBackendVoice = async () => {
    setListening(true);
    setStatus("Listening (4s)...");
    try {
      const response = await fetch(`${API_BASE_URL}/listen-voice`, {
        method: "POST"
      });

      if (!response.ok) {
        throw new Error(`Server returned ${response.status}`);
      }

      const contentType = response.headers.get("content-type") || "";
      if (contentType.includes("application/json")) {
        const data = await response.json();
        if (data.transcript) {
          setTranscript(data.transcript);
        }
        setStatus(data.reply || data.executed || "Speech processed.");
      } else if (response.body) {
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        let accumulatedText = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop();

          for (const line of lines) {
            const trimmed = line.trim();
            if (trimmed.startsWith("data: ")) {
              const dataStr = trimmed.slice(6);
              try {
                const parsed = JSON.parse(dataStr);
                if (parsed.status === "done") continue;
                if (parsed.transcript) {
                  setTranscript(parsed.transcript);
                }
                if (parsed.text) {
                  accumulatedText = accumulatedText
                    ? `${accumulatedText} ${parsed.text}`
                    : parsed.text;
                  setStatus(accumulatedText);
                }
              } catch (e) {}
            }
          }
        }
      }
    } catch (err) {
      setStatus("Failed to access backend voice service");
    } finally {
      setListening(false);
    }
  };

  const startScreenCapture = async () => {
    try {
      const stream = await navigator.mediaDevices.getDisplayMedia({
        video: true,
        audio: false
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
      const response = await fetch(`${API_BASE_URL}/process-frame`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ image_base64: base64Image })
      });
      const data = await response.json();
      setVisionAnalysis(data);
      setShowVisionDetails(true);
      setStatus("Frame Analysis Complete");
    } catch (err) {
      setStatus("Failed to process frame on backend");
    }
  };

  const handleAnalyzeAndClick = async () => {
    if (!videoRef.current || !screenSharing) {
      setStatus("Please start screen share first.");
      return;
    }

    setStatus("Capturing screen and analyzing UI elements...");
    try {
      const video = videoRef.current;
      const canvas = canvasRef.current;
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      const ctx = canvas.getContext("2d");
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
      const base64Image = canvas.toDataURL("image/jpeg", 0.85);

      const response = await fetch(`${API_BASE_URL}/process-frame`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ image_base64: base64Image })
      });

      const data = await response.json();
      setVisionAnalysis(data);

      if (data.bounding_boxes && data.bounding_boxes.length > 0) {
        setStatus("Target UI elements located. Executing visual click...");
        const clickRes = await fetch(`${API_BASE_URL}/visual-click`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            box_index: 0,
            bounding_boxes: data.bounding_boxes
          })
        });
        const clickData = await clickRes.json();
        setStatus(clickData.message || "Visual click dispatched.");
      } else {
        setStatus("No interactive elements detected on frame.");
      }
    } catch (err) {
      setStatus(`Target Click failed: ${err.message}`);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      {/* Engine Status Area (Fixed Top Bar) */}
      <div className="card" style={{ padding: "16px 20px" }}>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
          <div>
            <div style={{ fontSize: "11px", fontWeight: "600", textTransform: "uppercase", color: "var(--text-muted)", letterSpacing: "0.5px", marginBottom: "4px" }}>
              Engine Status
            </div>
            <div style={{ fontSize: "14px", fontWeight: "500", color: "var(--text-primary)", wordBreak: "break-word" }}>
              {status}
            </div>
          </div>
          <div>
            <div style={{ fontSize: "11px", fontWeight: "600", textTransform: "uppercase", color: "var(--text-muted)", letterSpacing: "0.5px", marginBottom: "4px" }}>
              Last Input
            </div>
            <div style={{ fontSize: "14px", color: "var(--accent)", fontWeight: "500", wordBreak: "break-word" }}>
              {transcript || "None"}
            </div>
          </div>
        </div>
      </div>

      {/* Main Command Input & Controls */}
      <div className="card">
        <h2 style={{ fontSize: "15px", fontWeight: "600", marginBottom: "16px" }}>
          Execute Command
        </h2>
        <form onSubmit={handleManualSubmit} style={{ display: "flex", gap: "8px", marginBottom: "16px" }}>
          <input
            type="text"
            value={manualCommand}
            onChange={(e) => setManualCommand(e.target.value)}
            placeholder="Try: open notepad, volume up, take screenshot..."
            style={{ flex: 1 }}
          />
          <button type="submit" className="btn btn-primary" style={{ whiteSpace: "nowrap" }}>
            Execute
          </button>
        </form>

        {/* Voice Action Bar */}
        <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: "12px", paddingTop: "12px", borderTop: "1px solid var(--border)" }}>
          <button
            type="button"
            onClick={triggerBackendVoice}
            disabled={listening}
            className="btn btn-secondary"
            style={{ flex: 1, minWidth: "150px" }}
          >
            <MicIcon size={16} />
            {listening ? "Listening (4s)..." : "Speak Command"}
          </button>

          <button
            type="button"
            onClick={handleStop}
            className="btn btn-danger"
            style={{ minWidth: "80px" }}
          >
            <StopIcon size={16} /> Stop
          </button>

          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <label style={{ fontSize: "12px", color: "var(--text-secondary)", whiteSpace: "nowrap" }}>
              Voice Lang:
            </label>
            <select
              value={language}
              onChange={(e) => handleLanguageChange(e.target.value)}
              style={{ width: "auto", padding: "6px 10px" }}
            >
              <option value="en-IN">English (India)</option>
              <option value="hi-IN">Hindi</option>
              <option value="kn-IN">Kannada</option>
            </select>
          </div>
        </div>
      </div>

      {/* Vision & Screen Automation */}
      <div className="card">
        <h2 style={{ fontSize: "15px", fontWeight: "600", marginBottom: "16px" }}>
          Screen & Vision Automation
        </h2>
        <div style={{ display: "flex", flexWrap: "wrap", gap: "10px", marginBottom: "16px" }}>
          <button
            type="button"
            onClick={screenSharing ? stopScreenCapture : startScreenCapture}
            className="btn btn-secondary"
          >
            <CameraIcon size={16} />
            {screenSharing ? "Stop Screen Share" : "Start Screen Share"}
          </button>

          <button
            type="button"
            onClick={analyzeCurrentFrame}
            disabled={!screenSharing}
            className="btn btn-secondary"
          >
            <TargetIcon size={16} /> Analyze Frame (OpenCV)
          </button>

          <button
            type="button"
            onClick={handleAnalyzeAndClick}
            disabled={!screenSharing}
            className="btn btn-primary"
          >
            Analyze & Target Click
          </button>
        </div>

        <canvas ref={canvasRef} style={{ display: "none" }} />

        {screenSharing && (
          <div style={{ marginTop: "16px", borderRadius: "var(--radius-card)", overflow: "hidden", border: "1px solid var(--border)" }}>
            <video ref={videoRef} autoPlay playsInline muted style={{ width: "100%", maxHeight: "360px", display: "block", backgroundColor: "#000" }} />
          </div>
        )}

        {/* Collapsible OpenCV Analysis Results (Closed by default) */}
        {visionAnalysis && (
          <div style={{ marginTop: "16px", border: "1px solid var(--border)", borderRadius: "var(--radius-card)", overflow: "hidden" }}>
            <button
              type="button"
              onClick={() => setShowVisionDetails(!showVisionDetails)}
              style={{
                width: "100%",
                padding: "12px 16px",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                background: "var(--bg-secondary)",
                border: "none",
                cursor: "pointer",
                color: "var(--text-primary)",
                fontWeight: "600",
                fontSize: "13px"
              }}
            >
              <span>OpenCV Analysis Results ({visionAnalysis.bounding_boxes?.length || 0} boxes detected)</span>
              {showVisionDetails ? <ChevronUpIcon size={16} /> : <ChevronDownIcon size={16} />}
            </button>
            {showVisionDetails && (
              <pre style={{
                padding: "16px",
                margin: 0,
                fontSize: "12px",
                backgroundColor: "var(--bg)",
                overflowX: "auto",
                color: "var(--text-secondary)"
              }}>
                {JSON.stringify(visionAnalysis, null, 2)}
              </pre>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default ControlCenterPage;
