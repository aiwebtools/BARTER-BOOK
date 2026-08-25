import { Link, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Handshake, MapPinLine, ShieldCheck, ArrowsClockwise, Users, Star, GitBranch, Question, Package, Wrench, Leaf } from "@phosphor-icons/react";

const examples = [
  { a: "Water Filter", b: "Bike Lock" },
  { a: "Hand Saw", b: "Camping Stove" },
  { a: "Computer Help", b: "Garden Tools" },
  { a: "Firewood", b: "Power Drill" },
];

const faqs = [
  { q: "Do I need money to use BarterGrid?", a: "No. BarterGrid is a barter network. You trade what you have for what you need — no price tags required." },
  { q: "How does matching work?", a: "Post what you have and what you need. We surface nearby people whose have/need pairs line up with yours." },
  { q: "How do I stay safe?", a: "Meet in public locations, keep chat inside the app, verify listings, and report anything suspicious. See our Safety Center." },
  { q: "Can I trade services?", a: "Yes — post 'I CAN DO' listings for skills like tutoring, repair, or gardening." },
  { q: "What items are prohibited?", a: "Weapons, illegal goods, stolen property, and fraudulent items. See Community Rules." },
];

export default function Landing() {
  const nav = useNavigate();
  return (
    <div className="min-h-screen" data-testid="landing-page">
      {/* Nav */}
      <header className="sticky top-0 z-40 backdrop-blur-xl bg-background/80 border-b border-border/50">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2">
            <div className="w-9 h-9 rounded-xl bg-primary text-primary-foreground grid place-items-center font-heading font-bold">B</div>
            <span className="font-heading font-bold text-xl tracking-tight">BarterGrid</span>
          </Link>
          <div className="flex items-center gap-2">
            <Button variant="ghost" onClick={() => nav("/login")} className="rounded-full" data-testid="landing-signin">Sign in</Button>
            <Button onClick={() => nav("/signup")} className="rounded-full" data-testid="landing-start">Start Trading</Button>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 mesh-bg" />
        <div className="absolute inset-0 dot-grid opacity-40" />
        <div className="relative max-w-7xl mx-auto px-6 py-24 lg:py-32 grid lg:grid-cols-2 gap-16 items-center">
          <div className="space-y-8">
            <span className="inline-flex items-center gap-2 pill px-4 py-1.5 bg-card border border-border text-xs font-semibold tracking-widest uppercase">
              <span className="w-2 h-2 rounded-full bg-primary pulse-connect" /> Local exchange, real people
            </span>
            <h1 className="font-heading text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight leading-[1.05]">
              Trade what you have<br />for what you <span className="text-primary">need.</span>
            </h1>
            <p className="text-lg text-muted-foreground max-w-xl leading-relaxed">
              BarterGrid connects neighbors who want to exchange goods, skills, and resources — without price tags.
              The things you need may already exist in your community.
            </p>
            <div className="flex flex-wrap gap-3">
              <Button size="lg" className="rounded-full h-12 px-8" onClick={() => nav("/signup")} data-testid="hero-cta">
                Start Trading — it's free
              </Button>
              <Button size="lg" variant="outline" className="rounded-full h-12 px-8" onClick={() => nav("/discover")} data-testid="hero-explore">
                Explore Nearby
              </Button>
            </div>
          </div>

          {/* Visual: connected nodes */}
          <div className="relative">
            <div className="rounded-3xl bg-card border border-border p-8 shadow-xl">
              <div className="grid grid-cols-3 gap-4 items-center">
                <NodeCard kind="have" title="Water Filter" name="Maya" />
                <div className="flex flex-col items-center gap-2">
                  <ArrowsClockwise size={44} weight="duotone" className="text-primary pulse-connect" />
                  <span className="text-xs font-semibold uppercase tracking-widest text-primary">Match</span>
                </div>
                <NodeCard kind="need" title="Bike Lock" name="Jordan" />
              </div>
              <div className="mt-8 pt-6 border-t border-border grid grid-cols-2 gap-4">
                <StatMini icon={Users} n="3,200+" label="Traders" />
                <StatMini icon={Handshake} n="8,900+" label="Trades" />
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="max-w-7xl mx-auto px-6 py-24">
        <div className="text-center mb-16">
          <p className="text-sm font-bold uppercase tracking-[0.2em] text-primary mb-3">How it works</p>
          <h2 className="font-heading text-3xl sm:text-4xl font-bold">The barter loop, made simple.</h2>
        </div>
        <div className="grid md:grid-cols-4 gap-6">
          {[
            { icon: Package, title: "Post what you have", desc: "Items sitting around? Skills to offer? List them in seconds." },
            { icon: Leaf, title: "Add what you need", desc: "Keep a running Needs list. We'll ping you when something matches." },
            { icon: Handshake, title: "Find local matches", desc: "See potential trades within your chosen radius." },
            { icon: MapPinLine, title: "Meet safely", desc: "Chat, pick a public meetup, complete the trade, build reputation." },
          ].map((s, i) => (
            <div key={i} className="rounded-2xl border border-border p-6 bg-card card-hover">
              <div className="w-12 h-12 rounded-xl bg-accent grid place-items-center mb-4">
                <s.icon size={26} weight="duotone" className="text-primary" />
              </div>
              <div className="text-xs font-bold uppercase tracking-[0.2em] text-muted-foreground mb-1">Step {i + 1}</div>
              <h3 className="font-heading font-semibold text-lg mb-2">{s.title}</h3>
              <p className="text-sm text-muted-foreground leading-relaxed">{s.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Example trades */}
      <section className="bg-accent/40 py-24 border-y border-border">
        <div className="max-w-7xl mx-auto px-6">
          <div className="mb-12">
            <p className="text-sm font-bold uppercase tracking-[0.2em] text-primary mb-3">Example trades</p>
            <h2 className="font-heading text-3xl sm:text-4xl font-bold">Real exchanges. No price tags.</h2>
          </div>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {examples.map((e, i) => (
              <div key={i} className="rounded-2xl bg-card border border-border p-6 flex flex-col gap-3">
                <div className="flex items-center gap-2 text-sm">
                  <span className="pill px-3 py-1 text-xs font-semibold bg-accent text-accent-foreground">HAVE</span>
                  <span className="font-medium">{e.a}</span>
                </div>
                <ArrowsClockwise size={20} weight="duotone" className="text-primary mx-auto" />
                <div className="flex items-center gap-2 text-sm">
                  <span className="pill px-3 py-1 text-xs font-semibold bg-secondary text-secondary-foreground">NEED</span>
                  <span className="font-medium">{e.b}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Trust */}
      <section className="max-w-7xl mx-auto px-6 py-24 grid md:grid-cols-3 gap-6">
        {[
          { icon: ShieldCheck, title: "Safe Meetups", desc: "Meet at public libraries, community centers, or police exchange zones. Never share your home address." },
          { icon: Star, title: "Real Reputation", desc: "Every completed trade builds trust. Ratings, verification badges, and trade counts — all visible." },
          { icon: GitBranch, title: "Trade Chains", desc: "When A→B→C→A adds up, we surface multi-party trades. Coordination made simple." },
        ].map((f, i) => (
          <div key={i} className="rounded-2xl border border-border p-8 bg-card card-hover">
            <f.icon size={36} weight="duotone" className="text-primary mb-4" />
            <h3 className="font-heading font-semibold text-xl mb-2">{f.title}</h3>
            <p className="text-sm text-muted-foreground leading-relaxed">{f.desc}</p>
          </div>
        ))}
      </section>

      {/* FAQ */}
      <section className="bg-muted/50 border-y border-border">
        <div className="max-w-4xl mx-auto px-6 py-20">
          <div className="flex items-center gap-3 mb-10">
            <Question size={32} weight="duotone" className="text-primary" />
            <h2 className="font-heading text-3xl sm:text-4xl font-bold">Frequently asked</h2>
          </div>
          <div className="space-y-3">
            {faqs.map((f, i) => (
              <details key={i} className="group bg-card border border-border rounded-2xl px-6 py-4">
                <summary className="cursor-pointer font-heading font-semibold flex items-center justify-between">
                  {f.q}
                  <span className="text-muted-foreground group-open:rotate-45 transition-transform">＋</span>
                </summary>
                <p className="mt-3 text-sm text-muted-foreground leading-relaxed">{f.a}</p>
              </details>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="max-w-5xl mx-auto px-6 py-24 text-center">
        <h2 className="font-heading text-3xl sm:text-5xl font-bold mb-6">Your community has what you need.</h2>
        <p className="text-lg text-muted-foreground mb-8 max-w-2xl mx-auto">Join BarterGrid and start trading with neighbors today.</p>
        <Button size="lg" className="rounded-full h-14 px-10 text-base" onClick={() => nav("/signup")} data-testid="footer-cta">
          Create your free account
        </Button>
      </section>

      {/* Footer */}
      <footer className="border-t border-border py-10 px-6">
        <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-4 text-sm text-muted-foreground">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-primary text-primary-foreground grid place-items-center font-heading font-bold text-sm">B</div>
            <span className="font-heading font-semibold text-foreground">BarterGrid</span>
            <span>· Local exchange. Real people.</span>
          </div>
          <div className="flex gap-4">
            <Link to="/safety" className="hover:text-foreground">Safety</Link>
            <Link to="/login" className="hover:text-foreground">Sign in</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}

function NodeCard({ kind, title, name }) {
  const cls = kind === "have" ? "bg-accent text-accent-foreground" : "bg-secondary text-secondary-foreground";
  return (
    <div className="rounded-2xl bg-background border border-border p-4 text-center">
      <span className={`pill px-2 py-0.5 text-[10px] font-bold tracking-widest ${cls}`}>{kind === "have" ? "HAVE" : "NEED"}</span>
      <div className="mt-3 font-heading font-semibold">{title}</div>
      <div className="text-xs text-muted-foreground mt-1">{name}</div>
    </div>
  );
}

function StatMini({ icon: Icon, n, label }) {
  return (
    <div className="flex items-center gap-3">
      <div className="w-10 h-10 rounded-xl bg-accent grid place-items-center">
        <Icon size={20} weight="duotone" className="text-primary" />
      </div>
      <div>
        <div className="font-heading font-bold text-lg leading-none">{n}</div>
        <div className="text-xs text-muted-foreground">{label}</div>
      </div>
    </div>
  );
}
