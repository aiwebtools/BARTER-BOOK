import { Link } from "react-router-dom";
import { ShieldCheck, MapPin, ChatCircleText, Eye, HandFist, Warning } from "@phosphor-icons/react";

const tips = [
  { icon: MapPin, title: "Meet in public locations", desc: "Libraries, community centers, or police exchange zones are safest. Never invite strangers to your home." },
  { icon: Eye, title: "Inspect items before completing", desc: "Take a moment to verify the item matches the listing before confirming completion." },
  { icon: ChatCircleText, title: "Keep chat inside the app", desc: "Don't share phone numbers or personal info until you're comfortable. In-app messaging keeps trade context." },
  { icon: HandFist, title: "Trust your instincts", desc: "If a meetup or listing feels off, cancel it. You are never obligated to complete a trade." },
  { icon: Warning, title: "Report suspicious behavior", desc: "Every listing and profile has a Report button. Help keep the community safe." },
  { icon: ShieldCheck, title: "Prohibited items", desc: "No weapons, illegal drugs, stolen property, or fraudulent goods. Violations lead to removal and bans." },
];

export default function Safety() {
  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 py-8 pb-24 md:pb-8" data-testid="safety-page">
      <p className="text-sm font-bold uppercase tracking-[0.2em] text-primary mb-1">Safety Center</p>
      <h1 className="font-heading text-3xl sm:text-4xl font-bold mb-2">Trade safely, every time.</h1>
      <p className="text-muted-foreground mb-8">BarterGrid facilitates connections between people — it doesn't guarantee outcomes. These practical steps help protect everyone.</p>

      <div className="grid sm:grid-cols-2 gap-4 mb-10">
        {tips.map((t) => (
          <div key={t.title} className="rounded-2xl bg-card border border-border p-6">
            <t.icon size={28} weight="duotone" className="text-primary mb-3" />
            <h3 className="font-heading font-semibold mb-2">{t.title}</h3>
            <p className="text-sm text-muted-foreground leading-relaxed">{t.desc}</p>
          </div>
        ))}
      </div>

      <div className="rounded-2xl bg-secondary/10 border border-secondary/30 p-6">
        <h3 className="font-heading font-semibold text-lg mb-2 flex items-center gap-2"><Warning size={22} weight="duotone" className="text-secondary" /> Emergency</h3>
        <p className="text-sm text-muted-foreground">If you are in danger, contact your local emergency services immediately. BarterGrid cannot replace emergency response.</p>
      </div>

      <div className="mt-8 text-sm text-muted-foreground">
        <Link to="/dashboard" className="text-primary font-medium">← Back to your dashboard</Link>
      </div>
    </div>
  );
}
