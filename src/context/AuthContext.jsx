import React, { createContext, useContext, useState, useEffect } from "react";
import { API_BASE_URL } from "../config";

const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(() => localStorage.getItem("kalki_token"));
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const verifySession = async () => {
      const savedToken = localStorage.getItem("kalki_token");
      if (!savedToken) {
        setLoading(false);
        return;
      }

      try {
        const response = await fetch(`${API_BASE_URL}/api/auth/me`, {
          headers: {
            "Authorization": `Bearer ${savedToken}`
          }
        });

        if (response.ok) {
          const data = await response.json();
          setUser(data.user || data);
          setToken(savedToken);
        } else {
          // Token expired or invalid
          localStorage.removeItem("kalki_token");
          setUser(null);
          setToken(null);
        }
      } catch (err) {
        console.error("Auth session verification failed:", err);
        // Retain local state or clear if unreachable
        localStorage.removeItem("kalki_token");
        setUser(null);
        setToken(null);
      } finally {
        setLoading(false);
      }
    };

    verifySession();
  }, []);

  const login = (newToken, userData) => {
    localStorage.setItem("kalki_token", newToken);
    setToken(newToken);
    setUser(userData);
  };

  const logout = () => {
    localStorage.removeItem("kalki_token");
    setToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, token, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
