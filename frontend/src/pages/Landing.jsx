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
  { q: "What is this exactly?", a: "BarterGrid is a bulletin board for trading without money. You list what you have, list what you need, and it connects you with a neighbor who has the opposite." },
  { q: "Do I need money to use it?", a: "No. There are no fees, no premium tier, no ads, no price tags. Two people agree on a swap and meet up." },
  { q: "Why does this exist?", a: "Because supply chains, banks, and prices can all fail — sometimes for a week, sometimes longer. If that ever happens, communities that already know how to trade will be fine. This is a tool for that, whether you use it every day or you're just keeping it in your back pocket." },
  { q: "How does matching work?", a: "You mark items as HAVE, NEED, or CAN DO. We surface people whose HAVE lines up with your NEED and vice versa. Nothing fancy — clear labels and real distances." },
  { q: "Is it only for emergencies?", a: "No. Everyday use is the point. Tools, seeds, rides, tutoring, meal help, an extra deep-freeze — anything you'd normally sell, gift, or buy." },
  { q: "How do I stay safe?", a: "Meet in public. Never share your home address. Read the Safety Center. BarterGrid can't guarantee any exchange — it just makes it easier to find one." },
  { q: "Can I trade services?", a: "Yes. Skills count. Post 'I CAN DO' listings for things like repair, tutoring, moving help, gardening, or cooking." },
  { q: "What items aren't allowed?", a: "No weapons, illegal drugs, stolen goods, or counterfeits. See Community Rules." },
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
              <span className="w-2 h-2 rounded-full bg-primary pulse-connect" /> Free · No fees · No ads
            </span>
            <h1 className="font-heading text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight leading-[1.05]">
              A place to <span className="text-primary">trade</span><br />without money.
            </h1>
            <p className="text-lg text-muted-foreground max-w-xl leading-relaxed">
              BarterGrid is a simple tool for swapping goods, skills and help with your neighbors. Post what you have. Post what you need. Meet up. Trade.
            </p>
            <p className="text-base text-muted-foreground max-w-xl leading-relaxed">
              Money and supply chains don't always work. We may have to go back to bartering one day — maybe for a week, maybe longer. This app is here for that day, and for every ordinary day in between.
            </p>
            <div className="flex flex-wrap gap-3">
              <Button size="lg" className="rounded-full h-12 px-8 shine" onClick={() => nav("/signup")} data-testid="hero-cta">
                Create a free account
              </Button>
              <Button size="lg" variant="outline" className="rounded-full h-12 px-8" onClick={() => nav("/discover")} data-testid="hero-explore">
                Browse listings
              </Button>
            </div>
            <p className="text-xs text-muted-foreground">Nothing to buy. No credit card. No hidden tier.</p>
          </div>

          {/* Visual: photo + connected nodes */}
          <div className="relative">
            <div className="absolute -inset-6 rounded-[2rem] bg-primary/10 blur-2xl" aria-hidden />
            <div className="relative rounded-3xl bg-card border border-border overflow-hidden shadow-xl">
              <img
                src="https://images.unsplash.com/photo-1604881988758-f76ad2f7aac1?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjAzMjh8MHwxfHNlYXJjaHwxfHxkaXZlcnNlJTIwY29tbXVuaXR5JTIwcGVvcGxlJTIwY2hhdHRpbmclMjBjb2ZmZWV8ZW58MHx8fHwxNzg3Njg1NTM3fDA&ixlib=rb-4.1.0&q=85"
                alt="Neighbors exchanging goods"
                className="w-full h-72 object-cover"
                loading="eager"
              />
              <div className="p-6">
                <div className="grid grid-cols-3 gap-3 items-center">
                  <NodeCard kind="have" title="Water Filter" name="You" />
                  <div className="flex flex-col items-center gap-1">
                    <ArrowsClockwise size={36} weight="duotone" className="text-primary pulse-connect" />
                    <span className="text-[10px] font-semibold uppercase tracking-widest text-primary">Match</span>
                  </div>
                  <NodeCard kind="need" title="Bike Lock" name="Neighbor" />
                </div>
                <div className="mt-6 pt-4 border-t border-border grid grid-cols-2 gap-4">
                  <StatMini icon={Users} n="Free" label="Always. No fees, no ads." />
                  <StatMini icon={Handshake} n="Local" label="Trade in your radius." />
                </div>
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
          { icon: ShieldCheck, title: "Meet somewhere public", desc: "The app suggests libraries, community centers, and public parking. Never share your home address." },
          { icon: Star, title: "Reputation is earned", desc: "Ratings and completed-trade counts show up next to a name. Nothing fake, no filters." },
          { icon: GitBranch, title: "Three-way trades", desc: "A→B→C→A works too. When two people don't have exactly what each other needs, sometimes a third person closes the loop." },
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
        <h2 className="font-heading text-3xl sm:text-5xl font-bold mb-6">Try it once. Keep it forever.</h2>
        <p className="text-lg text-muted-foreground mb-8 max-w-2xl mx-auto">Make an account, post one thing you'd swap, and see who's around. That's it.</p>
        <Button size="lg" className="rounded-full h-14 px-10 text-base" onClick={() => nav("/signup")} data-testid="footer-cta">
          Create your free account
        </Button>
      </section>

      {/* Footer */}
      <footer className="border-t border-border py-10 px-6">
        <div className="max-w-7xl mx-auto grid md:grid-cols-3 gap-8 pb-8">
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-primary text-primary-foreground grid place-items-center font-heading font-bold text-sm">B</div>
              <span className="font-heading font-semibold">BarterGrid</span>
            </div>
            <p className="text-sm text-muted-foreground max-w-xs">A free bartering service for the people, by the people. Local exchange, real neighbors, no price tags.</p>
          </div>
          <div className="text-sm space-y-2">
            <div className="text-xs font-bold uppercase tracking-widest text-muted-foreground mb-2">Explore</div>
            <Link to="/safety" className="block text-muted-foreground hover:text-foreground">Safety center</Link>
            <Link to="/login" className="block text-muted-foreground hover:text-foreground">Sign in</Link>
            <Link to="/signup" className="block text-muted-foreground hover:text-foreground">Create free account</Link>
          </div>
          <div className="rounded-2xl bg-secondary/10 border border-secondary/40 p-5">
            <div className="text-xs font-bold uppercase tracking-widest text-secondary mb-2">Bonus for members</div>
            <div className="font-heading font-semibold mb-1">FREE AI TOOLS</div>
            <p className="text-xs text-muted-foreground mb-3">A curated directory of creative AI tools — from the same team.</p>
            <a href="https://aiwebtools.app" target="_blank" rel="noreferrer" className="pill inline-flex items-center gap-1.5 px-4 py-2 text-xs font-bold bg-secondary text-secondary-foreground hover:opacity-90 transition-opacity" data-testid="landing-ai-tools">
              Open aiwebtools.app →
            </a>
          </div>
        </div>
        <div className="max-w-7xl mx-auto pt-6 border-t border-border text-center text-xs text-muted-foreground">
          Made with <span className="text-secondary">♥</span> by <a href="https://aiwebtools.app" target="_blank" rel="noreferrer" className="text-primary font-semibold">aiwebtools.app</a> — a free bartering service for the people, by the people.
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
