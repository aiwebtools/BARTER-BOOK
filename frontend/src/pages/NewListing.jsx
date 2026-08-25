import { useState } from "react";
import { useNavigate } from "react-router-dom";
import api, { CATEGORIES, BACKEND_URL } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";
import { Package, Handshake, Wrench, X, Camera } from "@phosphor-icons/react";

const KINDS = [
  { value: "have", label: "I HAVE something", desc: "An item to trade or give away", icon: Package, cls: "bg-accent text-accent-foreground" },
  { value: "need", label: "I NEED something", desc: "Looking for a specific item", icon: Handshake, cls: "bg-secondary text-secondary-foreground" },
  { value: "service", label: "I CAN DO something", desc: "Offer a skill or service", icon: Wrench, cls: "bg-primary text-primary-foreground" },
];

export default function NewListing() {
  const nav = useNavigate();
  const [kind, setKind] = useState("have");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState(CATEGORIES[0]);
  const [condition, setCondition] = useState("Good");
  const [quantity, setQuantity] = useState("");
  const [wants, setWants] = useState([]);
  const [wantInput, setWantInput] = useState("");
  const [photos, setPhotos] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [suggesting, setSuggesting] = useState(false);
  const [ships, setShips] = useState(false);
  const [shippingFee, setShippingFee] = useState("");
  const [shippingNotes, setShippingNotes] = useState("");

  const upload = async (file) => {
    setUploading(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const r = await api.post("/upload", fd, { headers: { "Content-Type": "multipart/form-data" } });
      setPhotos((p) => [...p, `${BACKEND_URL}/api/files/${r.data.file_id}`]);
      toast.success("Photo added");
    } catch (e) {
      toast.error("Upload failed");
    } finally { setUploading(false); }
  };

  const aiSuggest = async () => {
    if (!title.trim()) { toast.error("Add a title first"); return; }
    setSuggesting(true);
    try {
      const r = await api.post("/ai/suggest-category", { title, description });
      if (r.data?.category) { setCategory(r.data.category); toast.success(`AI suggests: ${r.data.category}`); }
    } catch { toast.error("Couldn't reach AI"); }
    finally { setSuggesting(false); }
  };

  const submit = async () => {
    if (!title.trim()) { toast.error("Add a title"); return; }
    setSaving(true);
    try {
      await api.post("/listings", {
        kind, title, description, category,
        condition: kind === "have" ? condition : null,
        quantity: quantity || null,
        wants: kind === "have" ? wants : [],
        photos, tags: [],
        ships, shipping_fee: ships ? (shippingFee || null) : null,
        shipping_notes: ships ? (shippingNotes || null) : null,
      });
      toast.success("Listing posted!");
      nav("/listings");
    } catch (e) {
      const msg = e.response?.data?.detail || "Couldn't post listing";
      toast.error(msg);
    } finally { setSaving(false); }
  };

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 py-8 pb-24 md:pb-16" data-testid="new-listing-page">
      <p className="text-sm font-bold uppercase tracking-[0.2em] text-primary mb-1">Post something</p>
      <h1 className="font-heading text-3xl sm:text-4xl font-bold mb-8">What are you doing?</h1>

      <div className="grid sm:grid-cols-3 gap-3 mb-8">
        {KINDS.map((k) => (
          <button
            key={k.value}
            onClick={() => setKind(k.value)}
            data-testid={`kind-${k.value}`}
            className={`text-left rounded-2xl border-2 p-5 transition-colors ${kind === k.value ? "border-primary bg-accent/50" : "border-border bg-card hover:border-primary/40"}`}
          >
            <span className={`inline-flex pill px-3 py-1 text-xs font-bold mb-3 ${k.cls}`}>{k.label.split(" ")[1]}</span>
            <k.icon size={26} weight="duotone" className="text-primary mb-2" />
            <div className="font-heading font-semibold">{k.label}</div>
            <div className="text-xs text-muted-foreground mt-1">{k.desc}</div>
          </button>
        ))}
      </div>

      <div className="rounded-2xl bg-card border border-border p-6 sm:p-8 space-y-5">
        <div>
          <Label htmlFor="title">Title</Label>
          <Input id="title" value={title} onChange={(e) => setTitle(e.target.value)} className="h-12 rounded-xl mt-1" placeholder={kind === "service" ? "e.g. Bicycle repair" : "e.g. Water Filter"} data-testid="listing-title" />
        </div>
        <div>
          <Label htmlFor="desc">Description</Label>
          <Textarea id="desc" value={description} onChange={(e) => setDescription(e.target.value)} className="rounded-xl mt-1 min-h-[120px]" placeholder="Add details, condition, timing…" data-testid="listing-description" />
        </div>
        <div className="grid sm:grid-cols-2 gap-4">
          <div>
            <div className="flex items-center justify-between">
              <Label htmlFor="cat">Category</Label>
              <button type="button" onClick={aiSuggest} disabled={suggesting} className="text-xs font-medium text-primary hover:underline disabled:opacity-50" data-testid="ai-suggest-category">
                {suggesting ? "AI thinking…" : "✨ Ask AI"}
              </button>
            </div>
            <select id="cat" value={category} onChange={(e) => setCategory(e.target.value)} className="h-12 w-full rounded-xl border border-border bg-background px-3 mt-1" data-testid="listing-category">
              {CATEGORIES.map((c) => <option key={c}>{c}</option>)}
            </select>
          </div>
          {kind === "have" && (
            <div>
              <Label htmlFor="cond">Condition</Label>
              <select id="cond" value={condition} onChange={(e) => setCondition(e.target.value)} className="h-12 w-full rounded-xl border border-border bg-background px-3 mt-1" data-testid="listing-condition">
                {["New", "Like New", "Good", "Fair", "For Parts"].map((c) => <option key={c}>{c}</option>)}
              </select>
            </div>
          )}
        </div>

        {kind !== "need" && (
          <div className="rounded-xl border border-border p-4 bg-background">
            <label className="flex items-center gap-2 font-medium cursor-pointer">
              <input type="checkbox" checked={ships} onChange={(e) => setShips(e.target.checked)} data-testid="listing-ships" />
              Willing to ship this item
            </label>
            {ships && (
              <div className="mt-3 grid sm:grid-cols-2 gap-3">
                <Input placeholder="Shipping fee (e.g. $12 or trade extra)" value={shippingFee} onChange={(e) => setShippingFee(e.target.value)} className="h-11 rounded-xl" data-testid="listing-shipping-fee" />
                <Input placeholder="Notes (e.g. USPS, up to 5 lbs)" value={shippingNotes} onChange={(e) => setShippingNotes(e.target.value)} className="h-11 rounded-xl" data-testid="listing-shipping-notes" />
              </div>
            )}
          </div>
        )}

        {kind === "have" && (
          <div>
            <Label>What do you want in exchange?</Label>
            <div className="flex gap-2 mt-1">
              <Input value={wantInput} onChange={(e) => setWantInput(e.target.value)} placeholder="e.g. Bike lock" className="h-12 rounded-xl" onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); if (wantInput.trim()) { setWants([...wants, wantInput.trim()]); setWantInput(""); } } }} data-testid="listing-want-input" />
              <Button type="button" variant="outline" className="rounded-full h-12" onClick={() => { if (wantInput.trim()) { setWants([...wants, wantInput.trim()]); setWantInput(""); } }}>Add</Button>
            </div>
            {wants.length > 0 && (
              <div className="flex flex-wrap gap-2 mt-3">
                {wants.map((w, i) => (
                  <span key={i} className="pill px-3 py-1 bg-muted text-sm inline-flex items-center gap-1">
                    {w} <button onClick={() => setWants(wants.filter((_, j) => j !== i))} className="hover:text-destructive"><X size={14} /></button>
                  </span>
                ))}
              </div>
            )}
          </div>
        )}

        <div>
          <Label>Photos (optional)</Label>
          <div className="flex flex-wrap gap-3 mt-2">
            {photos.map((p, i) => (
              <div key={i} className="relative w-24 h-24 rounded-xl overflow-hidden border border-border">
                <img src={p} alt="" className="w-full h-full object-cover" />
                <button onClick={() => setPhotos(photos.filter((_, j) => j !== i))} className="absolute top-1 right-1 w-6 h-6 rounded-full bg-background/90 grid place-items-center"><X size={12} /></button>
              </div>
            ))}
            <label className="w-24 h-24 rounded-xl border-2 border-dashed border-border grid place-items-center cursor-pointer hover:border-primary transition-colors" data-testid="upload-photo">
              <Camera size={24} weight="duotone" className="text-muted-foreground" />
              <input type="file" accept="image/*" className="hidden" disabled={uploading} onChange={(e) => e.target.files?.[0] && upload(e.target.files[0])} />
            </label>
          </div>
          {uploading && <p className="text-xs text-muted-foreground mt-2">Uploading…</p>}
        </div>

        <Button onClick={submit} disabled={saving} className="w-full h-12 rounded-full" data-testid="listing-submit">
          {saving ? "Posting…" : "Post listing"}
        </Button>
      </div>
    </div>
  );
}
