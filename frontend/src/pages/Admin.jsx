import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";
import { Navigate } from "react-router-dom";
import api from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { toast } from "sonner";
import { ShieldWarning, Users, Package, Trash, Prohibit } from "@phosphor-icons/react";

export default function Admin() {
  const { user, loading } = useAuth();
  const [reports, setReports] = useState([]);
  const [users, setUsers] = useState([]);
  const [listings, setListings] = useState([]);

  useEffect(() => {
    if (user?.role !== "admin") return;
    Promise.all([
      api.get("/admin/reports").then((r) => setReports(r.data)).catch(() => {}),
      api.get("/admin/users").then((r) => setUsers(r.data)).catch(() => {}),
      api.get("/listings").then((r) => setListings(r.data)).catch(() => {}),
    ]);
  }, [user]);

  if (loading) return null;
  if (user?.role !== "admin") return <Navigate to="/dashboard" replace />;

  const suspend = async (uid) => {
    if (!window.confirm("Suspend this user?")) return;
    await api.post(`/admin/users/${uid}/suspend`);
    toast.success("User suspended");
    const r = await api.get("/admin/users"); setUsers(r.data);
  };
  const delListing = async (lid) => {
    if (!window.confirm("Delete listing?")) return;
    await api.delete(`/admin/listings/${lid}`);
    toast.success("Listing removed");
    const r = await api.get("/listings"); setListings(r.data);
  };

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8 pb-24 md:pb-8" data-testid="admin-page">
      <p className="text-sm font-bold uppercase tracking-[0.2em] text-primary mb-1 flex items-center gap-2"><ShieldWarning size={16} weight="fill" /> Admin</p>
      <h1 className="font-heading text-3xl sm:text-4xl font-bold mb-8">Moderation console</h1>

      <div className="grid grid-cols-3 gap-3 mb-8">
        <Stat n={reports.filter((r) => r.status === "open").length} label="Open reports" icon={ShieldWarning} />
        <Stat n={users.length} label="Total users" icon={Users} />
        <Stat n={listings.length} label="Active listings" icon={Package} />
      </div>

      <Tabs defaultValue="reports">
        <TabsList className="h-auto bg-transparent p-0 gap-2 mb-6">
          <TabsTrigger value="reports" className="pill h-10 px-5 data-[state=active]:bg-primary data-[state=active]:text-primary-foreground border border-border" data-testid="admin-tab-reports">Reports ({reports.length})</TabsTrigger>
          <TabsTrigger value="users" className="pill h-10 px-5 data-[state=active]:bg-primary data-[state=active]:text-primary-foreground border border-border" data-testid="admin-tab-users">Users ({users.length})</TabsTrigger>
          <TabsTrigger value="listings" className="pill h-10 px-5 data-[state=active]:bg-primary data-[state=active]:text-primary-foreground border border-border" data-testid="admin-tab-listings">Listings ({listings.length})</TabsTrigger>
        </TabsList>

        <TabsContent value="reports">
          {reports.length === 0 ? <Empty msg="No reports yet." /> : (
            <div className="space-y-3">
              {reports.map((r) => (
                <div key={r.id} className="rounded-2xl bg-card border border-border p-5" data-testid={`report-${r.id}`}>
                  <div className="flex items-center justify-between gap-3 mb-2">
                    <div className="flex items-center gap-2 text-sm">
                      <span className="pill px-3 py-1 text-xs font-bold bg-secondary text-secondary-foreground">{r.reason}</span>
                      <span className="text-muted-foreground">on {r.target_type}: {r.target_id}</span>
                    </div>
                    <span className="text-xs text-muted-foreground">{new Date(r.created_at).toLocaleDateString()}</span>
                  </div>
                  {r.description && <p className="text-sm mt-2">{r.description}</p>}
                </div>
              ))}
            </div>
          )}
        </TabsContent>

        <TabsContent value="users">
          <div className="rounded-2xl border border-border bg-card overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-muted/50">
                <tr className="text-left">
                  <th className="p-3">Name</th><th className="p-3">City</th><th className="p-3">Trades</th><th className="p-3">Role</th><th className="p-3"></th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.user_id} className="border-t border-border" data-testid={`admin-user-${u.user_id}`}>
                    <td className="p-3 font-medium">{u.display_name}</td>
                    <td className="p-3 text-muted-foreground">{u.city || "—"}</td>
                    <td className="p-3">{u.successful_trades || 0}</td>
                    <td className="p-3"><span className={`pill px-2 py-0.5 text-xs ${u.role === "admin" ? "bg-primary text-primary-foreground" : u.role === "suspended" ? "bg-destructive text-destructive-foreground" : "bg-muted"}`}>{u.role}</span></td>
                    <td className="p-3 text-right">
                      {u.role !== "admin" && u.role !== "suspended" && (
                        <Button size="sm" variant="destructive" onClick={() => suspend(u.user_id)} className="rounded-full" data-testid={`suspend-${u.user_id}`}><Prohibit size={14} className="mr-1" /> Suspend</Button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </TabsContent>

        <TabsContent value="listings">
          <div className="grid sm:grid-cols-2 gap-3">
            {listings.map((l) => (
              <div key={l.listing_id} className="rounded-2xl bg-card border border-border p-5 flex items-center justify-between gap-3">
                <div className="min-w-0">
                  <span className="pill px-2 py-0.5 text-[10px] font-bold bg-muted">{l.kind.toUpperCase()}</span>
                  <div className="font-heading font-semibold truncate mt-1">{l.title}</div>
                  <div className="text-xs text-muted-foreground">{l.user_display_name}</div>
                </div>
                <Button size="sm" variant="destructive" onClick={() => delListing(l.listing_id)} className="rounded-full" data-testid={`admin-del-${l.listing_id}`}><Trash size={14} /></Button>
              </div>
            ))}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}

function Stat({ n, label, icon: Icon }) {
  return (
    <div className="rounded-2xl bg-card border border-border p-5">
      <Icon size={22} weight="duotone" className="text-primary mb-2" />
      <div className="font-heading text-2xl font-bold">{n}</div>
      <div className="text-xs text-muted-foreground">{label}</div>
    </div>
  );
}

function Empty({ msg }) {
  return <div className="rounded-2xl border border-dashed border-border p-12 text-center text-muted-foreground">{msg}</div>;
}
