import { useEffect, useState, useCallback } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import api from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { toast } from "sonner";
import { ArrowLeft, MapPinLine, ChatCircleText, CheckCircle, Star, PaperPlaneTilt, Warning } from "@phosphor-icons/react";

const STATUS_META = {
  proposed: { label: "Proposed", cls: "bg-secondary text-secondary-foreground" },
  accepted: { label: "Accepted", cls: "bg-accent text-accent-foreground" },
  meetup_planned: { label: "Meetup Planned", cls: "bg-primary text-primary-foreground" },
  completed: { label: "Completed", cls: "bg-primary text-primary-foreground" },
  declined: { label: "Declined", cls: "bg-muted text-muted-foreground" },
  cancelled: { label: "Cancelled", cls: "bg-muted text-muted-foreground" },
};

export function TradesList() {
  const [trades, setTrades] = useState([]);
  const load = useCallback(async () => {
    const r = await api.get("/trades");
    setTrades(r.data);
  }, []);
  useEffect(() => { load(); }, [load]);

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8 pb-24 md:pb-8" data-testid="trades-page">
      <p className="text-sm font-bold uppercase tracking-[0.2em] text-primary mb-1">Trades</p>
      <h1 className="font-heading text-3xl sm:text-4xl font-bold mb-8">All your active and completed exchanges.</h1>
      {trades.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-border p-16 text-center">
          <h3 className="font-heading font-semibold text-xl mb-2">No trades yet</h3>
          <p className="text-muted-foreground">Head to Matches to find a trade partner.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {trades.map((t) => (
            <Link key={t.trade_id} to={`/trades/${t.trade_id}`} className="block rounded-2xl bg-card border border-border p-5 card-hover" data-testid={`trade-${t.trade_id}`}>
              <div className="flex items-center justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-2">
                    <span className={`pill px-3 py-1 text-xs font-bold ${STATUS_META[t.status]?.cls || "bg-muted"}`}>{STATUS_META[t.status]?.label || t.status}</span>
                    <span className="text-xs text-muted-foreground">with {t.other_user?.display_name}</span>
                  </div>
                  <div className="font-heading font-semibold truncate">{t.my_listing.title} ↔ {t.their_listing.title}</div>
                </div>
                <ChatCircleText size={22} weight="duotone" className="text-muted-foreground shrink-0" />
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

const MEETUP_TYPES = [
  { v: "library", l: "Public Library" },
  { v: "community_center", l: "Community Center" },
  { v: "police_station", l: "Police Exchange Zone" },
  { v: "public", l: "Other Public Location" },
];

export function TradeDetail() {
  const { id } = useParams();
  const nav = useNavigate();
  const { user } = useAuth();
  const [trade, setTrade] = useState(null);
  const [messages, setMessages] = useState([]);
  const [text, setText] = useState("");
  const [showMeetup, setShowMeetup] = useState(false);
  const [showRate, setShowRate] = useState(false);
  const [meetupForm, setMeetupForm] = useState({ location_name: "", location_type: "library", date: "", time: "" });
  const [rating, setRating] = useState({ stars: 5, comment: "", tags: [] });

  const load = useCallback(async () => {
    const [t, m] = await Promise.all([api.get(`/trades/${id}`), api.get(`/trades/${id}/messages`)]);
    setTrade(t.data); setMessages(m.data);
  }, [id]);

  useEffect(() => { load(); const iv = setInterval(load, 5000); return () => clearInterval(iv); }, [load]);

  if (!trade) return <div className="p-8">Loading…</div>;

  const iAmProposer = trade.role === "proposer";
  const other = trade.other_user;
  const canAct = (a) => {
    if (a === "accept" || a === "decline") return !iAmProposer && trade.status === "proposed";
    if (a === "meetup") return ["accepted", "meetup_planned"].includes(trade.status);
    if (a === "complete") return ["accepted", "meetup_planned"].includes(trade.status) && !trade[`${trade.role}_completed`];
    if (a === "rate") return trade.status === "completed" && !trade[`${trade.role}_rated`];
    if (a === "cancel") return !["completed", "cancelled", "declined"].includes(trade.status);
    return false;
  };

  const doAction = async (action) => {
    try {
      const r = await api.post(`/trades/${id}/action?action=${action}`);
      setTrade(r.data);
      toast.success(`Trade ${action}ed`);
    } catch (e) { toast.error(e.response?.data?.detail || "Failed"); }
  };

  const sendMsg = async () => {
    if (!text.trim()) return;
    const t = text; setText("");
    await api.post(`/trades/${id}/messages`, { text: t });
    load();
  };

  const saveMeetup = async () => {
    if (!meetupForm.location_name || !meetupForm.date || !meetupForm.time) { toast.error("Fill all fields"); return; }
    const r = await api.post(`/trades/${id}/meetup`, meetupForm);
    setTrade(r.data); setShowMeetup(false); toast.success("Meetup planned");
  };

  const submitRating = async () => {
    await api.post(`/trades/${id}/rate`, rating);
    toast.success("Thanks for rating!");
    setShowRate(false); load();
  };

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 py-8 pb-24 md:pb-8" data-testid="trade-detail">
      <button onClick={() => nav(-1)} className="text-sm text-muted-foreground mb-4 flex items-center gap-1"><ArrowLeft size={16} /> Back to trades</button>

      {/* Header */}
      <div className="rounded-2xl bg-card border border-border p-6 mb-5">
        <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
          <span className={`pill px-3 py-1 text-xs font-bold ${STATUS_META[trade.status]?.cls}`}>{STATUS_META[trade.status]?.label || trade.status}</span>
          <div className="text-sm text-muted-foreground">with <span className="font-medium text-foreground">{other?.display_name}</span> · ⭐ {(other?.reputation_score || 0).toFixed(1)}</div>
        </div>
        <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-3">
          <div className="rounded-xl border border-border p-3 bg-background">
            <div className="text-xs text-muted-foreground uppercase tracking-widest">{iAmProposer ? "You offer" : "They offer"}</div>
            <div className="font-heading font-semibold mt-1">{trade.my_listing.title}</div>
          </div>
          <span className="text-2xl">↔</span>
          <div className="rounded-xl border border-border p-3 bg-background">
            <div className="text-xs text-muted-foreground uppercase tracking-widest">{iAmProposer ? "They offer" : "You offer"}</div>
            <div className="font-heading font-semibold mt-1">{trade.their_listing.title}</div>
          </div>
        </div>

        {/* Actions */}
        <div className="mt-5 flex flex-wrap gap-2">
          {canAct("accept") && <Button onClick={() => doAction("accept")} className="rounded-full" data-testid="accept-trade">Accept trade</Button>}
          {canAct("decline") && <Button variant="outline" onClick={() => doAction("decline")} className="rounded-full" data-testid="decline-trade">Decline</Button>}
          {canAct("meetup") && <Button onClick={() => setShowMeetup(true)} variant="outline" className="rounded-full" data-testid="plan-meetup"><MapPinLine size={18} className="mr-1" /> {trade.meetup ? "Update meetup" : "Plan meetup"}</Button>}
          {canAct("complete") && <Button onClick={() => doAction("complete")} className="rounded-full" data-testid="complete-trade"><CheckCircle size={18} className="mr-1" /> I completed this trade</Button>}
          {canAct("rate") && <Button onClick={() => setShowRate(true)} className="rounded-full" data-testid="rate-trade"><Star size={18} className="mr-1" /> Rate</Button>}
          {canAct("cancel") && <Button variant="ghost" onClick={() => doAction("cancel")} className="rounded-full text-muted-foreground" data-testid="cancel-trade">Cancel</Button>}
        </div>
      </div>

      {/* Meetup card */}
      {trade.meetup && (
        <div className="rounded-2xl border border-border bg-accent/40 p-5 mb-5">
          <div className="text-xs font-bold uppercase tracking-widest text-primary mb-2">Meetup</div>
          <div className="font-heading font-semibold text-lg flex items-center gap-2"><MapPinLine size={20} weight="duotone" /> {trade.meetup.location_name}</div>
          <div className="text-sm text-muted-foreground mt-1">{trade.meetup.date} at {trade.meetup.time}</div>
        </div>
      )}

      {/* Meetup planner */}
      {showMeetup && (
        <div className="rounded-2xl bg-card border border-border p-6 mb-5">
          <h3 className="font-heading font-semibold mb-3">Plan a safe meetup</h3>
          <p className="text-xs text-muted-foreground mb-4 flex items-start gap-1"><Warning size={14} className="mt-0.5 shrink-0" /> Meet in public. Never share your home address.</p>
          <div className="grid sm:grid-cols-2 gap-3">
            <select value={meetupForm.location_type} onChange={(e) => setMeetupForm({ ...meetupForm, location_type: e.target.value })} className="h-12 rounded-xl border border-border bg-background px-3" data-testid="meetup-type">
              {MEETUP_TYPES.map((t) => <option key={t.v} value={t.v}>{t.l}</option>)}
            </select>
            <Input placeholder="Location name (e.g. Main Library)" value={meetupForm.location_name} onChange={(e) => setMeetupForm({ ...meetupForm, location_name: e.target.value })} className="h-12 rounded-xl" data-testid="meetup-location" />
            <Input type="date" value={meetupForm.date} onChange={(e) => setMeetupForm({ ...meetupForm, date: e.target.value })} className="h-12 rounded-xl" data-testid="meetup-date" />
            <Input type="time" value={meetupForm.time} onChange={(e) => setMeetupForm({ ...meetupForm, time: e.target.value })} className="h-12 rounded-xl" data-testid="meetup-time" />
          </div>
          <div className="flex gap-2 mt-4">
            <Button onClick={saveMeetup} className="rounded-full" data-testid="save-meetup">Save meetup</Button>
            <Button variant="outline" onClick={() => setShowMeetup(false)} className="rounded-full">Cancel</Button>
          </div>
        </div>
      )}

      {/* Rating */}
      {showRate && (
        <div className="rounded-2xl bg-card border border-border p-6 mb-5">
          <h3 className="font-heading font-semibold mb-3">How did this trade go?</h3>
          <div className="flex gap-2 mb-4">
            {[1, 2, 3, 4, 5].map((n) => (
              <button key={n} onClick={() => setRating({ ...rating, stars: n })} data-testid={`star-${n}`}>
                <Star size={32} weight={n <= rating.stars ? "fill" : "regular"} className={n <= rating.stars ? "text-secondary" : "text-muted-foreground"} />
              </button>
            ))}
          </div>
          <textarea rows={3} value={rating.comment} onChange={(e) => setRating({ ...rating, comment: e.target.value })} placeholder="Optional feedback…" className="w-full rounded-xl border border-border bg-background p-3 mb-3" data-testid="rating-comment" />
          <Button onClick={submitRating} className="rounded-full" data-testid="submit-rating">Submit rating</Button>
        </div>
      )}

      {/* Chat */}
      <div className="rounded-2xl bg-card border border-border p-6" data-testid="chat-panel">
        <h3 className="font-heading font-semibold mb-4 flex items-center gap-2"><ChatCircleText size={20} weight="duotone" /> Trade chat</h3>
        <div className="space-y-3 max-h-96 overflow-y-auto mb-4">
          {messages.length === 0 && <p className="text-sm text-muted-foreground text-center py-6">No messages yet. Say hi!</p>}
          {messages.map((m) => {
            const mine = m.user_id === user.user_id;
            return (
              <div key={m.id} className={`flex ${mine ? "justify-end" : "justify-start"}`}>
                <div className={`max-w-[75%] rounded-2xl px-4 py-2 text-sm ${mine ? "bg-primary text-primary-foreground" : "bg-muted"}`}>
                  <div>{m.text}</div>
                  <div className={`text-[10px] mt-1 ${mine ? "text-primary-foreground/70" : "text-muted-foreground"}`}>{new Date(m.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</div>
                </div>
              </div>
            );
          })}
        </div>
        <div className="flex gap-2">
          <Input value={text} onChange={(e) => setText(e.target.value)} onKeyDown={(e) => e.key === "Enter" && sendMsg()} placeholder="Type a message…" className="h-12 rounded-full" data-testid="chat-input" />
          <Button onClick={sendMsg} className="rounded-full h-12 w-12 p-0" data-testid="send-msg"><PaperPlaneTilt size={18} weight="fill" /></Button>
        </div>
      </div>
    </div>
  );
}
