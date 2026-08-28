import { useEffect, useState } from "react";
import { Link, useParams, useNavigate } from "react-router-dom";
import api from "@/lib/api";
import { useAuth } from "@/lib/auth";
import ListingCard from "@/components/ListingCard";
import ShareButtons from "@/components/ShareButtons";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { MapPinLine, Star, ShieldCheck, CheckCircle, Storefront, ChatCircleText, CurrencyDollar, Copy, CurrencyBtc, Wallet, Prohibit, Flag } from "@phosphor-icons/react";

const PAY_META = {
  cashapp_tag: { label: "CashApp", url: (v) => `https://cash.app/$${v.replace(/^\$/, "")}`, display: (v) => `$${v.replace(/^\$/, "")}`, icon: CurrencyDollar },
  venmo_tag: { label: "Venmo", url: (v) => `https://venmo.com/${v.replace(/^@/, "")}`, display: (v) => `@${v.replace(/^@/, "")}`, icon: CurrencyDollar },
  paypal_link: { label: "PayPal", url: (v) => v.startsWith("http") ? v : `https://${v}`, display: (v) => v, icon: CurrencyDollar },
  bitcoin_address: { label: "Bitcoin", display: (v) => v, icon: CurrencyBtc, mono: true },
  solana_address: { label: "Solana", display: (v) => v, icon: Wallet, mono: true },
  ethereum_address: { label: "Ethereum / EVM", display: (v) => v, icon: Wallet, mono: true },
};

