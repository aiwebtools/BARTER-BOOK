import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import api from "@/lib/api";
import { useAuth } from "@/lib/auth";
import ListingCard from "@/components/ListingCard";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { Trash, PencilSimple, ArrowLeft } from "@phosphor-icons/react";

export function MyListings() {
  const nav = useNavigate();
  const [items, setItems] = useState([]);

  const load = async () => {
    const r = await api.get("/listings?mine=true");
    setItems(r.data);
  };
  useEffect(() => { load(); }, []);

  const del = async (id) => {
    if (!window.confirm("Delete this listing?")) return;
    await api.delete(`/listings/${id}`);
    toast.success("Deleted");
    load();
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8 pb-24 md:pb-8" data-testid="my-listings-page">
      <div className="flex items-center justify-between mb-8">
        <div>
          <p className="text-sm font-bold uppercase tracking-[0.2em] text-primary mb-1">Your listings</p>
          <h1 className="font-heading text-3xl sm:text-4xl font-bold">Everything you've posted.</h1>
        </div>
        <Button onClick={() => nav("/new")} className="rounded-full h-12 px-6">Post new</Button>
      </div>
      {items.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-border p-16 text-center">
          <h3 className="font-heading font-semibold text-xl mb-2">Nothing posted yet</h3>
          <p className="text-muted-foreground mb-6">Add your first listing to start trading.</p>
          <Button onClick={() => nav("/new")} className="rounded-full">Post something</Button>
        </div>
      ) : (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {items.map((l) => (
            <ListingCard key={l.listing_id} listing={l} action={
              <div className="flex gap-2 pt-3 border-t border-border">
                <Button variant="destructive" size="sm" className="rounded-full flex-1" onClick={() => del(l.listing_id)} data-testid={`delete-${l.listing_id}`}><Trash size={16} className="mr-1" /> Delete</Button>
              </div>
            } />
          ))}
        </div>
      )}
    </div>
  );
}

