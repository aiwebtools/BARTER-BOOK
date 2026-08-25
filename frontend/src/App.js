import "@/App.css";
import { BrowserRouter, Routes, Route, useLocation, Navigate } from "react-router-dom";
import { Toaster } from "sonner";
import { AuthProvider, useAuth } from "@/lib/auth";
import AppLayout from "@/components/AppLayout";
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
      <Route element={<AppLayout />}>
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/discover" element={<Discover />} />
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
