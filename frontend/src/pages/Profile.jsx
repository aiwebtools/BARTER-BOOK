import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";
import api from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { CheckCircle, MapPinLine, Star, ShieldCheck } from "@phosphor-icons/react";

export default function Profile() {
  const { user, refresh } = useAuth();
  const [form, setForm] = useState({ display_name: "", bio: "", city: "", state: "", search_radius_miles: 10 });
  const [saving, setSaving] = useState(false);
  const [ratings, setRatings] = useState([]);

  useEffect(() => {
    if (user) {
      setForm({
        display_name: user.display_name || "",
        bio: user.bio || "",
        city: user.city || "",
        state: user.state || "",
        search_radius_miles: user.search_radius_miles || 10,
      });
      api.get(`/users/${user.user_id}/ratings`).then((r) => setRatings(r.data));
    }
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

  if (!user) return null;

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 py-8 pb-24 md:pb-8" data-testid="profile-page">
      <div className="flex flex-col sm:flex-row items-start sm:items-center gap-6 mb-8">
        <div className="w-24 h-24 rounded-full bg-muted grid place-items-center overflow-hidden">
          {user.picture ? <img src={user.picture} alt="" className="w-24 h-24 object-cover" /> : <span className="font-heading text-3xl font-bold">{user.display_name?.[0]}</span>}
        </div>
        <div className="flex-1">
          <h1 className="font-heading text-3xl font-bold">{user.display_name}</h1>
          <p className="text-muted-foreground flex items-center gap-1.5 mt-1"><MapPinLine size={16} weight="duotone" /> {user.city || "No location set"}, {user.state}</p>
          <div className="flex flex-wrap gap-2 mt-3">
            {user.email_verified && <span className="pill px-3 py-1 text-xs bg-accent text-accent-foreground flex items-center gap-1"><ShieldCheck size={12} weight="fill" /> Email verified</span>}
            <span className="pill px-3 py-1 text-xs bg-muted flex items-center gap-1"><Star size={12} weight="fill" className="text-secondary" /> {(user.reputation_score || 0).toFixed(1)}</span>
            <span className="pill px-3 py-1 text-xs bg-muted flex items-center gap-1"><CheckCircle size={12} weight="fill" /> {user.successful_trades} trades</span>
          </div>
        </div>
      </div>

      <div className="rounded-2xl bg-card border border-border p-6 sm:p-8 space-y-5 mb-6">
        <h2 className="font-heading font-semibold text-xl">Edit profile</h2>
        <div>
          <Label>Display name</Label>
          <Input value={form.display_name} onChange={(e) => setForm({ ...form, display_name: e.target.value })} className="h-12 rounded-xl mt-1" data-testid="profile-name" />
        </div>
        <div>
          <Label>Bio</Label>
          <Textarea value={form.bio} onChange={(e) => setForm({ ...form, bio: e.target.value })} className="rounded-xl mt-1" data-testid="profile-bio" />
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

      {ratings.length > 0 && (
        <div className="rounded-2xl bg-card border border-border p-6 sm:p-8">
          <h2 className="font-heading font-semibold text-xl mb-4">Recent reviews</h2>
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
        </div>
      )}
    </div>
  );
}
