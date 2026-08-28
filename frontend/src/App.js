import "@/App.css";
import { BrowserRouter, Routes, Route, useLocation, Navigate } from "react-router-dom";
import { Toaster } from "sonner";
import { AuthProvider, useAuth } from "@/lib/auth";
import AppLayout from "@/components/AppLayout";
import TopNav, { BottomNav } from "@/components/TopNav";
import AppFooter from "@/components/AppFooter";
import Landing from "@/pages/Landing";
import Login from "@/pages/Login";
import AuthCallback from "@/pages/AuthCallback";
import Onboarding from "@/pages/Onboarding";
import Dashboard from "@/pages/Dashboard";
import Discover from "@/pages/Discover";
import NewListing from "@/pages/NewListing";
import { MyListings, ListingDetail } from "@/pages/Listings";
import Matches from "@/pages/Matches";
import { TradesList, TradeDetail } from "@/pages/Trades";
import Profile from "@/pages/Profile";
import PublicProfile from "@/pages/PublicProfile";
import Safety from "@/pages/Safety";
import Needs from "@/pages/Needs";
import Community from "@/pages/Community";
import Admin from "@/pages/Admin";
import Settings from "@/pages/Settings";
import { InvitePage } from "@/pages/Referral";
import { MessagesList, MessageThread } from "@/pages/Messages";

function Router() {
  const location = useLocation();
  if (location.hash?.includes("session_id=")) return <AuthCallback />;

  return (
    <Routes>
      <Route path="/" element={<LandingOrRedirect />} />
      <Route path="/login" element={<Login mode="login" />} />
      <Route path="/signup" element={<Login mode="signup" />} />
      <Route path="/onboarding" element={<Onboarding />} />
      <Route path="/invite/:code" element={<InvitePage />} />
      <Route path="/u/:id" element={<PublicProfile />} />
      <Route path="/discover" element={<GuestOrAppShell><Discover /></GuestOrAppShell>} />
      <Route path="/community" element={<GuestOrAppShell><Community /></GuestOrAppShell>} />
      <Route element={<AppLayout />}>
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/new" element={<NewListing />} />
        <Route path="/listings" element={<MyListings />} />
        <Route path="/listings/view/:id" element={<ListingDetail />} />
        <Route path="/needs" element={<Needs />} />
        <Route path="/matches" element={<Matches />} />
        <Route path="/trades" element={<TradesList />} />
        <Route path="/trades/:id" element={<TradeDetail />} />
        <Route path="/messages" element={<MessagesList />} />
        <Route path="/messages/:userId" element={<MessageThread />} />
        <Route path="/profile" element={<Profile />} />
        <Route path="/safety" element={<Safety />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="/admin" element={<Admin />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

function LandingOrRedirect() {
  const { user, loading } = useAuth();
  if (loading) return null;
  if (user) return <Navigate to="/dashboard" replace />;
  return <Landing />;
}

function GuestOrAppShell({ children }) {
  const { user, loading } = useAuth();
  if (loading) return null;
  if (user) return (
    <div className="min-h-screen flex flex-col">
      <TopNav />
      <main className="flex-1">{children}</main>
      <AppFooter />
      <BottomNav />
    </div>
  );
  return (
    <div className="min-h-screen flex flex-col">
      <GuestHeader />
      <main className="flex-1">{children}</main>
      <GuestFooter />
    </div>
  );
}

function GuestHeader() {
  return (
    <header className="sticky top-0 z-40 backdrop-blur-xl bg-background/85 border-b border-border/60">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between gap-3">
        <a href="/" className="flex items-center gap-2">
          <div className="w-9 h-9 rounded-xl bg-primary text-primary-foreground grid place-items-center font-heading font-bold">B</div>
          <span className="font-heading font-bold text-lg tracking-tight">BarterGrid</span>
        </a>
        <div className="flex items-center gap-2">
          <a href="https://aiwebtools.app" target="_blank" rel="noreferrer" className="hidden sm:inline-flex pill px-3.5 py-2 text-xs font-semibold bg-secondary/15 text-secondary border border-secondary/40 hover:bg-secondary hover:text-secondary-foreground transition-colors items-center gap-1.5">✨ FREE AI TOOLS</a>
          <a href="/login" className="pill px-4 py-2 text-sm font-medium hover:bg-muted transition-colors">Sign in</a>
          <a href="/signup" className="pill px-4 py-2 text-sm font-bold bg-primary text-primary-foreground shine">Sign up free</a>
        </div>
      </div>
    </header>
  );
}

function GuestFooter() {
  return (
    <footer className="border-t border-border py-8 px-4 sm:px-6 mt-12">
      <p className="text-xs text-center text-muted-foreground">
        Made with <span className="text-secondary">♥</span> by <a href="https://aiwebtools.app" target="_blank" rel="noreferrer" className="text-primary font-semibold">aiwebtools.app</a> — a free bartering service for the people, by the people.
      </p>
    </footer>
  );
}

export default function App() {
  return (
    <div className="App">
      <AuthProvider>
        <BrowserRouter>
          <Router />
          <Toaster position="top-right" richColors />
        </BrowserRouter>
      </AuthProvider>
    </div>
  );
}
