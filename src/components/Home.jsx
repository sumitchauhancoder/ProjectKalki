import React from "react";
import "./Home.css";

export default function Home({ onNavigate }) {
  return (
    <div className="home-container">
      <div className="home-hero-glow"></div>
      
      <div className="home-content">
        <div className="badge-system">
          <span className="pulse-dot"></span>
          KALKI CORE ENGINE v1.0
        </div>

        <h1 className="home-title">
          Autonomous Multilingual <span className="highlight-red">AI Assistant</span>
        </h1>
        
        <p className="home-subtitle">
          Advanced J.A.R.V.I.S.-inspired desktop intelligence featuring hybrid local fast-path execution, 
          cloud reasoning fallbacks, and real-time computer vision UI targeting.
        </p>

        <div className="home-actions">
          <button 
            className="btn-primary-red" 
            onClick={() => onNavigate("login")}
          >
            Get Started &rarr;
          </button>
        </div>

        <div className="system-features-grid">
          <div className="feature-card">
            <h3>Hybrid Core</h3>
            <p>0ms local fast-path routing with resilient Gemini & Groq cloud failover.</p>
          </div>
          <div className="feature-card">
            <h3>Vision & Voice</h3>
            <p>OpenCV spatial bounding box targeting and neural text-to-speech feedback.</p>
          </div>
          <div className="feature-card">
            <h3>Persistent Memory</h3>
            <p>PostgreSQL-backed multi-turn chat history and secure macro auditing.</p>
          </div>
        </div>
      </div>
    </div>
  );
}