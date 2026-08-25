import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { toast } from "sonner";
import { Plus, Sparkle, Trash, ArrowsClockwise, MapPin } from "@phosphor-icons/react";
import { CATEGORIES } from "@/lib/api";

const URGENCY = {
  high: { label: "Urgent", cls: "bg-secondary text-secondary-foreground", dot: "bg-secondary" },
  normal: { label: "Normal", cls: "bg-accent text-accent-foreground", dot: "bg-yellow-500" },
  low: { label: "Nice-to-have", cls: "bg-muted text-muted-foreground", dot: "bg-primary" },
};

export default function Needs() {
  const [needs, setNeeds] = useState([]);
  const [matches, setMatches] = useState([]);
  const [adding, setAdding] = useState(false);
  const [form, setForm] = useState({ title: "", category: CATEGORIES[0], urgency: "normal", description: "" });
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    const [n, m] = await Promise.all([
      api.get("/listings?mine=true&kind=need"),
      api.get("/matches"),
    ]);
    setNeeds(n.data);
    setMatches(m.data);
    setLoading(false);
  };

  useEffect(() => { load(); }, []);

  const addNeed = async () => {
    if (!form.title.trim()) { toast.error("Add a title"); return; }
    try {
      await api.post("/listings", { kind: "need", ...form, photos: [], wants: [], tags: [], is_active: true });
      toast.success("Added to your needs");
      setForm({ title: "", category: CATEGORIES[0], urgency: "normal", description: "" });
      setAdding(false);
      load();
    } catch { toast.error("Failed"); }
  };

  const remove = async (id) => {
    if (!window.confirm("Remove this need?")) return;
    await api.delete(`/listings/${id}`);
    load();
  };

  // Map need id -> matching count
  const matchCountFor = (need) => {
    const nid = need.listing_id;
    return matches.filter((m) => m.their_listing.title.toLowerCase().split(/\s+/).some((tok) => need.title.toLowerCase().includes(tok) || (need.title.toLowerCase().split(/\s+/).includes(tok)))).length;
  };

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8 pb-24 md:pb-8" data-testid="needs-page">
      <div className="flex items-start justify-between mb-8 gap-4">
        <div>
          <p className="text-sm font-bold uppercase tracking-[0.2em] text-primary mb-1">My needs</p>
          <h1 className="font-heading text-3xl sm:text-4xl font-bold">Your persistent wish list.</h1>
          <p className="text-muted-foreground mt-2 text-sm">We'll ping you when someone nearby has something on this list.</p>
        </div>
        <Button onClick={() => setAdding(true)} className="rounded-full h-12 px-5 shrink-0" data-testid="add-need-btn"><Plus size={18} weight="bold" className="mr-1" /> Add need</Button>
      </div>

      {adding && (
        <div className="rounded-2xl bg-card border border-border p-6 mb-6" data-testid="add-need-form">
          <h3 className="font-heading font-semibold mb-4">Add a new need</h3>
          <div className="space-y-3">
            <Input placeholder="What do you need? e.g. Bike lock" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} className="h-12 rounded-xl" data-testid="need-title" />
            <Input placeholder="Details (optional)" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} className="h-12 rounded-xl" />
            <div className="grid sm:grid-cols-2 gap-3">
              <select value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} className="h-12 rounded-xl border border-border bg-background px-3" data-testid="need-category">
                {CATEGORIES.map((c) => <option key={c}>{c}</option>)}
              </select>
              <select value={form.urgency} onChange={(e) => setForm({ ...form, urgency: e.target.value })} className="h-12 rounded-xl border border-border bg-background px-3" data-testid="need-urgency">
                <option value="high">🔴 Urgent</option>
                <option value="normal">🟡 Normal</option>
                <option value="low">🟢 Nice-to-have</option>
              </select>
            </div>
            <div className="flex gap-2">
              <Button onClick={addNeed} className="rounded-full flex-1" data-testid="save-need">Save need</Button>
              <Button variant="outline" onClick={() => setAdding(false)} className="rounded-full">Cancel</Button>
            </div>
          </div>
        </div>
      )}

      {loading ? (
        <div className="text-center py-16 text-muted-foreground">Loading…</div>
      ) : needs.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-border p-16 text-center">
          <Sparkle size={40} weight="duotone" className="text-primary mx-auto mb-3" />
          <h3 className="font-heading font-semibold text-xl mb-2">Nothing on your list yet</h3>
          <p className="text-muted-foreground mb-6">Add the things you're looking for. We'll surface matches automatically.</p>
          <Button onClick={() => setAdding(true)} className="rounded-full">Add your first need</Button>
        </div>
      ) : (
        <div className="space-y-3">
          {needs.map((n) => {
            const u = URGENCY[n.urgency] || URGENCY.normal;
            const nMatches = matchCountFor(n);
            return (
              <div key={n.listing_id} className="rounded-2xl bg-card border border-border p-5 card-hover flex items-start gap-4" data-testid={`need-item-${n.listing_id}`}>
                <div className={`w-2 h-full min-h-[3rem] rounded-full ${u.dot}`} />
                <div className="flex-1 min-w-0">
                  <div className="flex flex-wrap items-center gap-2 mb-1">
                    <span className={`pill px-2.5 py-0.5 text-[10px] font-bold tracking-wide ${u.cls}`}>{u.label.toUpperCase()}</span>
                    <span className="text-xs text-muted-foreground">{n.category}</span>
                  </div>
                  <div className="font-heading font-semibold text-lg">{n.title}</div>
                  {n.description && <p className="text-sm text-muted-foreground line-clamp-1 mt-1">{n.description}</p>}
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  {nMatches > 0 && (
                    <Link to="/matches" className="pill px-3 py-1 text-xs font-semibold bg-primary text-primary-foreground flex items-center gap-1" data-testid={`match-count-${n.listing_id}`}>
                      <ArrowsClockwise size={14} weight="bold" /> {nMatches} match{nMatches === 1 ? "" : "es"}
                    </Link>
                  )}
                  <button onClick={() => remove(n.listing_id)} className="p-2 rounded-full hover:bg-muted transition-colors text-muted-foreground" data-testid={`remove-need-${n.listing_id}`}>
                    <Trash size={18} />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
