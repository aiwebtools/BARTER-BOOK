import { useEffect, useRef } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import api from "@/lib/api";

export default function AuthCallback() {
  const nav = useNavigate();
  const location = useLocation();
  const { setUserDirect } = useAuth();
  const processed = useRef(false);

  useEffect(() => {
    if (processed.current) return;
    processed.current = true;
    const hash = location.hash || window.location.hash;
    const m = hash.match(/session_id=([^&]+)/);
    if (!m) { nav("/login"); return; }
    const sessionId = m[1];
    (async () => {
      try {
        const r = await api.post("/auth/google/session", null, { headers: { "X-Session-ID": sessionId } });
        localStorage.setItem("bg_token", r.data.token);
        setUserDirect(r.data.user);
        window.history.replaceState(null, "", "/dashboard");
        nav("/dashboard", { replace: true, state: { user: r.data.user } });
      } catch {
        nav("/login", { replace: true });
      }
    })();
  }, [location, nav, setUserDirect]);

  return (
    <div className="min-h-screen grid place-items-center" data-testid="auth-callback">
      <div className="text-center">
        <div className="w-12 h-12 rounded-full border-4 border-primary/30 border-t-primary animate-spin mx-auto mb-4" />
        <p className="text-muted-foreground">Signing you in…</p>
      </div>
    </div>
  );
}
