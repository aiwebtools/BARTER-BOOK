import { Link, NavLink, useNavigate } from "react-router-dom";
import { useState } from "react";
import { useAuth } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import NotificationBell from "@/components/NotificationBell";
import { House, MagnifyingGlass, ListPlus, Handshake, ChatCircleText, User, SignOut, GridFour, ListChecks, ShieldWarning, EnvelopeSimple, Gear, List, X, Sparkle, ShieldCheck, Users } from "@phosphor-icons/react";

const AI_TOOLS_URL = "https://aiwebtools.app";

const links = [
  { to: "/dashboard", label: "Home", icon: House },
  { to: "/discover", label: "Discover", icon: MagnifyingGlass },
  { to: "/listings", label: "Listings", icon: GridFour },
  { to: "/needs", label: "Needs", icon: ListChecks },
  { to: "/matches", label: "Matches", icon: Handshake },
  { to: "/community", label: "Community", icon: Users },
  { to: "/messages", label: "Messages", icon: EnvelopeSimple },
  { to: "/trades", label: "Trades", icon: ChatCircleText },
];

export default function TopNav() {
  const { user, logout } = useAuth();
  const nav = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <header className="sticky top-0 z-40 backdrop-blur-xl bg-background/85 border-b border-border/60" data-testid="top-nav">
      <div className="max-w-7xl mx-auto px-3 sm:px-6 h-16 flex items-center justify-between gap-2">
        {/* Left: hamburger (mobile) + logo */}
        <div className="flex items-center gap-2 min-w-0">
          <button
            onClick={() => setMenuOpen(true)}
            className="md:hidden p-2 -ml-1 rounded-full hover:bg-muted transition-colors"
            data-testid="hamburger-btn"
            aria-label="Open menu"
          >
            <List size={24} weight="bold" />
          </button>
          <Link to="/dashboard" className="flex items-center gap-2 min-w-0" data-testid="nav-logo">
            <div className="w-9 h-9 rounded-xl bg-primary text-primary-foreground grid place-items-center font-heading font-bold shrink-0">B</div>
            <span className="font-heading font-bold text-lg tracking-tight hidden sm:block truncate">BarterGrid</span>
          </Link>
        </div>

        {/* Center: desktop nav */}
        <nav className="hidden md:flex items-center gap-1">
          {links.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              data-testid={`nav-${label.toLowerCase().replace(/ /g, "-")}`}
              className={({ isActive }) =>
                `flex items-center gap-1.5 px-3 py-2 rounded-full text-sm font-medium transition-colors ${
                  isActive ? "bg-accent text-accent-foreground" : "text-muted-foreground hover:text-foreground hover:bg-muted"
                }`
              }
            >
              <Icon size={17} weight="duotone" />
              <span>{label}</span>
            </NavLink>
          ))}
          {user?.role === "admin" && (
            <NavLink to="/admin" data-testid="nav-admin" className={({ isActive }) => `flex items-center gap-1.5 px-3 py-2 rounded-full text-sm font-medium transition-colors ${isActive ? "bg-secondary text-secondary-foreground" : "text-secondary hover:bg-secondary/10"}`}>
              <ShieldWarning size={17} weight="duotone" /> <span>Admin</span>
            </NavLink>
          )}
        </nav>

        {/* Right: actions */}
        <div className="flex items-center gap-1">
          <a href={AI_TOOLS_URL} target="_blank" rel="noreferrer" className="hidden lg:inline-flex pill px-3.5 py-2 text-xs font-semibold bg-secondary/15 text-secondary border border-secondary/40 hover:bg-secondary hover:text-secondary-foreground transition-colors items-center gap-1.5" data-testid="ai-tools-header">
            <Sparkle size={14} weight="fill" /> FREE AI TOOLS
          </a>
          <Button
            onClick={() => nav("/new")}
            className="rounded-full hidden sm:inline-flex shine"
            data-testid="post-listing-btn"
          >
            <ListPlus size={18} weight="bold" className="mr-1" /> Post
          </Button>
          <NotificationBell />
          <Link to="/profile" className="w-10 h-10 rounded-full bg-muted grid place-items-center hover:bg-accent transition-colors overflow-hidden" data-testid="nav-profile">
            {user?.picture ? (
              <img src={user.picture} alt="" className="w-10 h-10 rounded-full object-cover" />
            ) : (
              <User size={20} weight="duotone" />
            )}
          </Link>
          <Link to="/settings" className="p-2 rounded-full hover:bg-muted transition-colors hidden sm:inline-flex" data-testid="nav-settings" aria-label="Settings">
            <Gear size={20} weight="duotone" />
          </Link>
          <button onClick={logout} className="p-2 rounded-full hover:bg-muted transition-colors hidden sm:inline-flex" data-testid="logout-btn" aria-label="Logout">
            <SignOut size={20} />
          </button>
        </div>
      </div>

      {/* Mobile hamburger drawer */}
      {menuOpen && (
        <>
          <div className="md:hidden fixed inset-0 z-50 bg-black/60" onClick={() => setMenuOpen(false)} />
          <aside className="md:hidden fixed top-0 left-0 bottom-0 z-50 w-[85vw] max-w-sm bg-background border-r border-border shadow-2xl flex flex-col" data-testid="mobile-menu">
            <div className="flex items-center justify-between px-5 h-16 border-b border-border">
              <Link to="/dashboard" onClick={() => setMenuOpen(false)} className="flex items-center gap-2">
                <div className="w-9 h-9 rounded-xl bg-primary text-primary-foreground grid place-items-center font-heading font-bold">B</div>
                <span className="font-heading font-bold text-lg">BarterGrid</span>
              </Link>
              <button onClick={() => setMenuOpen(false)} className="p-2 rounded-full hover:bg-muted" data-testid="close-menu"><X size={22} /></button>
            </div>

            {user && (
              <div className="px-5 py-4 border-b border-border">
                <div className="flex items-center gap-3">
                  <div className="w-11 h-11 rounded-full bg-muted grid place-items-center overflow-hidden">
                    {user.picture ? <img src={user.picture} alt="" className="w-11 h-11 object-cover" /> : <User size={22} weight="duotone" />}
                  </div>
                  <div className="min-w-0">
                    <div className="font-heading font-semibold truncate">{user.first_name || user.display_name}</div>
                    <div className="text-xs text-muted-foreground truncate">@{user.username || "trader"}</div>
                  </div>
                </div>
              </div>
            )}

            <nav className="flex-1 overflow-y-auto py-3">
              {links.map(({ to, label, icon: Icon }) => (
                <NavLink
                  key={to}
                  to={to}
                  onClick={() => setMenuOpen(false)}
                  data-testid={`mobile-nav-${label.toLowerCase()}`}
                  className={({ isActive }) => `flex items-center gap-3 px-5 py-3 text-base font-medium transition-colors ${isActive ? "bg-accent text-accent-foreground" : "hover:bg-muted"}`}
                >
                  <Icon size={22} weight="duotone" />
                  <span>{label}</span>
                </NavLink>
              ))}
              <NavLink to="/profile" onClick={() => setMenuOpen(false)} className={({ isActive }) => `flex items-center gap-3 px-5 py-3 text-base font-medium ${isActive ? "bg-accent text-accent-foreground" : "hover:bg-muted"}`} data-testid="mobile-nav-profile"><User size={22} weight="duotone" /> <span>My Profile</span></NavLink>
              <NavLink to="/settings" onClick={() => setMenuOpen(false)} className={({ isActive }) => `flex items-center gap-3 px-5 py-3 text-base font-medium ${isActive ? "bg-accent text-accent-foreground" : "hover:bg-muted"}`} data-testid="mobile-nav-settings"><Gear size={22} weight="duotone" /> <span>Settings</span></NavLink>
              <NavLink to="/safety" onClick={() => setMenuOpen(false)} className={({ isActive }) => `flex items-center gap-3 px-5 py-3 text-base font-medium ${isActive ? "bg-accent text-accent-foreground" : "hover:bg-muted"}`}><ShieldCheck size={22} weight="duotone" /> <span>Safety Center</span></NavLink>
              {user?.role === "admin" && (
                <NavLink to="/admin" onClick={() => setMenuOpen(false)} className="flex items-center gap-3 px-5 py-3 text-base font-medium text-secondary hover:bg-secondary/10"><ShieldWarning size={22} weight="duotone" /> <span>Admin</span></NavLink>
              )}

              <div className="mt-3 mx-4 rounded-2xl bg-secondary/10 border border-secondary/40 p-4" data-testid="ai-tools-mobile-panel">
                <div className="flex items-center gap-2 mb-2">
                  <Sparkle size={18} weight="fill" className="text-secondary" />
                  <span className="text-xs font-bold uppercase tracking-widest text-secondary">Bonus</span>
                </div>
                <div className="font-heading font-semibold mb-1">FREE AI TOOLS</div>
                <p className="text-xs text-muted-foreground mb-3">A curated directory of creative AI tools you can use free. Made by the same team.</p>
                <a href={AI_TOOLS_URL} target="_blank" rel="noreferrer" onClick={() => setMenuOpen(false)} className="pill inline-flex items-center gap-1 px-4 py-2 text-xs font-bold bg-secondary text-secondary-foreground w-full justify-center" data-testid="ai-tools-mobile-btn">
                  Open aiwebtools.app →
                </a>
              </div>
            </nav>

            <div className="border-t border-border p-4 space-y-2">
              <button onClick={() => { setMenuOpen(false); logout(); }} className="w-full flex items-center gap-2 px-4 py-3 rounded-xl hover:bg-muted text-sm font-medium" data-testid="mobile-logout">
                <SignOut size={18} /> Log out
              </button>
              <p className="text-[11px] text-center text-muted-foreground pt-2">
                Made with <span className="text-secondary">♥</span> by <a href={AI_TOOLS_URL} target="_blank" rel="noreferrer" className="text-primary font-medium">aiwebtools.app</a> — a free bartering service for the people, by the people.
              </p>
            </div>
          </aside>
        </>
      )}
    </header>
  );
}

export function BottomNav() {
  return (
    <nav className="md:hidden fixed bottom-0 inset-x-0 z-40 border-t border-border bg-background/95 backdrop-blur-xl" data-testid="bottom-nav">
      <div className="grid grid-cols-5 max-w-lg mx-auto">
        {[
          { to: "/dashboard", label: "Home", icon: House },
          { to: "/discover", label: "Discover", icon: MagnifyingGlass },
          { to: "/new", label: "Post", icon: ListPlus },
          { to: "/messages", label: "Chat", icon: EnvelopeSimple },
          { to: "/trades", label: "Trades", icon: ChatCircleText },
        ].map(({ to, label, icon: Icon }) => (
          <NavLink key={to} to={to} className={({ isActive }) => `flex flex-col items-center gap-1 py-2 text-[11px] ${isActive ? "text-primary" : "text-muted-foreground"}`}>
            <Icon size={22} weight="duotone" />
            <span>{label}</span>
          </NavLink>
        ))}
      </div>
    </nav>
  );
}
