import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "@/lib/api";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { ArrowsClockwise, MapPin, Star } from "@phosphor-icons/react";

export default function Matches() {
  const nav = useNavigate();
  const [matches, setMatches] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get("/matches").then((r) => setMatches(r.data)).finally(() => setLoading(false));
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
        matches.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-border p-16 text-center">
            <h3 className="font-heading font-semibold text-xl mb-2">No matches yet</h3>
            <p className="text-muted-foreground mb-6">Post more items and needs, or expand your search radius.</p>
            <Button onClick={() => nav("/new")} className="rounded-full">Post something</Button>
          </div>
        ) : (
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
    </div>
  );
}
