import { useEffect, useState, useCallback } from "react";
import { Link, useNavigate } from "react-router-dom";
import api from "@/lib/api";
import { useAuth } from "@/lib/auth";
import ListingCard from "@/components/ListingCard";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { CATEGORIES } from "@/lib/api";
import { MagnifyingGlass } from "@phosphor-icons/react";

export default function Discover() {
  const nav = useNavigate();
  const { user } = useAuth();
  const [items, setItems] = useState([]);
  const [q, setQ] = useState("");
  const [kind, setKind] = useState("");
  const [category, setCategory] = useState("");
  const [radius, setRadius] = useState("");
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    const params = new URLSearchParams();
    if (q) params.set("q", q);
    if (kind) params.set("kind", kind);
    if (category) params.set("category", category);
    if (radius) params.set("radius", radius);
    try {
      const r = await api.get(`/listings?${params.toString()}`);
      setItems(r.data);
    } catch (e) {
      console.warn("[discover] load failed", e?.response?.status || e?.message);
    } finally { setLoading(false); }
  }, [q, kind, category, radius]);

  useEffect(() => { load(); }, [load]);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8 pb-24 md:pb-8" data-testid="discover-page">
      {!user && (
        <div className="mb-6 rounded-2xl bg-primary/10 border border-primary/30 p-5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3" data-testid="guest-banner">
          <div>
            <p className="font-heading font-semibold text-lg">Preview mode — you're browsing as a guest.</p>
            <p className="text-sm text-muted-foreground">Create a free account to message traders, propose swaps, and post your own listings.</p>
          </div>
          <div className="flex gap-2 shrink-0">
            <Button variant="outline" onClick={() => nav("/login")} className="rounded-full" data-testid="guest-signin">Sign in</Button>
            <Button onClick={() => nav("/signup")} className="rounded-full shine" data-testid="guest-signup">Sign up free</Button>
          </div>
        </div>
      )}
      <div className="mb-6">
        <p className="text-sm font-bold uppercase tracking-[0.2em] text-primary mb-1">Discover</p>
        <h1 className="font-heading text-3xl sm:text-4xl font-bold">What's nearby right now.</h1>
      </div>

      <div className="rounded-2xl border border-border bg-card p-4 sm:p-5 mb-8 flex flex-col md:flex-row gap-3">
        <div className="relative flex-1">
          <MagnifyingGlass size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-muted-foreground" />
          <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search items, tools, skills…" className="h-12 rounded-full pl-11" data-testid="discover-search" />
        </div>
        <select value={category} onChange={(e) => setCategory(e.target.value)} className="h-12 rounded-full border border-border bg-background px-4 text-sm" data-testid="discover-category">
          <option value="">All categories</option>
          {CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
        <select value={radius} onChange={(e) => setRadius(e.target.value)} className="h-12 rounded-full border border-border bg-background px-4 text-sm" data-testid="discover-radius">
          <option value="">Any distance</option>
          <option value="1">1 mile</option>
          <option value="5">5 miles</option>
          <option value="10">10 miles</option>
          <option value="25">25 miles</option>
          <option value="50">50 miles</option>
        </select>
      </div>

      <Tabs value={kind || "all"} onValueChange={(v) => setKind(v === "all" ? "" : v)} className="mb-6">
        <TabsList className="h-auto bg-transparent p-0 gap-2 flex-wrap">
          <TabsTrigger value="all" className="pill h-10 px-5 data-[state=active]:bg-primary data-[state=active]:text-primary-foreground border border-border" data-testid="tab-all">For You</TabsTrigger>
          <TabsTrigger value="have" className="pill h-10 px-5 data-[state=active]:bg-primary data-[state=active]:text-primary-foreground border border-border" data-testid="tab-have">I Have</TabsTrigger>
          <TabsTrigger value="need" className="pill h-10 px-5 data-[state=active]:bg-primary data-[state=active]:text-primary-foreground border border-border" data-testid="tab-need">I Need</TabsTrigger>
          <TabsTrigger value="service" className="pill h-10 px-5 data-[state=active]:bg-primary data-[state=active]:text-primary-foreground border border-border" data-testid="tab-service">Services</TabsTrigger>
        </TabsList>
      </Tabs>

      {loading ? (
        <div className="text-center py-16 text-muted-foreground">Loading…</div>
      ) : items.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-border p-10 text-center">
          <h3 className="font-heading font-semibold text-lg mb-2">Nothing here yet</h3>
          <p className="text-sm text-muted-foreground mb-5">Try expanding your search or being the first to post!</p>
          <Button onClick={() => nav("/new")} className="rounded-full">Post something</Button>
        </div>
      ) : (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {items.map((l) => <ListingCard key={l.listing_id} listing={l} />)}
        </div>
      )}
    </div>
  );
}
