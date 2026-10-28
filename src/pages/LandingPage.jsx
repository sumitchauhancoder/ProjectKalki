import React, { useState } from "react";
import { Link } from "react-router-dom";
import { useTheme } from "../context/ThemeContext";
import { SunIcon, MoonIcon, MicIcon, TerminalIcon, ShieldIcon, MenuIcon, XIcon } from "../components/common/Icons";

export const LandingPage = () => {
  const { theme, toggleTheme } = useTheme();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const scrollToFeatures = (e) => {
    e.preventDefault();
    const el = document.getElementById("features");
    if (el) el.scrollIntoView({ behavior: "smooth" });
  };

  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column", backgroundColor: "var(--bg)" }}>
      {/* Top Navbar */}
      <header style={{
        borderBottom: "1px solid var(--border)",
        backgroundColor: "var(--bg)",
        position: "sticky",
        top: 0,
        zIndex: 100
      }}>
        <div className="container" style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          height: "64px"
        }}>
          <Link to="/" style={{ fontSize: "18px", fontWeight: "700", letterSpacing: "1px", color: "var(--text-primary)" }}>
            KALKI
          </Link>

          {/* Desktop Nav */}
          <div style={{ display: "none", alignItems: "center", gap: "16px" }} className="desktop-nav">
            <button
              onClick={toggleTheme}
              className="btn btn-outline btn-sm"
              aria-label="Toggle theme"
              title="Toggle Light/Dark Theme"
              style={{ padding: "6px 10px" }}
            >
              {theme === "dark" ? <SunIcon size={16} /> : <MoonIcon size={16} />}
            </button>
            <Link to="/login" className="btn btn-outline btn-sm">
              Sign In
            </Link>
            <Link to="/register" className="btn btn-primary btn-sm">
              Get Started
            </Link>
          </div>

          {/* Mobile Menu Button */}
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="btn btn-outline btn-sm mobile-menu-btn"
            style={{ display: "flex", padding: "6px" }}
            aria-label="Toggle Navigation Menu"
          >
            {mobileMenuOpen ? <XIcon size={18} /> : <MenuIcon size={18} />}
          </button>
        </div>

        {/* Mobile Dropdown */}
        {mobileMenuOpen && (
          <div style={{
            borderTop: "1px solid var(--border)",
            padding: "16px",
            display: "flex",
            flexDirection: "column",
            gap: "12px",
            backgroundColor: "var(--bg-secondary)"
          }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontSize: "13px", color: "var(--text-secondary)" }}>Theme</span>
              <button onClick={toggleTheme} className="btn btn-outline btn-sm">
                {theme === "dark" ? <SunIcon size={14} /> : <MoonIcon size={14} />} {theme === "dark" ? "Light" : "Dark"}
              </button>
            </div>
            <Link to="/login" className="btn btn-outline" style={{ width: "100%", justifyContent: "center" }}>
              Sign In
            </Link>
            <Link to="/register" className="btn btn-primary" style={{ width: "100%", justifyContent: "center" }}>
              Get Started
            </Link>
          </div>
        )}
      </header>

      {/* Hero Section */}
      <section style={{
        padding: "80px 16px 64px",
        textAlign: "center",
        background: theme === "dark"
          ? "radial-gradient(circle at 50% 20%, #1a1a1a 0%, #0f0f0f 70%)"
          : "radial-gradient(circle at 50% 20%, #fafafa 0%, #ffffff 70%)"
      }}>
        <div style={{ maxWidth: "640px", margin: "0 auto" }}>
          <h1 style={{
            fontSize: "clamp(32px, 5vw, 48px)",
            fontWeight: "700",
            letterSpacing: "-0.5px",
            lineHeight: "1.15",
            marginBottom: "16px",
            color: "var(--text-primary)"
          }}>
            Your AI-Powered Desktop Assistant.
          </h1>
          <p style={{
            fontSize: "16px",
            color: "var(--text-secondary)",
            marginBottom: "32px",
            lineHeight: "1.5"
          }}>
            Voice commands, multilingual support, and local automation. Free and open.
          </p>
          <div style={{ display: "flex", gap: "12px", justifyContent: "center", flexWrap: "wrap" }}>
            <Link to="/register" className="btn btn-primary" style={{ padding: "10px 24px", fontSize: "15px" }}>
              Get Started
            </Link>
            <button onClick={scrollToFeatures} className="btn btn-outline" style={{ padding: "10px 24px", fontSize: "15px" }}>
              Learn More
            </button>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" style={{ padding: "64px 16px", borderTop: "1px solid var(--border)", backgroundColor: "var(--bg-secondary)" }}>
        <div className="container">
          <div style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
            gap: "24px"
          }}>
            {/* Card 1 */}
            <div className="card">
              <div style={{
                width: "40px",
                height: "40px",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                backgroundColor: "var(--bg-tertiary)",
                borderRadius: "var(--radius-card)",
                color: "var(--accent)",
                marginBottom: "16px"
              }}>
                <MicIcon size={20} />
              </div>
              <h3 style={{ fontSize: "16px", fontWeight: "600", marginBottom: "8px" }}>
                Voice in Your Language
              </h3>
              <p style={{ color: "var(--text-secondary)", fontSize: "13px", lineHeight: "1.5" }}>
                Speak naturally in Hindi, Kannada, or English with automatic script detection and natural voices.
              </p>
            </div>

            {/* Card 2 */}
            <div className="card">
              <div style={{
                width: "40px",
                height: "40px",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                backgroundColor: "var(--bg-tertiary)",
                borderRadius: "var(--radius-card)",
                color: "var(--accent)",
                marginBottom: "16px"
              }}>
                <TerminalIcon size={20} />
              </div>
              <h3 style={{ fontSize: "16px", fontWeight: "600", marginBottom: "8px" }}>
                Smart Local Commands
              </h3>
              <p style={{ color: "var(--text-secondary)", fontSize: "13px", lineHeight: "1.5" }}>
                Launch local applications, execute desktop macros, and control system tools with zero cloud latency.
              </p>
            </div>

            {/* Card 3 */}
            <div className="card">
              <div style={{
                width: "40px",
                height: "40px",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                backgroundColor: "var(--bg-tertiary)",
                borderRadius: "var(--radius-card)",
                color: "var(--accent)",
                marginBottom: "16px"
              }}>
                <ShieldIcon size={20} />
              </div>
              <h3 style={{ fontSize: "16px", fontWeight: "600", marginBottom: "8px" }}>
                Private and Free
              </h3>
              <p style={{ color: "var(--text-secondary)", fontSize: "13px", lineHeight: "1.5" }}>
                Runs entirely on your machine with local SQLite database storage and free API key tiers.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer style={{
        marginTop: "auto",
        borderTop: "1px solid var(--border)",
        padding: "24px 16px",
        backgroundColor: "var(--bg)"
      }}>
        <div className="container" style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexWrap: "wrap",
          gap: "12px"
        }}>
          <span style={{ fontSize: "13px", color: "var(--text-muted)" }}>
            KALKI Assistant. Built for everyone.
          </span>
          <button
            onClick={toggleTheme}
            className="btn btn-outline btn-sm"
            style={{ fontSize: "12px", padding: "4px 10px" }}
          >
            {theme === "dark" ? <SunIcon size={14} /> : <MoonIcon size={14} />}{" "}
            {theme === "dark" ? "Light Mode" : "Dark Mode"}
          </button>
        </div>
      </footer>

      {/* Responsive CSS */}
      <style>{`
        @media (min-width: 640px) {
          .desktop-nav { display: flex !important; }
          .mobile-menu-btn { display: none !important; }
        }
      `}</style>
    </div>
  );
};

export default LandingPage;
