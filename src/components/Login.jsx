import React, { useState } from "react";
import "./Login.css";

export default function Login({ onLoginSuccess }) {
  const [authMode, setAuthMode] = useState("login"); // 'login' | 'register' | 'forgot'

  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const handleLoginSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setMessage("");
    try {
      const res = await fetch("http://localhost:8000/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ identifier, password }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Login failed");

      onLoginSuccess(data.user);
    } catch (err) {
      setError(err.message);
    }
  };

  const handleRegisterSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setMessage("");
    try {
      const res = await fetch("http://localhost:8000/api/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, username, email, password }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Registration failed");

      setMessage("Registration successful! Please sign in.");
      setAuthMode("login");
    } catch (err) {
      setError(err.message);
    }
  };

  const handleForgotSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setMessage("");
    try {
      const res = await fetch(
        "http://localhost:8000/api/auth/forgot-password",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email }),
        },
      );
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Request failed");

      setMessage(
        data.dev_reset_token
          ? `Dev Reset Token: ${data.dev_reset_token}`
          : data.message,
      );
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div className="auth-container">
      <div className="auth-card">
        <div className="auth-header">
          <span className="pulse-dot"></span>
          <h2>KALKI CORE</h2>
          <p>Autonomous Agent Control Center</p>
        </div>

        {error && <div className="alert-error">{error}</div>}
        {message && <div className="alert-success">{message}</div>}

        {authMode === "login" && (
          <form onSubmit={handleLoginSubmit} className="auth-form">
            <h3>Operator Sign In</h3>
            <div className="input-group">
              <label>Username or Email</label>
              <input
                type="text"
                value={identifier}
                onChange={(e) => setIdentifier(e.target.value)}
                placeholder="Enter username or email..."
                required
              />
            </div>
            <div className="input-group">
              <label>Password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                required
              />
            </div>
            <button type="submit" className="btn-primary-red">
              Sign In
            </button>
            <div className="auth-links">
              <button
                type="button"
                onClick={() => {
                  setAuthMode("forgot");
                  setMessage("");
                  setError("");
                }}
              >
                Forgot Password?
              </button>
              <button
                type="button"
                onClick={() => {
                  setAuthMode("register");
                  setMessage("");
                  setError("");
                }}
              >
                Create Account
              </button>
            </div>
          </form>
        )}

        {authMode === "register" && (
          <form onSubmit={handleRegisterSubmit} className="auth-form">
            <h3>New Operator Registration</h3>
            <div className="input-group">
              <label>Full Name</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="John Doe"
                required
              />
            </div>
            <div className="input-group">
              <label>Username</label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="johndoe"
                required
              />
            </div>
            <div className="input-group">
              <label>Email Address</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="john@example.com"
                required
              />
            </div>
            <div className="input-group">
              <label>Password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                required
              />
            </div>
            <button type="submit" className="btn-primary-red">
              Register Account
            </button>
            <div className="auth-links">
              <button
                type="button"
                onClick={() => {
                  setAuthMode("login");
                  setMessage("");
                  setError("");
                }}
              >
                Already have an account? Sign In
              </button>
            </div>
          </form>
        )}

        {authMode === "forgot" && (
          <form onSubmit={handleForgotSubmit} className="auth-form">
            <h3>Reset Password</h3>
            <div className="input-group">
              <label>Registered Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="john@example.com"
                required
              />
            </div>
            <button type="submit" className="btn-primary-red">
              Send Reset Instructions
            </button>
            <div className="auth-links">
              <button
                type="button"
                onClick={() => {
                  setAuthMode("login");
                  setMessage("");
                  setError("");
                }}
              >
                Back to Sign In
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
