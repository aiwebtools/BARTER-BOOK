import { useEffect, useState, useCallback } from "react";
import { Link, useParams } from "react-router-dom";
import api from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { ShareNetwork, Copy, CheckCircle, Star, Sparkle } from "@phosphor-icons/react";

export function ReferralPanel() {
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [copied, setCopied] = useState(false);

  const load = useCallback(async () => {
    try {
      const r = await api.get("/referrals/mine");
      setData(r.data);
    } catch (e) {
      console.warn("[referral] load failed", e?.response?.status || e?.message);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  if (!data) return null;

  const inviteUrl = `${window.location.origin}/invite/${data.referral_code}`;

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(inviteUrl);
      setCopied(true);
      toast.success("Invite link copied!");
      setTimeout(() => setCopied(false), 2000);
    } catch { toast.error("Couldn't copy"); }
  };

  const share = async () => {
    if (navigator.share) {
      try { await navigator.share({ title: "Join me on BarterGrid", text: "Trade what you have for what you need — no price tags.", url: inviteUrl }); }
      catch { /* user cancelled */ }
    } else { copy(); }
  };

  return (
    <div className="rounded-2xl bg-card border border-border p-6 sm:p-8" data-testid="referral-panel">
      <div className="flex items-start justify-between gap-4 mb-4">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-primary mb-1">Referral Sparks</p>
          <h2 className="font-heading font-semibold text-xl">Invite a neighbor, both earn Verified.</h2>
          <p className="text-sm text-muted-foreground mt-1">When someone joins with your link and completes their first trade, you both get a <Star size={12} weight="fill" className="inline text-secondary" /> Verified badge.</p>
        </div>
        {user?.verified_referral && (
          <span className="pill px-3 py-1 text-xs font-bold bg-primary text-primary-foreground flex items-center gap-1 shrink-0"><CheckCircle size={14} weight="fill" /> Verified</span>
        )}
      </div>

      <div className="rounded-xl bg-muted/60 border border-border p-4 flex items-center justify-between gap-3 mb-3">
        <code className="text-sm truncate flex-1" data-testid="invite-url">{inviteUrl}</code>
        <Button size="sm" variant="outline" onClick={copy} className="rounded-full shrink-0" data-testid="copy-invite">
          {copied ? <CheckCircle size={16} className="mr-1" weight="fill" /> : <Copy size={16} className="mr-1" />} {copied ? "Copied" : "Copy"}
        </Button>
      </div>
      <Button onClick={share} className="rounded-full w-full h-11" data-testid="share-invite"><ShareNetwork size={18} className="mr-1" weight="bold" /> Share invite</Button>

      <div className="grid grid-cols-2 gap-3 mt-5 pt-5 border-t border-border">
        <div className="text-center">
          <div className="font-heading text-2xl font-bold">{data.referred_count}</div>
          <div className="text-xs text-muted-foreground">Invited</div>
        </div>
        <div className="text-center">
          <div className="font-heading text-2xl font-bold text-primary">{data.verified_count}</div>
          <div className="text-xs text-muted-foreground">Completed a trade</div>
        </div>
      </div>

      {data.referred_users?.length > 0 && (
        <div className="mt-5 pt-5 border-t border-border">
          <p className="text-xs font-bold uppercase tracking-widest text-muted-foreground mb-3">Your neighbors</p>
          <div className="space-y-2">
            {data.referred_users.map((r) => (
              <div key={`${r.display_name}-${r.city || 'nocity'}`} className="flex items-center justify-between text-sm">
                <span>{r.display_name} · {r.city || "—"}</span>
                {r.verified ? (
                  <span className="pill px-2 py-0.5 text-[10px] font-bold bg-primary text-primary-foreground">VERIFIED</span>
                ) : (
                  <span className="text-xs text-muted-foreground">{r.successful_trades} trades</span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export function InvitePage() {
  const { code } = useParams();
  const [inviter, setInviter] = useState(null);
  const [notFound, setNotFound] = useState(false);

  useEffect(() => {
    api.get(`/referrals/lookup/${code}`)
      .then((r) => setInviter(r.data))
      .catch(() => setNotFound(true));
    // stash in localStorage so signup can apply it
    localStorage.setItem("bg_referral_code", code);
  }, [code]);

  if (notFound) return (
    <div className="min-h-screen grid place-items-center p-6" data-testid="invite-invalid">
      <div className="text-center max-w-md">
        <h1 className="font-heading text-2xl font-bold mb-2">Invite link not found</h1>
        <p className="text-muted-foreground mb-6">This invite code isn't valid, but you're welcome to sign up anyway.</p>
        <Link to="/signup"><Button className="rounded-full">Sign up</Button></Link>
      </div>
    </div>
  );

  if (!inviter) return <div className="min-h-screen grid place-items-center"><div className="w-10 h-10 border-4 border-primary/30 border-t-primary rounded-full animate-spin" /></div>;

  return (
    <div className="min-h-screen mesh-bg" data-testid="invite-page">
      <div className="max-w-lg mx-auto px-6 py-16">
        <div className="rounded-3xl bg-card border border-border p-8 sm:p-10 text-center">
          <div className="w-20 h-20 rounded-full bg-accent grid place-items-center mx-auto mb-4 overflow-hidden">
            {inviter.picture ? <img src={inviter.picture} alt="" className="w-full h-full object-cover" /> : <Sparkle size={32} weight="duotone" className="text-primary" />}
          </div>
          <p className="text-sm font-bold uppercase tracking-[0.2em] text-primary mb-2">You've been invited</p>
          <h1 className="font-heading text-3xl font-bold mb-2">{inviter.display_name} invited you to BarterGrid.</h1>
          <p className="text-muted-foreground mb-4">Trade what you have for what you need — no price tags, just neighbors.</p>
          <div className="flex items-center justify-center gap-2 text-sm text-muted-foreground mb-8">
            <Star size={14} weight="fill" className="text-secondary" /> {(inviter.reputation_score || 0).toFixed(1)} · {inviter.successful_trades || 0} trades · {inviter.city || "Nearby"}
          </div>
          <div className="rounded-xl bg-accent/50 border border-border p-4 mb-6 text-sm">
            <p className="font-semibold mb-1">Referral bonus</p>
            <p className="text-muted-foreground">Complete your first trade and you both earn a Verified badge.</p>
          </div>
          <Link to="/signup"><Button className="rounded-full w-full h-12" data-testid="invite-accept">Accept invite & sign up</Button></Link>
          <p className="text-xs text-muted-foreground mt-4">Already have an account? <Link to="/login" className="text-primary font-medium">Sign in</Link></p>
        </div>
      </div>
    </div>
  );
}
