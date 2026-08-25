import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";
import api, { BACKEND_URL } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { CheckCircle, MapPinLine, Star, ShieldCheck, Camera, Storefront, CurrencyDollar, Link as LinkIcon } from "@phosphor-icons/react";
import { ReferralPanel } from "@/pages/Referral";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";

export default function Profile() {
  const { user, refresh } = useAuth();
  const [form, setForm] = useState(null);
  const [saving, setSaving] = useState(false);
  const [ratings, setRatings] = useState([]);
  const [uploadingBanner, setUploadingBanner] = useState(false);
  const [uploadingAvatar, setUploadingAvatar] = useState(false);

  useEffect(() => {
    if (!user) return;
    setForm({
      display_name: user.display_name || "",
      bio: user.bio || "",
      city: user.city || "",
      state: user.state || "",
      search_radius_miles: user.search_radius_miles || 10,
      picture: user.picture || "",
      store_name: user.store_name || "",
      store_tagline: user.store_tagline || "",
      banner_photo: user.banner_photo || "",
      accent_color: user.accent_color || "",
      cashapp_tag: user.cashapp_tag || "",
      venmo_tag: user.venmo_tag || "",
      paypal_link: user.paypal_link || "",
      bitcoin_address: user.bitcoin_address || "",
      solana_address: user.solana_address || "",
      ethereum_address: user.ethereum_address || "",
      accepts_donations: user.accepts_donations || false,
    });
    api.get(`/users/${user.user_id}/ratings`).then((r) => setRatings(r.data));
  }, [user]);

  const save = async () => {
    setSaving(true);
    try {
      await api.patch("/profile", form);
      await refresh();
      toast.success("Profile updated");
    } catch { toast.error("Failed"); }
    finally { setSaving(false); }
  };

  const uploadPhoto = async (file, setter, setLoading) => {
    setLoading(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const r = await api.post("/upload", fd, { headers: { "Content-Type": "multipart/form-data" } });
      setForm((f) => ({ ...f, [setter]: `${BACKEND_URL}/api/files/${r.data.file_id}` }));
      toast.success("Photo uploaded — remember to Save");
    } catch { toast.error("Upload failed"); }
    finally { setLoading(false); }
  };

  if (!user || !form) return null;

  const inviteUrl = user.user_id ? `${window.location.origin}/u/${user.user_id}` : "";

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 py-8 pb-24 md:pb-8" data-testid="profile-page">
      {/* Header with storefront preview */}
      <div className="rounded-2xl bg-card border border-border overflow-hidden mb-6">
        <div className="relative h-40 sm:h-48 bg-accent" style={form.banner_photo ? { backgroundImage: `url(${form.banner_photo})`, backgroundSize: "cover", backgroundPosition: "center" } : {}}>
          <label className="absolute right-3 top-3 pill px-3 py-1.5 text-xs bg-background/90 backdrop-blur border border-border cursor-pointer flex items-center gap-1 font-medium" data-testid="upload-banner">
            <Camera size={14} weight="duotone" /> {uploadingBanner ? "Uploading…" : "Change banner"}
            <input type="file" accept="image/*" className="hidden" disabled={uploadingBanner} onChange={(e) => e.target.files?.[0] && uploadPhoto(e.target.files[0], "banner_photo", setUploadingBanner)} />
          </label>
        </div>
        <div className="p-6 sm:p-8 -mt-12 flex flex-col sm:flex-row items-start sm:items-end gap-4">
          <div className="relative">
            <div className="w-24 h-24 rounded-full bg-muted border-4 border-card grid place-items-center overflow-hidden">
              {form.picture ? <img src={form.picture} alt="" className="w-full h-full object-cover" /> : <span className="font-heading text-3xl font-bold">{user.display_name?.[0]}</span>}
            </div>
            <label className="absolute -bottom-1 -right-1 w-8 h-8 rounded-full bg-primary text-primary-foreground grid place-items-center cursor-pointer" data-testid="upload-avatar">
              <Camera size={14} weight="fill" />
              <input type="file" accept="image/*" className="hidden" disabled={uploadingAvatar} onChange={(e) => e.target.files?.[0] && uploadPhoto(e.target.files[0], "picture", setUploadingAvatar)} />
            </label>
          </div>
          <div className="flex-1 min-w-0">
            <h1 className="font-heading text-2xl sm:text-3xl font-bold">{form.store_name || user.display_name}</h1>
            {form.store_tagline && <p className="text-muted-foreground text-sm">{form.store_tagline}</p>}
            <div className="flex flex-wrap gap-2 mt-2">
              {user.email_verified && <span className="pill px-2.5 py-0.5 text-xs bg-accent text-accent-foreground flex items-center gap-1"><ShieldCheck size={12} weight="fill" /> Verified</span>}
              {user.verified_referral && <span className="pill px-2.5 py-0.5 text-xs bg-primary text-primary-foreground flex items-center gap-1"><CheckCircle size={12} weight="fill" /> Trusted</span>}
              <span className="pill px-2.5 py-0.5 text-xs bg-muted flex items-center gap-1"><Star size={12} weight="fill" className="text-secondary" /> {(user.reputation_score || 0).toFixed(1)}</span>
              <span className="pill px-2.5 py-0.5 text-xs bg-muted">{user.successful_trades} trades</span>
              <span className="pill px-2.5 py-0.5 text-xs bg-muted flex items-center gap-1"><MapPinLine size={12} weight="fill" /> {user.city || "—"}, {user.state}</span>
            </div>
          </div>
          <a href={`/u/${user.user_id}`} target="_blank" rel="noreferrer" className="pill px-4 py-2 text-sm border border-border hover:bg-muted transition-colors flex items-center gap-1 font-medium" data-testid="view-store"><Storefront size={16} weight="duotone" /> View storefront</a>
        </div>
      </div>

      <Tabs defaultValue="basics" className="space-y-6">
        <TabsList className="h-auto bg-transparent p-0 gap-2 flex-wrap">
          <TabsTrigger value="basics" className="pill h-10 px-5 border border-border data-[state=active]:bg-primary data-[state=active]:text-primary-foreground" data-testid="tab-basics">Basics</TabsTrigger>
          <TabsTrigger value="store" className="pill h-10 px-5 border border-border data-[state=active]:bg-primary data-[state=active]:text-primary-foreground" data-testid="tab-store">My Store</TabsTrigger>
          <TabsTrigger value="payments" className="pill h-10 px-5 border border-border data-[state=active]:bg-primary data-[state=active]:text-primary-foreground" data-testid="tab-payments">Payment Handles</TabsTrigger>
          <TabsTrigger value="referral" className="pill h-10 px-5 border border-border data-[state=active]:bg-primary data-[state=active]:text-primary-foreground" data-testid="tab-referral">Invite Friends</TabsTrigger>
          <TabsTrigger value="reviews" className="pill h-10 px-5 border border-border data-[state=active]:bg-primary data-[state=active]:text-primary-foreground" data-testid="tab-reviews">Reviews</TabsTrigger>
        </TabsList>

        {/* BASICS */}
        <TabsContent value="basics">
          <div className="rounded-2xl bg-card border border-border p-6 sm:p-8 space-y-5">
            <div>
              <Label>Display name</Label>
              <Input value={form.display_name} onChange={(e) => setForm({ ...form, display_name: e.target.value })} className="h-12 rounded-xl mt-1" data-testid="profile-name" />
            </div>
            <div>
              <Label>Bio</Label>
              <Textarea value={form.bio} onChange={(e) => setForm({ ...form, bio: e.target.value })} className="rounded-xl mt-1" placeholder="Tell your neighbors about yourself…" data-testid="profile-bio" />
            </div>
            <div className="grid sm:grid-cols-2 gap-4">
              <div><Label>City</Label><Input value={form.city} onChange={(e) => setForm({ ...form, city: e.target.value })} className="h-12 rounded-xl mt-1" data-testid="profile-city" /></div>
              <div><Label>State</Label><Input value={form.state} onChange={(e) => setForm({ ...form, state: e.target.value })} className="h-12 rounded-xl mt-1" data-testid="profile-state" /></div>
            </div>
            <div>
              <Label>Search radius: {form.search_radius_miles} miles</Label>
              <input type="range" min="1" max="50" value={form.search_radius_miles} onChange={(e) => setForm({ ...form, search_radius_miles: Number(e.target.value) })} className="w-full mt-2" data-testid="profile-radius" />
            </div>
            <Button onClick={save} disabled={saving} className="rounded-full h-12 px-8" data-testid="profile-save">{saving ? "Saving…" : "Save changes"}</Button>
          </div>
        </TabsContent>

        {/* STORE */}
        <TabsContent value="store">
          <div className="rounded-2xl bg-card border border-border p-6 sm:p-8 space-y-5" data-testid="store-form">
            <div className="flex items-start gap-3 rounded-xl bg-accent/40 border border-border p-4">
              <Storefront size={22} weight="duotone" className="text-primary mt-0.5 shrink-0" />
              <div className="text-sm">
                <p className="font-semibold">Your BarterGrid storefront</p>
                <p className="text-muted-foreground">Customize how your public profile looks. It'll show your listings, reputation, and any payment handles you choose to share.</p>
              </div>
            </div>
            <div>
              <Label>Store name (shown on your public profile)</Label>
              <Input value={form.store_name} onChange={(e) => setForm({ ...form, store_name: e.target.value })} className="h-12 rounded-xl mt-1" placeholder={`${user.display_name}'s Barter Corner`} data-testid="store-name" />
            </div>
            <div>
              <Label>Tagline</Label>
              <Input value={form.store_tagline} onChange={(e) => setForm({ ...form, store_tagline: e.target.value })} className="h-12 rounded-xl mt-1" placeholder="Tools, garden goods, and a bit of everything." data-testid="store-tagline" />
            </div>
            <div>
              <Label>Accent color (hex, e.g. #2f5f3d)</Label>
              <div className="flex gap-2 mt-1">
                <Input value={form.accent_color} onChange={(e) => setForm({ ...form, accent_color: e.target.value })} className="h-12 rounded-xl flex-1" placeholder="#2f5f3d" data-testid="store-accent" />
                <div className="h-12 w-12 rounded-xl border border-border" style={{ background: form.accent_color || "transparent" }} />
              </div>
            </div>
            <p className="text-sm text-muted-foreground">Your public storefront: <a href={inviteUrl} target="_blank" rel="noreferrer" className="text-primary font-medium">{inviteUrl}</a></p>
            <Button onClick={save} disabled={saving} className="rounded-full h-12 px-8" data-testid="store-save">{saving ? "Saving…" : "Save storefront"}</Button>
          </div>
        </TabsContent>

        {/* PAYMENTS */}
        <TabsContent value="payments">
          <div className="rounded-2xl bg-card border border-border p-6 sm:p-8 space-y-5" data-testid="payment-form">
            <div className="flex items-start gap-3 rounded-xl bg-secondary/10 border border-secondary/30 p-4">
              <CurrencyDollar size={22} weight="duotone" className="text-secondary mt-0.5 shrink-0" />
              <div className="text-sm">
                <p className="font-semibold">Optional — payment handles</p>
                <p className="text-muted-foreground">BarterGrid is a barter network. These are only for the times when a neighbor wants to tip, cover a difference, or send you money outside the app. Only fill in what you're comfortable making public.</p>
              </div>
            </div>

            <div className="grid sm:grid-cols-2 gap-4">
              <PayField label="CashApp $tag" prefix="$" value={form.cashapp_tag} onChange={(v) => setForm({ ...form, cashapp_tag: v })} placeholder="yourtag" testid="pay-cashapp" />
              <PayField label="Venmo @tag" prefix="@" value={form.venmo_tag} onChange={(v) => setForm({ ...form, venmo_tag: v })} placeholder="yourtag" testid="pay-venmo" />
              <PayField label="PayPal.me link" value={form.paypal_link} onChange={(v) => setForm({ ...form, paypal_link: v })} placeholder="paypal.me/yourname" testid="pay-paypal" />
              <PayField label="Bitcoin address" value={form.bitcoin_address} onChange={(v) => setForm({ ...form, bitcoin_address: v })} placeholder="bc1q…" mono testid="pay-btc" />
              <PayField label="Solana address" value={form.solana_address} onChange={(v) => setForm({ ...form, solana_address: v })} placeholder="Solana pubkey" mono testid="pay-sol" />
              <PayField label="Ethereum / EVM address" value={form.ethereum_address} onChange={(v) => setForm({ ...form, ethereum_address: v })} placeholder="0x…" mono testid="pay-eth" />
            </div>

            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={!!form.accepts_donations} onChange={(e) => setForm({ ...form, accepts_donations: e.target.checked })} data-testid="accepts-donations" />
              Show a "Tip / Send" section on my public storefront
            </label>

            <div className="rounded-xl bg-muted/50 border border-border p-4 text-xs text-muted-foreground flex items-start gap-2">
              <LinkIcon size={14} className="mt-0.5 shrink-0" />
              <span>BarterGrid does not process payments. These handles are shown as-is to other users. Never share private keys or seed phrases.</span>
            </div>

            <Button onClick={save} disabled={saving} className="rounded-full h-12 px-8" data-testid="payments-save">{saving ? "Saving…" : "Save payment handles"}</Button>
          </div>
        </TabsContent>

        {/* REFERRAL */}
        <TabsContent value="referral">
          <ReferralPanel />
        </TabsContent>

        {/* REVIEWS */}
        <TabsContent value="reviews">
          <div className="rounded-2xl bg-card border border-border p-6 sm:p-8">
            <h2 className="font-heading font-semibold text-xl mb-4">Recent reviews</h2>
            {ratings.length === 0 ? (
              <p className="text-sm text-muted-foreground">No reviews yet. Complete a trade to earn your first star.</p>
            ) : (
              <div className="space-y-3">
                {ratings.map((r) => (
                  <div key={r.id} className="border-b border-border pb-3 last:border-0">
                    <div className="flex items-center gap-1 mb-1">
                      {[...Array(5)].map((_, i) => <Star key={i} size={14} weight="fill" className={i < r.stars ? "text-secondary" : "text-muted"} />)}
                    </div>
                    {r.comment && <p className="text-sm text-muted-foreground">{r.comment}</p>}
                    <p className="text-xs text-muted-foreground mt-1">{new Date(r.created_at).toLocaleDateString()}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}

function PayField({ label, prefix, value, onChange, placeholder, mono, testid }) {
  return (
    <div>
      <Label>{label}</Label>
      <div className="flex items-center gap-2 mt-1">
        {prefix && <span className="pill px-3 h-12 grid place-items-center bg-muted text-sm font-medium">{prefix}</span>}
        <Input value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder} className={`h-12 rounded-xl flex-1 ${mono ? "font-mono text-xs" : ""}`} data-testid={testid} />
      </div>
    </div>
  );
}
