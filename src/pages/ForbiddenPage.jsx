import React from "react";
import { Link } from "react-router-dom";
import { ShieldIcon, ArrowLeftIcon } from "../components/common/Icons";

export const ForbiddenPage = () => {
  return (
    <div style={{
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      minHeight: "100vh",
      padding: "24px",
      backgroundColor: "var(--bg-secondary)"
    }}>
      <div className="card" style={{ maxWidth: "420px", width: "100%", textAlign: "center" }}>
        <div style={{
          width: "48px",
          height: "48px",
          margin: "0 auto 16px",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          backgroundColor: "rgba(231, 76, 60, 0.15)",
          color: "var(--danger)",
          borderRadius: "50%"
        }}>
          <ShieldIcon size={24} />
        </div>
        <h2 style={{ fontSize: "20px", fontWeight: "600", marginBottom: "8px" }}>
          403 — Access Denied
        </h2>
        <p style={{ color: "var(--text-secondary)", marginBottom: "24px", fontSize: "14px" }}>
          Administrator privileges are required to view this panel. If you believe this is an error, contact your system administrator.
        </p>
        <Link to="/dashboard" className="btn btn-primary" style={{ width: "100%" }}>
          <ArrowLeftIcon size={16} /> Return to Dashboard
        </Link>
      </div>
    </div>
  );
};

export default ForbiddenPage;
