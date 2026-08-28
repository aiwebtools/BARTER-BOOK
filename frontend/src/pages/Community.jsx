import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "@/lib/api";
import ListingCard from "@/components/ListingCard";
import { Users, Package, Handshake, Wrench, TrendUp, Warning } from "@phosphor-icons/react";

export default function Community() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = () => {
    setLoading(true);
    setError(null);
    api.get("/community/dashboard")
      .then((r) => setData(r.data))
      .catch((e) => {
        console.warn("[community] load failed", e?.response?.status || e?.message);
        setError(e?.response?.data?.detail || "Couldn't load the community view. Please try again.");
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  if (loading) return <div className="min-h-[50vh] grid place-items-center text-muted-foreground" data-testid="community-loading">Loading community map…</div>;
  if (error) return (
    <div className="min-h-[50vh] grid place-items-center px-6" data-testid="community-error">
      <div className="text-center max-w-md">
        <Warning size={40} weight="duotone" className="text-destructive mx-auto mb-3" />
        <h3 className="font-heading text-xl font-semibold mb-2">Couldn't load the community view</h3>
        <p className="text-sm text-muted-foreground mb-4">{error}</p>
        <button onClick={load} className="pill px-5 py-2.5 bg-primary text-primary-foreground text-sm font-semibold" data-testid="community-retry">Try again</button>
      </div>
    </div>
  );
  if (!data) return null;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8 pb-24 md:pb-8 min-h-[calc(100vh-4rem)]" data-testid="community-page">
      <p className="text-sm font-bold uppercase tracking-[0.2em] text-primary mb-1">Community</p>
      <h1 className="font-heading text-3xl sm:text-4xl font-bold mb-2">What your neighbors have, need, and can do.</h1>
      <p className="text-muted-foreground mb-8 text-sm">Anonymized aggregate view of the whole exchange. No personal info — just the shape of your local economy.</p>

      {/* Emergency banner */}
      {data.emergency_count > 0 && (
        <section className="mb-8 rounded-2xl bg-destructive/10 border-2 border-destructive/50 p-6" data-testid="emergency-section">
          <div className="flex items-center gap-2 mb-4">
            <Warning size={26} weight="fill" className="text-destructive animate-pulse" />
            <h2 className="font-heading text-xl sm:text-2xl font-bold text-destructive">Urgent needs right now</h2>
            <span className="pill px-2 py-0.5 text-xs font-bold bg-destructive text-destructive-foreground">{data.emergency_count}</span>
          </div>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {data.emergency.map((l) => <ListingCard key={l.listing_id} listing={l} />)}
          </div>
        </section>
      )}

      {/* Top-line stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-8">
        <Stat icon={Users} n={data.total_users} label="Traders" />
        <Stat icon={Package} n={data.by_kind.have} label="Haves" />
        <Stat icon={Handshake} n={data.by_kind.need} label="Needs" />
        <Stat icon={Wrench} n={data.by_kind.service} label="Skills" />
      </div>
      <div className="grid grid-cols-2 gap-3 mb-10">
        <Stat icon={TrendUp} n={data.completed_trades} label="Trades completed all-time" />
        <Stat icon={TrendUp} n={data.recent_completed_30d} label="Completed in the last 30 days" />
      </div>

      {/* Category breakdown */}
      <section className="mb-10">
        <h2 className="font-heading font-semibold text-xl mb-4">By category</h2>
        <div className="rounded-2xl bg-card border border-border overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-muted/50">
              <tr className="text-left">
                <th className="p-3">Category</th>
                <th className="p-3 text-right">Have</th>
                <th className="p-3 text-right">Need</th>
                <th className="p-3 text-right">Skill</th>
                <th className="p-3 text-right">Total</th>
              </tr>
            </thead>
            <tbody>
              {data.by_category.map((c) => (
                <tr key={c.category} className="border-t border-border" data-testid={`cat-row-${c.category}`}>
                  <td className="p-3 font-medium">{c.category}</td>
                  <td className="p-3 text-right">{c.have}</td>
                  <td className="p-3 text-right">{c.need}</td>
                  <td className="p-3 text-right">{c.service}</td>
                  <td className="p-3 text-right font-heading font-semibold text-primary">{c.total}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Top skills */}
      {data.top_services.length > 0 && (
        <section className="mb-10">
          <h2 className="font-heading font-semibold text-xl mb-4">Skills offered locally</h2>
          <div className="flex flex-wrap gap-2">
            {data.top_services.map((s) => (
              <span key={s} className="pill px-4 py-2 bg-muted text-sm font-medium">{s}</span>
            ))}
          </div>
        </section>
      )}

      <div className="pt-6 border-t border-border text-center">
        <Link to="/discover" className="text-primary font-medium">Browse all listings →</Link>
      </div>
    </div>
  );
}

function Stat({ icon: Icon, n, label }) {
  return (
    <div className="rounded-2xl bg-card border border-border p-5">
      <Icon size={22} weight="duotone" className="text-primary mb-2" />
      <div className="font-heading text-2xl font-bold leading-none">{n}</div>
      <div className="text-xs text-muted-foreground mt-1">{label}</div>
    </div>
  );
}
