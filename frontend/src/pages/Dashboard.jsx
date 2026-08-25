import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import api from "@/lib/api";
import { useAuth } from "@/lib/auth";
import ListingCard from "@/components/ListingCard";
import SmartSearch from "@/components/SmartSearch";
import { Button } from "@/components/ui/button";
import { Handshake, ListPlus, Sparkle, MapPinLine, Users, ArrowsClockwise, Package, ListChecks, Wrench } from "@phosphor-icons/react";

export default function Dashboard() {
  const { user } = useAuth();
  const nav = useNavigate();
  const [mine, setMine] = useState([]);
  const [matches, setMatches] = useState([]);
  const [trades, setTrades] = useState([]);
  const [stats, setStats] = useState(null);

  useEffect(() => {
    (async () => {
      try {
        const [ml, mm, mt, st] = await Promise.all([
          api.get("/listings?mine=true"),
          api.get("/matches"),
          api.get("/trades"),
          api.get("/dashboard/stats"),
        ]);
        setMine(ml.data);
        setMatches(mm.data);
        setTrades(mt.data);
        setStats(st.data);
      } catch { /* handled globally */ }
    })();
  }, []);

  const activeTrades = trades.filter((t) => !["completed", "cancelled", "declined"].includes(t.status));
  const meetups = trades.filter((t) => t.meetup && ["accepted", "meetup_planned"].includes(t.status));

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8 pb-24 md:pb-8" data-testid="dashboard-page">
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 mb-6">
        <div>
          <p className="text-sm font-bold uppercase tracking-[0.2em] text-primary mb-1">Your home base</p>
          <h1 className="font-heading text-3xl sm:text-4xl font-bold">Welcome back, {user?.first_name || user?.display_name?.split(" ")[0]}.</h1>
          <p className="text-muted-foreground mt-1 flex items-center gap-1.5 text-sm"><MapPinLine size={16} weight="duotone" /> {user?.city || "Add your location"} · {user?.search_radius_miles || 10} mi radius</p>
        </div>
        <Button onClick={() => nav("/new")} className="rounded-full h-12 px-6 shine" data-testid="dashboard-post-btn"><ListPlus size={20} weight="bold" className="mr-1" /> Post something</Button>
      </div>

      {/* Smart search */}
      <div className="mb-8">
        <SmartSearch />
      </div>

      {/* Personal Stats */}
      {stats && (
        <>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
            <StatCard n={stats.my_haves} label="Your Haves" icon={Package} />
            <StatCard n={stats.my_needs} label="Your Needs" icon={ListChecks} />
            <StatCard n={stats.my_services} label="Your Skills" icon={Wrench} />
            <StatCard n={stats.my_completed_trades} label="Trades completed" icon={ArrowsClockwise} />
          </div>
          {stats.has_location ? (
            <div className="grid grid-cols-3 gap-3 mb-10 text-sm">
              <NearbyStat n={stats.nearby_haves} label={`Haves within ${stats.radius_miles} mi`} />
              <NearbyStat n={stats.nearby_needs} label={`Needs within ${stats.radius_miles} mi`} />
              <NearbyStat n={stats.nearby_services} label={`Skills within ${stats.radius_miles} mi`} />
            </div>
          ) : (
            <div className="mb-10 rounded-2xl border border-dashed border-border p-5 flex items-center justify-between gap-3">
              <div className="text-sm">
                <p className="font-semibold">Set your location</p>
                <p className="text-muted-foreground">We'll show you what's happening within your radius.</p>
              </div>
              <Button onClick={() => nav("/onboarding")} className="rounded-full shrink-0">Set location</Button>
            </div>
          )}
        </>
      )}

      {/* Matches */}
      <Section title="Potential matches nearby" cta={matches.length > 0 && <Link to="/matches" className="text-sm text-primary font-medium">See all →</Link>}>
        {matches.length === 0 ? (
          <EmptyState title="No matches yet" desc="Post an item and add a need — we'll surface people whose trades line up with yours." action={<Button onClick={() => nav("/new")} className="rounded-full" data-testid="empty-post">Post something</Button>} />
        ) : (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {matches.slice(0, 3).map((m, i) => (
              <MatchTile key={i} m={m} />
            ))}
          </div>
        )}
      </Section>

      {/* Upcoming meetups */}
      {meetups.length > 0 && (
        <Section title="Upcoming meetups">
          <div className="grid sm:grid-cols-2 gap-4">
            {meetups.map((t) => (
              <Link key={t.trade_id} to={`/trades/${t.trade_id}`} className="rounded-2xl bg-card border border-border p-5 card-hover">
                <div className="text-xs font-bold uppercase tracking-widest text-primary mb-1">Meetup planned</div>
                <div className="font-heading font-semibold">{t.my_listing.title} ↔ {t.their_listing.title}</div>
                <div className="text-sm text-muted-foreground mt-2 flex items-center gap-2"><MapPinLine size={14} /> {t.meetup.location_name}</div>
                <div className="text-sm text-muted-foreground">{t.meetup.date} · {t.meetup.time}</div>
              </Link>
            ))}
          </div>
        </Section>
      )}

      {/* Active trades */}
      {activeTrades.length > 0 && (
        <Section title="Active trades" cta={<Link to="/trades" className="text-sm text-primary font-medium">See all →</Link>}>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {activeTrades.slice(0, 3).map((t) => (
              <Link key={t.trade_id} to={`/trades/${t.trade_id}`} className="rounded-2xl bg-card border border-border p-5 card-hover">
                <div className="text-xs font-bold uppercase tracking-widest text-secondary mb-1">{t.status.replace(/_/g, " ")}</div>
                <div className="font-heading font-semibold line-clamp-1">{t.my_listing.title} ↔ {t.their_listing.title}</div>
                <div className="text-sm text-muted-foreground mt-2">with {t.other_user?.display_name}</div>
              </Link>
            ))}
          </div>
        </Section>
      )}

      {/* My listings */}
      <Section title="What you have posted" cta={<Link to="/listings" className="text-sm text-primary font-medium">Manage →</Link>}>
        {mine.length === 0 ? (
          <EmptyState title="Nothing posted yet" desc="Have something sitting around that someone else could use?" action={<Button onClick={() => nav("/new")} className="rounded-full">Post something</Button>} />
        ) : (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {mine.slice(0, 3).map((l) => <ListingCard key={l.listing_id} listing={l} />)}
          </div>
        )}
      </Section>
    </div>
  );
}

