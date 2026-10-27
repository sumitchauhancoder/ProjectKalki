import React, { useState } from "react";
import "./Login.css";

export default function Login({ onLoginSuccess, onBackToHome }) {
  const [isRegister, setIsRegister] = useState(false);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!username || !password) {
      alert("Please fill in all fields.");
      return;
    }
    // Proceed to main assistant dashboard
    onLoginSuccess({ username });
  };

  return (
    <div className="login-container">
      <div className="login-card">
        <button className="btn-back" onClick={onBackToHome}>
          &larr; Back
        </button>

        <div className="login-header">
          <span className="badge-mini">KALKI SECURITY</span>
          <h2>{isRegister ? "Create Account" : "Access Core"}</h2>
          <p>
            {isRegister
              ? "Register a new local operator profile."
              : "Enter credentials to access your desktop assistant."}
          </p>
        </div>

        <form onSubmit={handleSubmit} className="login-form">
          <div className="input-group">
            <label>Operator Username</label>
            <input
              type="text"
              placeholder="e.g. Sumit"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
            />
          </div>

          <div className="input-group">
            <label>Security Password</label>
            <input
              type="password"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>

          <button type="submit" className="btn-primary-red full-width">
            {isRegister ? "Register & Enter" : "Authorize Access"}
          </button>
        </form>

        <div className="login-footer">
          <p>
            {isRegister ? "Already have a profile?" : "New operator?"}{" "}
            <span
              className="toggle-link"
              onClick={() => setIsRegister(!isRegister)}
            >
              {isRegister ? "Sign In" : "Create Account"}
            </span>
          </p>
        </div>
      </div>
    </div>
  );
}