export default function PublicProfile() {
  const { id } = useParams();
  const { user: me } = useAuth();
  const nav = useNavigate();
  const [u, setU] = useState(null);
  const [notFound, setNotFound] = useState(false);
  const [reporting, setReporting] = useState(false);

  useEffect(() => {
    api.get(`/users/${id}`)
      .then((r) => setU(r.data))
      .catch(() => setNotFound(true));
  }, [id]);

  const copyValue = async (v) => {
    try { await navigator.clipboard.writeText(v); toast.success("Copied"); }
    catch { toast.error("Couldn't copy"); }
  };

  const messageUser = async () => {
    if (!me) { nav("/login"); return; }
    nav(`/messages/${u.user_id}`);
  };

  const block = async () => {
    if (!window.confirm("Block this user? They won't see your listings and can't message you.")) return;
    try { await api.post(`/blocks/${u.user_id}`); toast.success("User blocked"); nav("/discover"); }
    catch { toast.error("Failed"); }
  };

  const report = async () => {
    const reason = window.prompt("Report reason (spam, scam, harassment, prohibited item, other):");
    if (!reason) return;
    try {
      await api.post("/reports", { target_type: "user", target_id: u.user_id, reason, description: "" });
      toast.success("Reported. Our team will review.");
    } catch { toast.error("Failed"); }
  };

  if (notFound) return (
    <div className="min-h-screen grid place-items-center p-6" data-testid="profile-not-found">
      <div className="text-center max-w-md">
        <h1 className="font-heading text-2xl font-bold mb-2">Storefront not found</h1>
        <Link to="/discover"><Button className="rounded-full mt-4">Browse listings</Button></Link>
      </div>
    </div>
  );
  if (!u) return <div className="min-h-screen grid place-items-center"><div className="w-10 h-10 border-4 border-primary/30 border-t-primary rounded-full animate-spin" /></div>;

  const accent = u.accent_color || undefined;
  const paymentEntries = Object.entries(PAY_META).filter(([k]) => u[k]);
  const isMe = me?.user_id === u.user_id;

  return (
    <div className="min-h-screen" data-testid="public-profile">
      {/* Banner */}
      <div className="relative h-56 sm:h-72 bg-accent" style={u.banner_photo ? { backgroundImage: `url(${u.banner_photo})`, backgroundSize: "cover", backgroundPosition: "center" } : accent ? { background: accent } : {}}>
        <Link to="/discover" className="absolute top-4 left-4 pill px-4 py-2 text-sm bg-background/90 backdrop-blur border border-border font-medium">← Discover</Link>
      </div>

      <div className="max-w-5xl mx-auto px-4 sm:px-6 -mt-16 pb-24 md:pb-16">
        {/* Header card */}
        <div className="rounded-2xl bg-card border border-border p-6 sm:p-8">
          <div className="flex flex-col sm:flex-row gap-6 items-start">
            <div className="w-28 h-28 rounded-full bg-muted border-4 border-card grid place-items-center overflow-hidden shrink-0">
              {u.picture ? <img src={u.picture} alt="" className="w-full h-full object-cover" /> : <span className="font-heading text-4xl font-bold">{u.display_name?.[0]}</span>}
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <Storefront size={20} weight="duotone" className="text-primary" />
                <span className="text-xs font-bold uppercase tracking-[0.2em] text-muted-foreground">Storefront</span>
              </div>
              <h1 className="font-heading text-3xl sm:text-4xl font-bold" data-testid="store-name-heading">{u.store_name || u.display_name}</h1>
              {u.store_tagline && <p className="text-muted-foreground mt-1">{u.store_tagline}</p>}
              {!u.store_tagline && u.bio && <p className="text-muted-foreground mt-1">{u.bio}</p>}
              <div className="flex flex-wrap gap-2 mt-3">
                {u.email_verified && <span className="pill px-2.5 py-0.5 text-xs bg-accent text-accent-foreground flex items-center gap-1"><ShieldCheck size={12} weight="fill" /> Email verified</span>}
                {u.verified_referral && <span className="pill px-2.5 py-0.5 text-xs bg-primary text-primary-foreground flex items-center gap-1"><CheckCircle size={12} weight="fill" /> Trusted</span>}
                <span className="pill px-2.5 py-0.5 text-xs bg-muted flex items-center gap-1"><Star size={12} weight="fill" className="text-secondary" /> {(u.reputation_score || 0).toFixed(1)} · {u.ratings_count || 0} reviews</span>
                <span className="pill px-2.5 py-0.5 text-xs bg-muted">{u.successful_trades || 0} trades</span>
                <span className="pill px-2.5 py-0.5 text-xs bg-muted flex items-center gap-1"><MapPinLine size={12} weight="fill" /> {[u.city, u.state].filter(Boolean).join(", ") || "—"}</span>
              </div>
            </div>
            {!isMe && me && (
              <div className="flex gap-2 shrink-0">
                <Button onClick={messageUser} className="rounded-full" data-testid="dm-user"><ChatCircleText size={18} weight="bold" className="mr-1" /> Message</Button>
                <div className="relative">
                  <Button variant="outline" onClick={() => setReporting(!reporting)} className="rounded-full h-11 w-11 p-0" aria-label="More" data-testid="profile-more">⋯</Button>
                  {reporting && (
                    <div className="absolute right-0 mt-2 w-48 rounded-xl bg-card border border-border shadow-lg py-1 z-20">
                      <button onClick={() => { setReporting(false); report(); }} className="w-full text-left px-4 py-2 text-sm hover:bg-muted flex items-center gap-2" data-testid="report-user"><Flag size={14} /> Report user</button>
                      <button onClick={() => { setReporting(false); block(); }} className="w-full text-left px-4 py-2 text-sm hover:bg-muted flex items-center gap-2 text-destructive" data-testid="block-user"><Prohibit size={14} /> Block user</button>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Share this storefront */}
          <div className="mt-6 pt-6 border-t border-border">
            <ShareButtons
              url={typeof window !== "undefined" ? window.location.href : ""}
              title={`${u.store_name || u.display_name}'s BarterGrid storefront`}
              text={`Check out ${u.store_name || u.display_name} on BarterGrid — free local barter network.`}
              testid="storefront-share"
            />
          </div>
        </div>

        {/* Payment handles */}
        {u.accepts_donations && paymentEntries.length > 0 && (
          <div className="mt-6 rounded-2xl bg-card border border-border p-6 sm:p-8" data-testid="payment-handles">
            <div className="flex items-center gap-2 mb-4">
              <CurrencyDollar size={22} weight="duotone" className="text-secondary" />
              <h2 className="font-heading font-semibold text-xl">Tip / Send</h2>
            </div>
            <p className="text-sm text-muted-foreground mb-4">{u.display_name} can also receive money electronically. BarterGrid doesn't process these — you're sending directly.</p>
            <div className="grid sm:grid-cols-2 gap-3">
              {paymentEntries.map(([key, meta]) => {
                const val = u[key];
                const disp = meta.display(val);
                const Icon = meta.icon;
                const hasUrl = !!meta.url;
                return (
                  <div key={key} className="rounded-xl border border-border p-4 flex items-center gap-3 bg-background" data-testid={`pay-${key}`}>
                    <Icon size={22} weight="duotone" className="text-primary shrink-0" />
                    <div className="flex-1 min-w-0">
                      <div className="text-xs font-bold uppercase tracking-widest text-muted-foreground">{meta.label}</div>
                      <div className={`text-sm truncate ${meta.mono ? "font-mono" : "font-medium"}`}>{disp}</div>
                    </div>
                    <button onClick={() => copyValue(val)} className="p-2 rounded-full hover:bg-muted transition-colors" aria-label="Copy" data-testid={`copy-${key}`}><Copy size={16} /></button>
                    {hasUrl && <a href={meta.url(val)} target="_blank" rel="noreferrer" className="pill px-3 py-1 text-xs bg-primary text-primary-foreground font-medium">Open</a>}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Listings storefront */}
        <div className="mt-6">
          <h2 className="font-heading font-semibold text-xl mb-4">{u.display_name?.split(" ")[0]}'s listings</h2>
          {(u.listings || []).length === 0 ? (
            <div className="rounded-2xl border border-dashed border-border p-12 text-center text-muted-foreground">Nothing posted yet.</div>
          ) : (
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
              {u.listings.map((l) => <ListingCard key={l.listing_id} listing={{ ...l, user_display_name: u.display_name, user_city: u.city, user_reputation: u.reputation_score, user_trades: u.successful_trades }} />)}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
