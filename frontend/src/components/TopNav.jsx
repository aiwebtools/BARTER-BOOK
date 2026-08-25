import { Link, NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import NotificationBell from "@/components/NotificationBell";
import { House, MagnifyingGlass, ListPlus, Handshake, ChatCircleText, User, SignOut, GridFour, ListChecks, ShieldWarning, EnvelopeSimple, Gear } from "@phosphor-icons/react";

const links = [
  { to: "/dashboard", label: "Home", icon: House },
  { to: "/discover", label: "Discover", icon: MagnifyingGlass },
  { to: "/listings", label: "Listings", icon: GridFour },
  { to: "/needs", label: "Needs", icon: ListChecks },
  { to: "/matches", label: "Matches", icon: Handshake },
  { to: "/messages", label: "Messages", icon: EnvelopeSimple },
  { to: "/trades", label: "Trades", icon: ChatCircleText },
];

export default function TopNav() {
  const { user, logout } = useAuth();
  const nav = useNavigate();

  return (
    <header className="sticky top-0 z-40 backdrop-blur-xl bg-background/80 border-b border-border/60" data-testid="top-nav">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between gap-4">
        <Link to="/dashboard" className="flex items-center gap-2" data-testid="nav-logo">
          <div className="w-9 h-9 rounded-xl bg-primary text-primary-foreground grid place-items-center font-heading font-bold">B</div>
          <span className="font-heading font-bold text-lg tracking-tight hidden sm:block">BarterGrid</span>
        </Link>

        <nav className="hidden md:flex items-center gap-1">
          {links.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              data-testid={`nav-${label.toLowerCase().replace(/ /g, "-")}`}
              className={({ isActive }) =>
                `flex items-center gap-2 px-3.5 py-2 rounded-full text-sm font-medium transition-colors ${
                  isActive ? "bg-accent text-accent-foreground" : "text-muted-foreground hover:text-foreground hover:bg-muted"
                }`
              }
            >
              <Icon size={18} weight="duotone" />
              <span>{label}</span>
            </NavLink>
          ))}
          {user?.role === "admin" && (
            <NavLink to="/admin" data-testid="nav-admin" className={({ isActive }) => `flex items-center gap-2 px-3.5 py-2 rounded-full text-sm font-medium transition-colors ${isActive ? "bg-secondary text-secondary-foreground" : "text-secondary hover:bg-secondary/10"}`}>
              <ShieldWarning size={18} weight="duotone" /> <span>Admin</span>
            </NavLink>
          )}
        </nav>

        <div className="flex items-center gap-1">
          <Button
            onClick={() => nav("/new")}
            className="rounded-full hidden sm:inline-flex"
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
          <NavLink key={to} to={to} className={({ isActive }) => `flex flex-col items-center gap-1 py-2 text-xs ${isActive ? "text-primary" : "text-muted-foreground"}`}>
            <Icon size={22} weight="duotone" />
            <span>{label}</span>
          </NavLink>
        ))}
      </div>
    </nav>
  );
}
