import { Outlet, Navigate } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import TopNav, { BottomNav } from "@/components/TopNav";
import AppFooter from "@/components/AppFooter";

export default function AppLayout() {
  const { user, loading } = useAuth();
  if (loading) return <div className="min-h-screen grid place-items-center"><div className="w-10 h-10 border-4 border-primary/30 border-t-primary rounded-full animate-spin" /></div>;
  if (!user) return <Navigate to="/login" replace />;

  return (
    <div className="min-h-screen flex flex-col">
      <TopNav />
      <main className="flex-1">
        <Outlet />
      </main>
      <AppFooter />
      <BottomNav />
    </div>
  );
}
