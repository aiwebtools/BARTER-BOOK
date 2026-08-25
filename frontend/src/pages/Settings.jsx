import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";
import { useNavigate } from "react-router-dom";
import api from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { toast } from "sonner";
import { Bell, Trash, Warning, EnvelopeSimple, User, Prohibit } from "@phosphor-icons/react";

export default function Settings() {
  const { user, refresh, logout } = useAuth();
  const nav = useNavigate();
  const [form, setForm] = useState(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!user) return;
    setForm({
      first_name: user.first_name || "",
      username: user.username || "",
      email_notifications: user.email_notifications !== false,
      notify_matches: user.notify_matches !== false,
      notify_messages: user.notify_messages !== false,
      notify_trades: user.notify_trades !== false,
    });
  }, [user]);

  const save = async () => {
    setSaving(true);
    try {
      await api.patch("/profile", form);
      await refresh();
      toast.success("Settings saved");
    } catch { toast.error("Failed"); }
    finally { setSaving(false); }
  };

  const clearNotifs = async () => {
    if (!window.confirm("Clear ALL notifications?")) return;
    await api.delete("/notifications");
    toast.success("Notifications cleared");
  };

  const deleteAccount = async () => {
    const confirm1 = window.prompt("Type DELETE to permanently delete your account. Trade history stays with the other party. This cannot be undone.");
    if (confirm1 !== "DELETE") { toast.error("Cancelled"); return; }
    try {
      await api.delete("/account");
      await logout();
      toast.success("Account deleted");
      nav("/");
    } catch { toast.error("Failed"); }
  };

  if (!form) return null;

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 py-8 pb-24 md:pb-8" data-testid="settings-page">
      <p className="text-sm font-bold uppercase tracking-[0.2em] text-primary mb-1">Settings</p>
      <h1 className="font-heading text-3xl sm:text-4xl font-bold mb-8">Your account.</h1>

      {/* Identity */}
      <section className="rounded-2xl bg-card border border-border p-6 sm:p-8 mb-5">
        <div className="flex items-center gap-2 mb-4">
          <User size={22} weight="duotone" className="text-primary" />
          <h2 className="font-heading font-semibold text-xl">Identity</h2>
        </div>
        <div className="space-y-4">
          <div>
            <Label>First name (private — used in greetings only)</Label>
            <Input value={form.first_name} onChange={(e) => setForm({ ...form, first_name: e.target.value })} className="h-12 rounded-xl mt-1" data-testid="settings-first-name" placeholder="First name" />
          </div>
          <div>
            <Label>Username (public @handle)</Label>
            <div className="flex items-center gap-2 mt-1">
              <span className="pill px-3 h-12 grid place-items-center bg-muted text-sm font-medium">@</span>
              <Input value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, "") })} className="h-12 rounded-xl flex-1" data-testid="settings-username" placeholder="yourhandle" />
            </div>
            <p className="text-xs text-muted-foreground mt-1">Anon-friendly. Only lowercase letters, numbers, and underscore.</p>
          </div>
        </div>
      </section>

      {/* Notifications */}
      <section className="rounded-2xl bg-card border border-border p-6 sm:p-8 mb-5" data-testid="notif-settings">
        <div className="flex items-center gap-2 mb-4">
          <Bell size={22} weight="duotone" className="text-primary" />
          <h2 className="font-heading font-semibold text-xl">Notifications</h2>
        </div>
        <div className="space-y-4">
          <Row label="Email notifications" desc="Receive email when someone interacts with you" checked={form.email_notifications} onChange={(v) => setForm({ ...form, email_notifications: v })} tid="opt-email" />
          <Row label="Match notifications" desc="Alert me when a potential match appears" checked={form.notify_matches} onChange={(v) => setForm({ ...form, notify_matches: v })} tid="opt-matches" />
          <Row label="Message notifications" desc="Alert me on direct messages and trade chats" checked={form.notify_messages} onChange={(v) => setForm({ ...form, notify_messages: v })} tid="opt-messages" />
          <Row label="Trade updates" desc="Alert me on proposals, accepts, meetups, and completions" checked={form.notify_trades} onChange={(v) => setForm({ ...form, notify_trades: v })} tid="opt-trades" />
        </div>
        <div className="mt-5 pt-5 border-t border-border flex flex-wrap gap-2">
          <Button variant="outline" className="rounded-full" onClick={clearNotifs} data-testid="clear-notifs"><Trash size={16} className="mr-1" /> Clear all notifications</Button>
        </div>
      </section>

      {/* Save button */}
      <div className="sticky bottom-16 md:bottom-6 z-10 bg-background/80 backdrop-blur -mx-4 sm:-mx-6 px-4 sm:px-6 py-3 border-t border-border md:border-0">
        <Button onClick={save} disabled={saving} className="rounded-full h-12 px-8 w-full sm:w-auto shine glow-primary" data-testid="settings-save">
          {saving ? "Saving…" : "Save settings"}
        </Button>
      </div>

      {/* Danger zone */}
      <section className="rounded-2xl bg-card border border-destructive/40 p-6 sm:p-8 mt-8" data-testid="danger-zone">
        <div className="flex items-center gap-2 mb-3">
          <Warning size={22} weight="duotone" className="text-destructive" />
          <h2 className="font-heading font-semibold text-xl">Danger zone</h2>
        </div>
        <p className="text-sm text-muted-foreground mb-4">Deleting your account removes your listings and personal info. Trade history with other users is retained so their reputation stays intact.</p>
        <Button variant="destructive" className="rounded-full" onClick={deleteAccount} data-testid="delete-account"><Prohibit size={16} className="mr-1" /> Delete my account</Button>
      </section>
    </div>
  );
}

function Row({ label, desc, checked, onChange, tid }) {
  return (
    <div className="flex items-start justify-between gap-4 py-2">
      <div className="flex-1 min-w-0">
        <div className="font-medium">{label}</div>
        <p className="text-xs text-muted-foreground">{desc}</p>
      </div>
      <Switch checked={checked} onCheckedChange={onChange} data-testid={tid} />
    </div>
  );
}
