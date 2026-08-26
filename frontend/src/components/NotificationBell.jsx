import { useEffect, useState, useCallback } from "react";
import { Link } from "react-router-dom";
import api from "@/lib/api";
import { Bell, Handshake, ChatCircleText, Sparkle, MapPinLine, Star } from "@phosphor-icons/react";

const TYPE_META = {
  trade_proposal: { icon: Handshake, cls: "bg-accent text-accent-foreground" },
  message: { icon: ChatCircleText, cls: "bg-primary/10 text-primary" },
  referral_verified: { icon: Star, cls: "bg-secondary text-secondary-foreground" },
  meetup: { icon: MapPinLine, cls: "bg-accent text-accent-foreground" },
  match: { icon: Sparkle, cls: "bg-primary text-primary-foreground" },
};

export default function NotificationBell() {
  const [items, setItems] = useState([]);
  const [open, setOpen] = useState(false);

  const load = useCallback(async () => {
    try {
      const r = await api.get("/notifications");
      setItems(r.data);
    } catch (e) {
      console.warn("[notif] load failed", e?.response?.status || e?.message);
    }
  }, []);

  useEffect(() => {
    load();
    const iv = setInterval(load, 20000);
    return () => clearInterval(iv);
  }, [load]);

  const unread = items.filter((n) => !n.read).length;

  const openPanel = async () => {
    setOpen((o) => !o);
    if (!open && unread > 0) {
      try {
        await api.post("/notifications/read");
        setItems((it) => it.map((n) => ({ ...n, read: true })));
      } catch (e) {
        console.warn("[notif] mark-read failed", e?.response?.status || e?.message);
      }
    }
  };

  return (
    <div className="relative">
      <button
        onClick={openPanel}
        aria-label="Notifications"
        data-testid="notif-bell"
        className="relative w-10 h-10 rounded-full hover:bg-muted transition-colors grid place-items-center"
      >
        <Bell size={22} weight="duotone" />
        {unread > 0 && (
          <span className="absolute top-1 right-1 min-w-[18px] h-[18px] px-1 rounded-full bg-secondary text-secondary-foreground text-[10px] font-bold grid place-items-center" data-testid="notif-badge">
            {unread > 9 ? "9+" : unread}
          </span>
        )}
      </button>
      {open && (
        <>
          <div className="fixed inset-0 z-30" onClick={() => setOpen(false)} />
          <div className="absolute right-0 mt-2 w-[92vw] max-w-sm rounded-2xl bg-card border border-border shadow-xl z-40 overflow-hidden" data-testid="notif-panel">
            <div className="px-5 py-4 border-b border-border flex items-center justify-between">
              <div className="font-heading font-semibold">Notifications</div>
              {items.length > 0 && (
                <button
                  onClick={async () => {
                    if (!window.confirm("Clear all notifications?")) return;
                    try { await api.delete("/notifications"); setItems([]); }
                    catch (e) { console.warn("[notif] clear-all failed", e?.response?.status || e?.message); }
                  }}
                  className="text-xs text-muted-foreground hover:text-destructive transition-colors"
                  data-testid="notif-clear-all"
                >Clear all</button>
              )}
            </div>
            <div className="max-h-[420px] overflow-y-auto">
              {items.length === 0 ? (
                <div className="p-8 text-center text-sm text-muted-foreground">No notifications yet.</div>
              ) : (
                items.map((n) => {
                  const t = TYPE_META[n.type] || { icon: Bell, cls: "bg-muted text-foreground" };
                  const Icon = t.icon;
                  const to = n.conversation_with ? `/messages/${n.conversation_with}` : n.trade_id ? `/trades/${n.trade_id}` : "/matches";
                  return (
                    <Link key={n.id} to={to} onClick={() => setOpen(false)} className="flex items-start gap-3 px-5 py-3 hover:bg-muted/60 transition-colors border-b border-border last:border-0" data-testid={`notif-item-${n.id}`}>
                      <span className={`w-9 h-9 rounded-full grid place-items-center shrink-0 ${t.cls}`}>
                        <Icon size={18} weight="duotone" />
                      </span>
                      <div className="flex-1 min-w-0">
                        <div className="text-sm leading-snug">{n.text}</div>
                        <div className="text-xs text-muted-foreground mt-1">{new Date(n.created_at).toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}</div>
                      </div>
                    </Link>
                  );
                })
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
