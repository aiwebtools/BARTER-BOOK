import { createContext, useContext, useEffect, useState, useCallback } from "react";
import api from "@/lib/api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const checkAuth = useCallback(async () => {
    try {
      const r = await api.get("/auth/me");
      setUser(r.data);
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // CRITICAL: If returning from OAuth callback, skip /me check. AuthCallback handles it.
    if (window.location.hash?.includes("session_id=")) {
      setLoading(false);
      return;
    }
    checkAuth();
  }, [checkAuth]);

  const login = async (email, password) => {
    const r = await api.post("/auth/login", { email, password });
    localStorage.setItem("bg_token", r.data.token);
    setUser(r.data.user);
    return r.data.user;
  };

  const signup = async (email, password, display_name) => {
    const referral_code = localStorage.getItem("bg_referral_code") || undefined;
    const r = await api.post("/auth/signup", { email, password, display_name, referral_code });
    localStorage.setItem("bg_token", r.data.token);
    localStorage.removeItem("bg_referral_code");
    setUser(r.data.user);
    return r.data.user;
  };

  const logout = async () => {
    try { await api.post("/auth/logout"); } catch { /* ignore */ }
    localStorage.removeItem("bg_token");
    setUser(null);
  };

  const refresh = checkAuth;
  const setUserDirect = (u) => setUser(u);

  return (
    <AuthContext.Provider value={{ user, loading, login, signup, logout, refresh, setUserDirect }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
