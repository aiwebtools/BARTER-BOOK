import { Link } from "react-router-dom";
import { KIND_META } from "@/lib/api";
import { MapPin, Star } from "@phosphor-icons/react";

export default function ListingCard({ listing, action }) {
  const meta = KIND_META[listing.kind] || KIND_META.have;
  const photo = listing.photos?.[0];
  return (
    <div className="group rounded-2xl bg-card border border-border card-hover overflow-hidden flex flex-col" data-testid={`listing-card-${listing.listing_id}`}>
      <Link to={`/listings/view/${listing.listing_id}`} className="block">
        <div className="relative aspect-[4/3] bg-muted overflow-hidden">
          {photo ? (
            <img src={photo} alt={listing.title} className="w-full h-full object-cover transition-transform group-hover:scale-105" />
          ) : (
            <div className="w-full h-full grid place-items-center text-muted-foreground font-heading text-2xl">{listing.title?.[0]?.toUpperCase()}</div>
          )}
          <span className={`absolute top-3 left-3 pill px-3 py-1 text-xs font-semibold tracking-wide ${meta.cls}`} data-testid={`kind-badge-${listing.kind}`}>
            {meta.label}
          </span>
          {listing.distance_miles != null && (
            <span className="absolute top-3 right-3 pill px-3 py-1 text-xs bg-background/90 backdrop-blur border border-border flex items-center gap-1">
              <MapPin size={14} weight="fill" /> {listing.distance_miles} mi
            </span>
          )}
        </div>
        <div className="p-5 flex-1 flex flex-col gap-2">
          <div className="flex items-start justify-between gap-2">
            <h3 className="font-heading font-semibold text-lg leading-tight line-clamp-1">{listing.title}</h3>
          </div>
          <p className="text-sm text-muted-foreground line-clamp-2">{listing.description || "—"}</p>
          {listing.kind === "have" && listing.wants?.length > 0 && (
            <div className="mt-1 flex flex-wrap gap-1.5">
              <span className="text-xs text-muted-foreground">Wants:</span>
              {listing.wants.slice(0, 3).map((w) => (
                <span key={w} className="text-xs px-2 py-0.5 rounded-full bg-muted">{w}</span>
              ))}
            </div>
          )}
          <div className="mt-2 pt-3 border-t border-border flex items-center justify-between text-xs text-muted-foreground">
            <span className="truncate">{listing.user_display_name} · {listing.user_city || "Nearby"}</span>
            <span className="flex items-center gap-1"><Star size={14} weight="fill" className="text-secondary" /> {(listing.user_reputation || 0).toFixed(1)} · {listing.user_trades || 0} trades</span>
          </div>
        </div>
      </Link>
      {action && <div className="px-5 pb-5">{action}</div>}
    </div>
  );
}
