import { useEffect, useState, useCallback, useRef } from "react";
import { Link, useParams, useNavigate } from "react-router-dom";
import api from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ArrowLeft, PaperPlaneTilt, ChatCircleText, User as UserIcon } from "@phosphor-icons/react";

export function MessagesList() {
  const [convs, setConvs] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try { const r = await api.get("/conversations"); setConvs(r.data); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); const iv = setInterval(load, 15000); return () => clearInterval(iv); }, [load]);

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 py-8 pb-24 md:pb-8" data-testid="messages-page">
      <p className="text-sm font-bold uppercase tracking-[0.2em] text-primary mb-1">Messages</p>
      <h1 className="font-heading text-3xl sm:text-4xl font-bold mb-8">Direct conversations.</h1>

      {loading ? <div className="text-center py-12 text-muted-foreground">Loading…</div> :
        convs.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-border p-12 text-center">
            <ChatCircleText size={40} weight="duotone" className="text-primary mx-auto mb-3" />
            <h3 className="font-heading font-semibold text-lg mb-2">No conversations yet</h3>
            <p className="text-muted-foreground text-sm">Message a neighbor from any listing or profile to start chatting.</p>
          </div>
        ) : (
          <div className="rounded-2xl bg-card border border-border overflow-hidden">
            {convs.map((c) => (
              <Link key={c.conversation_id} to={`/messages/${c.other_user?.user_id}`} className="flex items-center gap-4 px-5 py-4 hover:bg-muted/50 transition-colors border-b border-border last:border-0" data-testid={`conv-${c.conversation_id}`}>
                <div className="w-12 h-12 rounded-full bg-muted grid place-items-center overflow-hidden shrink-0">
                  {c.other_user?.picture ? <img src={c.other_user.picture} alt="" className="w-full h-full object-cover" /> : <UserIcon size={20} weight="duotone" />}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-heading font-semibold truncate">{c.other_user?.display_name || "User"}</span>
                    <span className="text-xs text-muted-foreground shrink-0">{new Date(c.last_message_at).toLocaleDateString([], { month: "short", day: "numeric" })}</span>
                  </div>
                  <div className="text-sm text-muted-foreground truncate">{c.last_message || "New conversation"}</div>
                </div>
                {c.unread > 0 && <span className="pill px-2 py-0.5 text-[10px] font-bold bg-secondary text-secondary-foreground" data-testid={`unread-${c.conversation_id}`}>{c.unread}</span>}
              </Link>
            ))}
          </div>
        )}
    </div>
  );
}

export function MessageThread() {
  const { userId } = useParams();
  const nav = useNavigate();
  const { user: me } = useAuth();
  const [data, setData] = useState(null);
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const scrollRef = useRef(null);

  const load = useCallback(async () => {
    try {
      const r = await api.get(`/conversations/${userId}`);
      setData(r.data);
    } catch (e) {
      if (e.response?.status === 404 || e.response?.status === 403) nav("/messages");
    }
  }, [userId, nav]);

  useEffect(() => { load(); const iv = setInterval(load, 4000); return () => clearInterval(iv); }, [load]);
  useEffect(() => { scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight }); }, [data]);

  const send = async () => {
    if (!text.trim() || sending) return;
    setSending(true);
    const body = text;
    setText("");
    try {
      await api.post(`/conversations/${userId}/messages`, { to_user_id: userId, text: body });
      load();
    } finally { setSending(false); }
  };

  if (!data) return <div className="min-h-screen grid place-items-center"><div className="w-10 h-10 border-4 border-primary/30 border-t-primary rounded-full animate-spin" /></div>;

  const other = data.other_user;

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 py-4 pb-24 md:pb-8 min-h-[calc(100vh-4rem)] flex flex-col" data-testid="message-thread">
      <div className="flex items-center gap-3 py-3 border-b border-border sticky top-16 bg-background/95 backdrop-blur z-10">
        <button onClick={() => nav("/messages")} className="p-2 rounded-full hover:bg-muted transition-colors" data-testid="msg-back"><ArrowLeft size={20} /></button>
        <Link to={`/u/${other?.user_id}`} className="flex items-center gap-3 flex-1 min-w-0">
          <div className="w-10 h-10 rounded-full bg-muted grid place-items-center overflow-hidden">
            {other?.picture ? <img src={other.picture} alt="" className="w-full h-full object-cover" /> : <UserIcon size={20} weight="duotone" />}
          </div>
          <div className="min-w-0">
            <div className="font-heading font-semibold truncate">{other?.display_name}</div>
            <div className="text-xs text-muted-foreground truncate">{other?.city || "—"} · ⭐ {(other?.reputation_score || 0).toFixed(1)}</div>
          </div>
        </Link>
      </div>

      <div ref={scrollRef} className="flex-1 overflow-y-auto py-4 space-y-2">
        {data.messages.length === 0 && <p className="text-center text-sm text-muted-foreground py-8">Say hi to start the conversation!</p>}
        {data.messages.map((m) => {
          const mine = m.user_id === me?.user_id;
          return (
            <div key={m.id} className={`flex ${mine ? "justify-end" : "justify-start"}`}>
              <div className={`max-w-[75%] rounded-2xl px-4 py-2 text-sm ${mine ? "bg-primary text-primary-foreground rounded-br-md" : "bg-muted rounded-bl-md"}`} data-testid={`dm-${m.id}`}>
                <div className="whitespace-pre-wrap break-words">{m.text}</div>
                <div className={`text-[10px] mt-1 ${mine ? "text-primary-foreground/70" : "text-muted-foreground"}`}>{new Date(m.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</div>
              </div>
            </div>
          );
        })}
      </div>

      <div className="sticky bottom-0 bg-background pt-3 pb-3 flex gap-2">
        <Input value={text} onChange={(e) => setText(e.target.value)} onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && (e.preventDefault(), send())} placeholder="Type a message…" className="h-12 rounded-full" data-testid="dm-input" />
        <Button onClick={send} disabled={sending || !text.trim()} className="rounded-full h-12 w-12 p-0" data-testid="dm-send"><PaperPlaneTilt size={18} weight="fill" /></Button>
      </div>
    </div>
  );
}
