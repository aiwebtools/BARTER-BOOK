import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "@/lib/api";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { ArrowsClockwise, MapPin, Star, GitBranch } from "@phosphor-icons/react";

export default function Matches() {
  const nav = useNavigate();
  const [matches, setMatches] = useState([]);
  const [chains, setChains] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      api.get("/matches").then((r) => setMatches(r.data)).catch((e) => console.warn("[matches] load failed", e?.response?.status)),
      api.get("/matches/chains").then((r) => setChains(r.data)).catch((e) => console.warn("[chains] load failed", e?.response?.status)),
    ]).finally(() => setLoading(false));
  }, []);

  const propose = async (m) => {
    try {
      const r = await api.post("/trades", {
        to_user_id: m.their_listing.user_id,
        my_listing_id: m.my_listing.listing_id,
        their_listing_id: m.their_listing.listing_id,
        message: `I noticed we might have a match — interested in trading?`,
      });
      nav(`/trades/${r.data.trade_id}`);
    } catch (e) {
      const msg = e?.response?.data?.detail || "Couldn't propose that trade";
      toast.error(msg);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8 pb-24 md:pb-8" data-testid="matches-page">
      <p className="text-sm font-bold uppercase tracking-[0.2em] text-primary mb-1">Matches</p>
      <h1 className="font-heading text-3xl sm:text-4xl font-bold mb-2">Potential trades near you.</h1>
      <p className="text-muted-foreground mb-8">These are people whose have/need pairs line up with yours.</p>

      {loading ? <div className="text-center py-12 text-muted-foreground">Finding matches…</div> :
        <>
          {chains.length > 0 && (
            <section className="mb-10" data-testid="chains-section">
              <div className="flex items-center gap-2 mb-4">
                <GitBranch size={22} weight="duotone" className="text-secondary" />
                <h2 className="font-heading text-xl sm:text-2xl font-semibold">Three-person trade chains</h2>
                <span className="pill px-2 py-0.5 text-[10px] font-bold bg-secondary/20 text-secondary">EXPERIMENTAL</span>
              </div>
              <p className="text-sm text-muted-foreground mb-4">You don't need a direct match — a neighbor of a neighbor closes the loop.</p>
              <div className="grid md:grid-cols-2 gap-4">
                {chains.map((c, i) => (
                  <div key={`${c.you.listing.listing_id}::${c.b.listing.listing_id}::${c.c.listing.listing_id}`} className="rounded-2xl bg-card border border-border p-5 card-hover" data-testid={`chain-${i}`}>
                    <div className="text-xs font-bold uppercase tracking-widest text-secondary mb-3">Chain of 3</div>
                    <div className="space-y-2 text-sm">
                      <ChainRow label="You give" title={c.you.listing.title} who="→" />
                      <ChainRow label={c.b.user.display_name + " gives"} title={c.b.listing.title} who="→" city={c.b.user.city} />
                      <ChainRow label={c.c.user.display_name + " gives"} title={c.c.listing.title} who="↩ back to you" city={c.c.user.city} />
                    </div>
                    <p className="text-xs text-muted-foreground mt-4 pt-3 border-t border-border">Coordinate with both neighbors — chat with each to plan a swap.</p>
                    <div className="mt-3 flex gap-2">
                      <Button size="sm" variant="outline" className="rounded-full" onClick={() => nav(`/messages/${c.b.user.user_id}`)} data-testid={`chain-${i}-msg-b`}>Message {c.b.user.display_name}</Button>
                      <Button size="sm" variant="outline" className="rounded-full" onClick={() => nav(`/messages/${c.c.user.user_id}`)} data-testid={`chain-${i}-msg-c`}>Message {c.c.user.display_name}</Button>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          )}

          {matches.length === 0 && chains.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-border p-16 text-center">
              <h3 className="font-heading font-semibold text-xl mb-2">No matches yet</h3>
              <p className="text-muted-foreground mb-6">Post more items and needs, or expand your search radius.</p>
              <Button onClick={() => nav("/new")} className="rounded-full">Post something</Button>
            </div>
          ) : matches.length === 0 ? null : (
          <div className="grid md:grid-cols-2 gap-5">
            {matches.map((m) => (
              <div key={`${m.my_listing.listing_id}::${m.their_listing.listing_id}`} className="rounded-2xl bg-card border border-border p-6 card-hover" data-testid={`match-${m.my_listing.listing_id}-${m.their_listing.listing_id}`}>
                <div className="flex items-center justify-between mb-4">
                  <span className="pill px-3 py-1 text-xs font-bold bg-accent text-accent-foreground">{m.label}</span>
                  {m.their_listing.distance_miles != null && <span className="text-xs text-muted-foreground flex items-center gap-1"><MapPin size={14} /> {m.their_listing.distance_miles} mi</span>}
                </div>
                <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-3 mb-5">
                  <div className="rounded-xl border border-border p-3 bg-background">
                    <div className="text-xs text-muted-foreground uppercase tracking-widest">You offer</div>
                    <div className="font-heading font-semibold mt-1 line-clamp-2">{m.my_listing.title}</div>
                  </div>
                  <ArrowsClockwise size={28} weight="duotone" className="text-primary" />
                  <div className="rounded-xl border border-border p-3 bg-background">
                    <div className="text-xs text-muted-foreground uppercase tracking-widest">They offer</div>
                    <div className="font-heading font-semibold mt-1 line-clamp-2">{m.their_listing.title}</div>
                  </div>
                </div>
                <div className="flex items-center justify-between pt-4 border-t border-border">
                  <div className="text-sm">
                    <div className="font-medium">{m.their_listing.user_display_name}</div>
                    <div className="text-xs text-muted-foreground flex items-center gap-1"><Star size={12} weight="fill" className="text-secondary" /> {(m.their_listing.user_reputation || 0).toFixed(1)} · {m.their_listing.user_trades || 0} trades</div>
                  </div>
                  <Button onClick={() => propose(m)} className="rounded-full" data-testid="propose-match">Propose trade</Button>
                </div>
              </div>
            ))}
          </div>
        )}
        </>
      }
    </div>
  );
}

function ChainRow({ label, title, who, city }) {
  return (
    <div className="flex items-center gap-2 rounded-xl border border-border bg-background px-3 py-2">
      <div className="flex-1 min-w-0">
        <div className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground">{label}{city ? ` · ${city}` : ""}</div>
        <div className="font-heading font-semibold truncate">{title}</div>
      </div>
      <span className="text-xs text-muted-foreground shrink-0">{who}</span>
    </div>
  );
}