export function ListingDetail() {
  const { id } = useParams();
  const nav = useNavigate();
  const { user } = useAuth();
  const [listing, setListing] = useState(null);
  const [proposing, setProposing] = useState(false);
  const [myHaves, setMyHaves] = useState([]);
  const [chosenMine, setChosenMine] = useState("");
  const [message, setMessage] = useState("");

  useEffect(() => {
    api.get(`/listings/${id}`).then((r) => setListing(r.data));
    api.get(`/listings?mine=true&kind=have`).then((r) => setMyHaves(r.data));
  }, [id]);

  const propose = async () => {
    if (!chosenMine) { toast.error("Pick something to offer"); return; }
    try {
      const r = await api.post("/trades", {
        to_user_id: listing.user_id,
        my_listing_id: chosenMine,
        their_listing_id: listing.listing_id,
        message,
      });
      toast.success("Trade proposed!");
      nav(`/trades/${r.data.trade_id}`);
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed");
    }
  };

  if (!listing) return <div className="p-8">Loading…</div>;
  const mine = listing.user_id === user?.user_id;

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 py-8 pb-24 md:pb-8" data-testid="listing-detail">
      <button onClick={() => nav(-1)} className="text-sm text-muted-foreground mb-4 flex items-center gap-1"><ArrowLeft size={16} /> Back</button>
      <div className="rounded-2xl bg-card border border-border overflow-hidden">
        {listing.photos?.[0] && (
          <div className="aspect-[16/9] bg-muted">
            <img src={listing.photos[0]} alt="" className="w-full h-full object-cover" />
          </div>
        )}
        <div className="p-6 sm:p-8">
          <div className="flex flex-wrap items-center gap-2 mb-3">
            <span className={`pill px-3 py-1 text-xs font-bold ${listing.kind === "have" ? "bg-accent text-accent-foreground" : listing.kind === "need" ? "bg-secondary text-secondary-foreground" : "bg-primary text-primary-foreground"}`}>
              {listing.kind === "have" ? "HAVE" : listing.kind === "need" ? "NEED" : "CAN DO"}
            </span>
            <span className="text-xs text-muted-foreground">{listing.category}</span>
            {listing.condition && <span className="text-xs text-muted-foreground">· {listing.condition}</span>}
          </div>
          <h1 className="font-heading text-3xl font-bold mb-3">{listing.title}</h1>
          <p className="text-muted-foreground leading-relaxed mb-6">{listing.description || "No description."}</p>

          {listing.wants?.length > 0 && (
            <div className="mb-6">
              <p className="text-sm font-semibold mb-2">Wanted in exchange:</p>
              <div className="flex flex-wrap gap-2">
                {listing.wants.map((w) => <span key={w} className="pill px-3 py-1 bg-muted text-sm">{w}</span>)}
              </div>
            </div>
          )}

          <div className="rounded-xl bg-muted/50 p-4 mb-6">
            <div className="flex items-center justify-between gap-2">
              <div className="min-w-0">
                <Link to={`/u/${listing.user_id}`} className="font-semibold hover:text-primary transition-colors" data-testid="owner-link">{listing.user_display_name}</Link>
                <span className="text-sm text-muted-foreground"> · {listing.user_city || "Nearby"}</span>
                {listing.distance_miles != null && <span className="text-sm text-muted-foreground"> · {listing.distance_miles} mi away</span>}
                <div className="text-xs text-muted-foreground mt-1">⭐ {(listing.user_reputation || 0).toFixed(1)} · {listing.user_trades || 0} trades completed</div>
              </div>
              {!mine && (
                <Button variant="outline" size="sm" className="rounded-full shrink-0" onClick={() => nav(`/messages/${listing.user_id}`)} data-testid="msg-owner">Message</Button>
              )}
            </div>
          </div>

          {mine ? (
            <p className="text-sm text-muted-foreground italic">This is your own listing.</p>
          ) : (
            <>
              {!proposing ? (
                <Button onClick={() => setProposing(true)} className="rounded-full h-12 px-8" data-testid="open-propose">Propose a trade</Button>
              ) : (
                <div className="rounded-xl border border-border p-5 bg-background">
                  <p className="font-heading font-semibold mb-3">Propose a trade</p>
                  <label className="text-sm block mb-1">You offer:</label>
                  <select value={chosenMine} onChange={(e) => setChosenMine(e.target.value)} className="h-12 w-full rounded-xl border border-border bg-background px-3 mb-3" data-testid="propose-mine">
                    <option value="">Pick something you have…</option>
                    {myHaves.map((l) => <option key={l.listing_id} value={l.listing_id}>{l.title}</option>)}
                  </select>
                  <label className="text-sm block mb-1">Message (optional):</label>
                  <textarea value={message} onChange={(e) => setMessage(e.target.value)} rows={3} placeholder="Would you be interested in trading?" className="w-full rounded-xl border border-border bg-background p-3 mb-3" data-testid="propose-message" />
                  <div className="flex gap-2">
                    <Button onClick={propose} className="rounded-full flex-1" data-testid="submit-propose">Send proposal</Button>
                    <Button variant="outline" className="rounded-full" onClick={() => setProposing(false)}>Cancel</Button>
                  </div>
                  {myHaves.length === 0 && <p className="text-xs text-muted-foreground mt-3">You need to post an "I HAVE" listing first. <Link to="/new" className="text-primary underline">Post one</Link></p>}
                </div>
              )}
              <button
                onClick={async () => {
                  const reason = window.prompt("Report reason (spam, scam, prohibited, harassment, other):");
                  if (!reason) return;
                  try { await api.post("/reports", { target_type: "listing", target_id: listing.listing_id, reason }); toast.success("Reported. Our team will review."); }
                  catch { toast.error("Failed"); }
                }}
                className="mt-4 text-xs text-muted-foreground hover:text-destructive transition-colors"
                data-testid="report-listing"
              >Report this listing</button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
