import React, { useState, useEffect, useRef } from "react";
import { API_BASE_URL } from "./config";
import Home from "./components/Home";
import Login from "./components/Login";
import Dashboard from "./components/Dashboard";

export default function App() {
  // Navigation state: 'home', 'login', or 'dashboard'
  const [currentView, setCurrentView] = useState("home");
  const [currentUser, setCurrentUser] = useState(null);

  const [activeTab, setActiveTab] = useState("controls");
  const [transcript, setTranscript] = useState("");
  const [manualCommand, setManualCommand] = useState("");
  const [status, setStatus] = useState("Idle");
  const [listening, setListening] = useState(false);
  const [screenSharing, setScreenSharing] = useState(false);
  const [visionAnalysis, setVisionAnalysis] = useState(null);

  const [macros, setMacros] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);
  const [chatHistory, setChatHistory] = useState([]);
  const [language, setLanguage] = useState("en-IN");

  const [newTrigger, setNewTrigger] = useState("");
  const [newActionType, setNewActionType] = useState("launch_app");
  const [newPayloadVal, setNewPayloadVal] = useState("calc.exe");

  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const streamRef = useRef(null);

  useEffect(() => {
    if (currentView === "dashboard") {
      fetchMacros();
      fetchAuditLogs();
      fetchChatHistory();
      fetchSettings();
    }
  }, [currentView]);

  const fetchSettings = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/settings`);
      if (res.ok) {
        const data = await res.json();
        if (data.language) setLanguage(data.language);
      }
    } catch (err) {
      console.error("Failed to fetch settings:", err);
    }
  };

  const handleLanguageChange = async (newLang) => {
    setLanguage(newLang);
    try {
      await fetch(`${API_BASE_URL}/settings`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ language: newLang }),
      });
    } catch (err) {
      console.error("Failed to update language setting:", err);
    }
  };

  const fetchMacros = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/macros`);
      const data = await res.json();
      setMacros(data);
    } catch (err) {
      console.error("Failed to fetch macros:", err);
    }
  };

  const fetchAuditLogs = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/audit-logs`);
      const data = await res.json();
      setAuditLogs(data);
    } catch (err) {
      console.error("Failed to fetch audit logs:", err);
    }
  };

  const fetchChatHistory = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/chat-history`);
      const data = await res.json();
      setChatHistory(data);
    } catch (err) {
      console.error("Failed to fetch chat history:", err);
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
      const res = await fetch(`${API_BASE_URL}/macros`, {
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

  const handleStop = async () => {
    try {
      await fetch(`${API_BASE_URL}/stop`, { method: "POST" });
    } catch (err) {
      console.error("Stop command error:", err);
    }
    setStatus("KALKI: Stopped.");
    setListening(false);
  };

  const triggerBackendVoice = async () => {
    setListening(true);
    setStatus("Listening via Python Core Mic (4s)...");
    try {
      const response = await fetch(`${API_BASE_URL}/listen-voice`, {
        method: "POST",
      });

      if (!response.ok) {
        throw new Error(`Server returned status ${response.status}`);
      }

      const contentType = response.headers.get("content-type") || "";
      if (contentType.includes("application/json")) {
        const data = await response.json();
        if (data.transcript) {
          setTranscript(data.transcript);
          setStatus(`Heard: ${data.transcript}`);
          await new Promise((resolve) => setTimeout(resolve, 600));
        }
        const responseText =
          data.reply || data.executed || data.message || "Speech processed";
        setStatus(`KALKI: ${responseText}`);
      } else if (response.body) {
        // Handle SSE streaming voice response
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
              if (dataStr === "[DONE]") continue;

              try {
                const parsed = JSON.parse(dataStr);
                if (parsed.status === "done") continue;
                if (parsed.transcript) {
                  setTranscript(parsed.transcript);
                  setStatus(`Heard: ${parsed.transcript}`);
                }
                if (parsed.text) {
                  accumulatedText = accumulatedText
                    ? `${accumulatedText} ${parsed.text}`
                    : parsed.text;
                  setStatus(`KALKI: ${accumulatedText}`);
                }
              } catch (jsonErr) {
                // Ignore non-json lines
              }
            }
          }
        }
      }

      fetchAuditLogs();
      fetchChatHistory();
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
      const response = await fetch(`${API_BASE_URL}/execute-command`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command: commandText }),
      });

      if (!response.ok) {
        throw new Error(`Server returned status ${response.status}`);
      }

      const data = await response.json();
      const responseText =
        data.reply || data.executed || data.message || "Command processed.";
      setStatus(`KALKI: ${responseText}`);
      fetchAuditLogs();
      fetchChatHistory();
    } catch (err) {
      console.error("Error sending command:", err);
      setStatus(`KALKI: Error - ${err.message}`);
    }
  };

  const sendStreamingCommandToBackend = async (commandText) => {
    setStatus("KALKI: Thinking...");
    let receivedAnyText = false;
    let accumulatedText = "";

    try {
      const response = await fetch(`${API_BASE_URL}/chat-stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command: commandText }),
      });

      if (!response.ok || !response.body) {
        throw new Error(`Server returned status ${response.status}`);
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
                setStatus(`KALKI: ${accumulatedText}`);
              }
            } catch (jsonErr) {
              if (dataStr && !dataStr.startsWith("{")) {
                receivedAnyText = true;
                accumulatedText = accumulatedText
                  ? `${accumulatedText} ${dataStr}`
                  : dataStr;
                setStatus(`KALKI: ${accumulatedText}`);
              }
            }
          }
        }
      }

      if (!receivedAnyText) {
        await sendCommandToBackend(commandText);
        return;
      }

      fetchAuditLogs();
      fetchChatHistory();
    } catch (err) {
      console.warn("Streaming failed, falling back to /execute-command:", err);
      if (!receivedAnyText) {
        await sendCommandToBackend(commandText);
      }
    }
  };

  const handleManualSubmit = (e) => {
    e.preventDefault();
    if (!manualCommand.trim()) return;
    sendStreamingCommandToBackend(manualCommand);
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
      const response = await fetch(`${API_BASE_URL}/process-frame`, {
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

  const handleAnalyzeAndClick = async () => {
    if (!videoRef.current || !screenSharing) {
      setStatus("KALKI: Please start screen share first.");
      return;
    }

    setStatus("KALKI: Capturing screen and analyzing UI elements...");
    try {
      const video = videoRef.current;
      const canvas = document.createElement("canvas");
      canvas.width = video.videoWidth || window.innerWidth;
      canvas.height = video.videoHeight || window.innerHeight;

      const ctx = canvas.getContext("2d");
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

      const base64Image = canvas.toDataURL("image/jpeg", 0.8);

      const response = await fetch(`${API_BASE_URL}/process-frame`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ image_base64: base64Image }),
      });
      const data = await response.json();

      if (data.sample_boxes && data.sample_boxes.length > 0) {
        const clickRes = await fetch(`${API_BASE_URL}/visual-click`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            box_index: 0,
            bounding_boxes: data.sample_boxes,
          }),
        });
        const clickData = await clickRes.json();
        setStatus(`KALKI: ${clickData.reply}`);
      } else {
        setStatus("KALKI: Visual Core found no interactive UI elements.");
      }
    } catch (err) {
      console.error("Visual targeting error:", err);
      setStatus("KALKI: Failed visual analysis");
    }
  };

  // --- RENDER ROUTING ---
  if (currentView === "home") {
    return <Home onNavigate={(view) => setCurrentView(view)} />;
  }

  if (currentView === "login") {
    return (
      <Login 
        onLoginSuccess={(user) => {
          setCurrentUser(user);
          setCurrentView("dashboard");
          setStatus("KALKI: Core session initialized.");
        }}
        onBackToHome={() => setCurrentView("home")} 
      />
    );
  }

  if (currentView === "dashboard") {
    return (
      <Dashboard
        currentUser={currentUser}
        onLogout={() => {
          setCurrentUser(null);
          setCurrentView("home");
        }}
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        status={status}
        transcript={transcript}
        manualCommand={manualCommand}
        setManualCommand={setManualCommand}
        handleManualSubmit={handleManualSubmit}
        triggerBackendVoice={triggerBackendVoice}
        listening={listening}
        screenSharing={screenSharing}
        startScreenCapture={startScreenCapture}
        stopScreenCapture={stopScreenCapture}
        analyzeCurrentFrame={analyzeCurrentFrame}
        handleAnalyzeAndClick={handleAnalyzeAndClick}
        canvasRef={canvasRef}
        videoRef={videoRef}
        visionAnalysis={visionAnalysis}
        macros={macros}
        newTrigger={newTrigger}
        setNewTrigger={setNewTrigger}
        newActionType={newActionType}
        setNewActionType={setNewActionType}
        newPayloadVal={newPayloadVal}
        setNewPayloadVal={setNewPayloadVal}
        handleAddMacro={handleAddMacro}
        auditLogs={auditLogs}
        fetchAuditLogs={fetchAuditLogs}
        chatHistory={chatHistory}
        fetchChatHistory={fetchChatHistory}
        language={language}
        handleLanguageChange={handleLanguageChange}
        handleStop={handleStop}
      />
    );
  }

  return null;
}
