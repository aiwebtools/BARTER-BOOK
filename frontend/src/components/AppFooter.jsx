import { Sparkle } from "@phosphor-icons/react";

const AI_TOOLS_URL = "https://aiwebtools.app";

/** Shared app footer with aiwebtools.app branding + AI Tools directory link. */
export default function AppFooter() {
  return (
    <footer className="mt-16 border-t border-border" data-testid="app-footer">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-10 grid md:grid-cols-3 gap-8">
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-primary text-primary-foreground grid place-items-center font-heading font-bold text-sm">B</div>
            <span className="font-heading font-semibold">BarterGrid</span>
          </div>
          <p className="text-sm text-muted-foreground leading-relaxed">
            A free bartering service for the people, by the people. Trade goods, skills and resources with your neighbors — no fees, no prices, no middleman.
          </p>
        </div>

        <div className="space-y-2 text-sm">
          <div className="text-xs font-bold uppercase tracking-widest text-muted-foreground mb-2">Product</div>
          <a href="/discover" className="block text-muted-foreground hover:text-foreground">Discover listings</a>
          <a href="/safety" className="block text-muted-foreground hover:text-foreground">Safety center</a>
          <a href="/settings" className="block text-muted-foreground hover:text-foreground">Settings</a>
          <a href="/profile" className="block text-muted-foreground hover:text-foreground">Your storefront</a>
        </div>

        <div className="rounded-2xl bg-secondary/10 border border-secondary/40 p-5" data-testid="ai-tools-footer">
          <div className="flex items-center gap-2 mb-2">
            <Sparkle size={18} weight="fill" className="text-secondary" />
            <span className="text-xs font-bold uppercase tracking-widest text-secondary">Bonus for members</span>
          </div>
          <div className="font-heading font-semibold mb-1">FREE AI TOOLS</div>
          <p className="text-xs text-muted-foreground mb-3">A curated directory of creative AI tools you can use for free — same team that built BarterGrid.</p>
          <a href={AI_TOOLS_URL} target="_blank" rel="noreferrer" className="pill inline-flex items-center gap-1.5 px-4 py-2 text-xs font-bold bg-secondary text-secondary-foreground hover:opacity-90 transition-opacity" data-testid="ai-tools-footer-btn">
            Open aiwebtools.app →
          </a>
        </div>
      </div>
      <div className="border-t border-border py-5 px-4 sm:px-6">
        <p className="text-xs text-center text-muted-foreground">
          Made with <span className="text-secondary">♥</span> by <a href={AI_TOOLS_URL} target="_blank" rel="noreferrer" className="text-primary font-semibold">aiwebtools.app</a> — a free bartering service for the people, by the people.
        </p>
      </div>
    </footer>
  );
}