function StatCard({ n, label, icon: Icon }) {
  return (
    <div className="rounded-2xl bg-card border border-border p-5">
      <Icon size={22} weight="duotone" className="text-primary mb-2" />
      <div className="font-heading text-2xl font-bold leading-none">{n}</div>
      <div className="text-xs text-muted-foreground mt-1">{label}</div>
    </div>
  );
}

function NearbyStat({ n, label }) {
  return (
    <div className="rounded-xl bg-muted/50 border border-border/60 px-4 py-3">
      <div className="font-heading text-lg font-bold text-primary">{n}</div>
      <div className="text-[11px] text-muted-foreground">{label}</div>
    </div>
  );
}

function Section({ title, cta, children }) {
  return (
    <section className="mb-12">
      <div className="flex items-center justify-between mb-5">
        <h2 className="font-heading text-xl sm:text-2xl font-semibold">{title}</h2>
        {cta}
      </div>
      {children}
    </section>
  );
}

function EmptyState({ title, desc, action }) {
  return (
    <div className="rounded-2xl border border-dashed border-border p-10 text-center bg-card/50">
      <h3 className="font-heading font-semibold text-lg mb-2">{title}</h3>
      <p className="text-sm text-muted-foreground mb-5">{desc}</p>
      {action}
    </div>
  );
}

function MatchTile({ m }) {
  return (
    <div className="rounded-2xl bg-card border border-border p-5 card-hover" data-testid="match-tile">
      <div className="flex items-center justify-between mb-3">
        <span className="pill px-3 py-1 text-xs font-bold bg-accent text-accent-foreground">{m.label}</span>
        {m.their_listing.distance_miles != null && <span className="text-xs text-muted-foreground">{m.their_listing.distance_miles} mi</span>}
      </div>
      <div className="space-y-2 text-sm">
        <div><span className="text-muted-foreground">You offer:</span> <span className="font-semibold">{m.my_listing.title}</span></div>
        <div><span className="text-muted-foreground">They offer:</span> <span className="font-semibold">{m.their_listing.title}</span></div>
      </div>
      <div className="mt-4 pt-3 border-t border-border text-xs text-muted-foreground">
        {m.their_listing.user_display_name} · ⭐ {(m.their_listing.user_reputation || 0).toFixed(1)}
      </div>
      <Link to="/matches" className="mt-3 inline-block text-sm font-medium text-primary">Review →</Link>
    </div>
  );
}
