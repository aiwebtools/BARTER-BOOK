import { useState } from "react";
import { toast } from "sonner";
import { FacebookLogo, TwitterLogo, ChatText, Copy, ShareNetwork, CheckCircle, WhatsappLogo } from "@phosphor-icons/react";

/**
 * ShareButtons — one-tap share to Facebook, Twitter/X, SMS, WhatsApp + copy.
 * Uses the native Web Share API when available (iOS/Android/Chrome).
 */
export default function ShareButtons({ url, title, text, compact = false, testid = "share" }) {
  const [copied, setCopied] = useState(false);
  const shareUrl = url || (typeof window !== "undefined" ? window.location.href : "");
  const shareTitle = title || "Check this out on BarterGrid";
  const shareText = text || "Trade what you have for what you need — no price tags. Free local barter network.";
  const composed = `${shareText} ${shareUrl}`;

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(shareUrl);
      setCopied(true);
      toast.success("Link copied");
      setTimeout(() => setCopied(false), 1800);
    } catch { toast.error("Couldn't copy"); }
  };

  const nativeShare = async () => {
    if (navigator.share) {
      try { await navigator.share({ title: shareTitle, text: shareText, url: shareUrl }); }
      catch (e) {
        // AbortError is fired when the user cancels — that's fine.
        if (e?.name !== "AbortError") console.warn("[share] native share failed", e?.message || e);
      }
    } else { copy(); }
  };

  const buttons = [
    { label: "Facebook", icon: FacebookLogo, href: `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(shareUrl)}`, cls: "hover:bg-[#1877f2]/15 hover:text-[#1877f2]", tid: "share-fb" },
    { label: "Twitter", icon: TwitterLogo, href: `https://twitter.com/intent/tweet?text=${encodeURIComponent(shareText)}&url=${encodeURIComponent(shareUrl)}`, cls: "hover:bg-foreground/10 hover:text-foreground", tid: "share-tw" },
    { label: "SMS", icon: ChatText, href: `sms:?&body=${encodeURIComponent(composed)}`, cls: "hover:bg-primary/15 hover:text-primary", tid: "share-sms" },
    { label: "WhatsApp", icon: WhatsappLogo, href: `https://wa.me/?text=${encodeURIComponent(composed)}`, cls: "hover:bg-[#25d366]/15 hover:text-[#25d366]", tid: "share-wa" },
  ];

  return (
    <div className={`flex flex-wrap items-center gap-2 ${compact ? "text-sm" : ""}`} data-testid={testid}>
      <span className="text-xs font-bold uppercase tracking-widest text-muted-foreground mr-1 flex items-center gap-1"><ShareNetwork size={14} weight="duotone" /> Share</span>
      {buttons.map((b) => (
        <a
          key={b.label}
          href={b.href}
          target={b.href.startsWith("sms:") ? "_self" : "_blank"}
          rel="noreferrer noopener"
          className={`pill p-2 border border-border transition-colors ${b.cls}`}
          aria-label={`Share on ${b.label}`}
          data-testid={b.tid}
        >
          <b.icon size={18} weight="duotone" />
        </a>
      ))}
      <button onClick={copy} className="pill p-2 border border-border hover:bg-muted transition-colors" aria-label="Copy link" data-testid={`${testid}-copy`}>
        {copied ? <CheckCircle size={18} weight="fill" className="text-primary" /> : <Copy size={18} weight="duotone" />}
      </button>
      {typeof navigator !== "undefined" && navigator.share && (
        <button onClick={nativeShare} className="pill p-2 border border-border hover:bg-muted transition-colors" aria-label="More share options" data-testid={`${testid}-native`}>
          <ShareNetwork size={18} weight="duotone" />
        </button>
      )}
    </div>
  );
}
