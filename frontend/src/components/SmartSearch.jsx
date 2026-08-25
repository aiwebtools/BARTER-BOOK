import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "@/lib/api";
import { MagnifyingGlass, MapPin, X } from "@phosphor-icons/react";

/**
 * SmartSearch — intelligent live search bar with dropdown suggestions.
 * Debounced queries hit /api/search/suggest; results show title, kind badge, distance.
 */
export default function SmartSearch({ compact = false }) {
  const nav = useNavigate();
  const [q, setQ] = useState("");
  const [results, setResults] = useState([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [active, setActive] = useState(-1);
  const debounceRef = useRef();
  const wrapRef = useRef();

  useEffect(() => {
    if (!q.trim()) { setResults([]); setLoading(false); return; }
    setLoading(true);
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(async () => {
      try {
        const r = await api.get(`/search/suggest?q=${encodeURIComponent(q.trim())}`);
        setResults(r.data);
        setOpen(true);
      } catch { setResults([]); }
      finally { setLoading(false); }
    }, 200);
    return () => clearTimeout(debounceRef.current);
  }, [q]);

  useEffect(() => {
    const onClick = (e) => { if (wrapRef.current && !wrapRef.current.contains(e.target)) setOpen(false); };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  const submit = () => {
    if (!q.trim()) return;
    nav(`/discover?q=${encodeURIComponent(q.trim())}`);
    setOpen(false);
  };

  const kindMeta = {
    have: { l: "HAVE", cls: "bg-accent text-accent-foreground" },
    need: { l: "NEED", cls: "bg-secondary text-secondary-foreground" },
    service: { l: "CAN DO", cls: "bg-primary text-primary-foreground" },
  };

  return (
    <div ref={wrapRef} className="relative" data-testid="smart-search">
      <div className={`relative rounded-2xl bg-card border border-border ${open && results.length > 0 ? "rounded-b-none border-b-transparent" : ""}`}>
        <MagnifyingGlass size={20} className="absolute left-5 top-1/2 -translate-y-1/2 text-primary" weight="bold" />
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onFocus={() => q && setOpen(true)}
          onKeyDown={(e) => {
            if (e.key === "Enter") { if (active >= 0 && results[active]) { nav(`/listings/view/${results[active].listing_id}`); } else submit(); }
            else if (e.key === "ArrowDown") { e.preventDefault(); setActive((a) => Math.min(a + 1, results.length - 1)); }
            else if (e.key === "ArrowUp") { e.preventDefault(); setActive((a) => Math.max(a - 1, -1)); }
            else if (e.key === "Escape") setOpen(false);
          }}
          placeholder={compact ? "Search…" : "Search — a drill, a bike, a plumber near you…"}
          className={`w-full ${compact ? "h-11 pl-12 pr-11 text-sm" : "h-14 pl-14 pr-14 text-base"} bg-transparent rounded-2xl focus:outline-none focus:ring-2 focus:ring-primary/40 font-medium`}
          data-testid="smart-search-input"
        />
        {q && (
          <button onClick={() => { setQ(""); setResults([]); }} className="absolute right-4 top-1/2 -translate-y-1/2 p-1 rounded-full hover:bg-muted" aria-label="Clear" data-testid="smart-search-clear">
            <X size={18} />
          </button>
        )}
      </div>

      {open && q.trim() && (
        <div className="absolute z-20 inset-x-0 top-full rounded-b-2xl bg-card border border-t-0 border-border shadow-xl max-h-[420px] overflow-y-auto" data-testid="smart-search-dropdown">
          {loading && <div className="px-5 py-3 text-sm text-muted-foreground">Searching…</div>}
          {!loading && results.length === 0 && (
            <div className="px-5 py-4 text-sm text-muted-foreground">No matches for "<span className="font-medium">{q}</span>". Press Enter to open Discover.</div>
          )}
          {results.map((r, i) => {
            const km = kindMeta[r.kind] || kindMeta.have;
            return (
              <button
                key={r.listing_id}
                onClick={() => nav(`/listings/view/${r.listing_id}`)}
                onMouseEnter={() => setActive(i)}
                className={`w-full flex items-center gap-3 px-4 py-3 text-left transition-colors border-t border-border/50 first:border-0 ${active === i ? "bg-muted" : "hover:bg-muted/60"}`}
                data-testid={`search-result-${r.listing_id}`}
              >
                <div className="w-11 h-11 rounded-xl bg-muted overflow-hidden shrink-0">
                  {r.photos?.[0] ? <img src={r.photos[0]} alt="" className="w-full h-full object-cover" /> : <div className="w-full h-full grid place-items-center font-heading font-bold text-primary">{r.title?.[0]?.toUpperCase()}</div>}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className={`pill px-2 py-0.5 text-[10px] font-bold ${km.cls}`}>{km.l}</span>
                    <span className="text-xs text-muted-foreground truncate">{r.category}</span>
                  </div>
                  <div className="font-semibold truncate">{r.title}</div>
                </div>
                {r.distance_miles != null && (
                  <span className="pill px-2.5 py-1 text-xs bg-muted flex items-center gap-1 shrink-0"><MapPin size={12} weight="fill" /> {r.distance_miles} mi</span>
                )}
              </button>
            );
          })}
          {results.length > 0 && (
            <button onClick={submit} className="w-full text-center text-sm font-medium text-primary py-3 border-t border-border hover:bg-muted/60 transition-colors" data-testid="search-see-all">
              See all results for "{q}" →
            </button>
          )}
        </div>
      )}
    </div>
  );
}
