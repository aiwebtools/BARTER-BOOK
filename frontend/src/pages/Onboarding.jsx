import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import api from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";

const CITY_COORDS = {
  "san francisco, ca": [37.7749, -122.4194],
  "new york, ny": [40.7128, -74.006],
  "chicago, il": [41.8781, -87.6298],
  "los angeles, ca": [34.0522, -118.2437],
  "austin, tx": [30.2672, -97.7431],
  "seattle, wa": [47.6062, -122.3321],
  "denver, co": [39.7392, -104.9903],
  "portland, or": [45.5152, -122.6784],
};

export default function Onboarding() {
  const nav = useNavigate();
  const { refresh } = useAuth();
  const [city, setCity] = useState("");
  const [state, setState] = useState("");
  const [radius, setRadius] = useState(10);
  const [saving, setSaving] = useState(false);

  const save = async () => {
    setSaving(true);
    const key = `${city.toLowerCase().trim()}, ${state.toLowerCase().trim()}`;
    const coords = CITY_COORDS[key] || [37.7749 + Math.random() * 0.1, -122.4194 + Math.random() * 0.1];
    try {
      await api.patch("/profile", {
        city: city.trim(),
        state: state.trim().toUpperCase(),
        country: "USA",
        approx_lat: coords[0],
        approx_lng: coords[1],
        search_radius_miles: radius,
      });
      await refresh();
      toast.success("Location set!");
      nav("/dashboard");
    } catch {
      toast.error("Couldn't save location");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="min-h-screen mesh-bg" data-testid="onboarding-page">
      <div className="max-w-xl mx-auto px-6 py-16">
        <div className="rounded-3xl bg-card border border-border p-8 sm:p-10">
          <p className="text-sm font-bold uppercase tracking-[0.2em] text-primary mb-2">Step 1 of 1</p>
          <h1 className="font-heading text-3xl font-bold mb-2">Where are you located?</h1>
          <p className="text-muted-foreground mb-8">We only use approximate location. Your address stays private.</p>

          <div className="space-y-5">
            <div>
              <Label htmlFor="city">City</Label>
              <Input id="city" value={city} onChange={(e) => setCity(e.target.value)} className="h-12 rounded-xl mt-1" placeholder="e.g. San Francisco" data-testid="onboarding-city" />
            </div>
            <div>
              <Label htmlFor="state">State / Region</Label>
              <Input id="state" value={state} onChange={(e) => setState(e.target.value)} className="h-12 rounded-xl mt-1" placeholder="CA" data-testid="onboarding-state" />
            </div>
            <div>
              <Label>Search radius: {radius} miles</Label>
              <input type="range" min="1" max="50" value={radius} onChange={(e) => setRadius(Number(e.target.value))} className="w-full mt-2" data-testid="onboarding-radius" />
              <div className="flex justify-between text-xs text-muted-foreground mt-1">
                <span>1 mi</span><span>25 mi</span><span>50 mi</span>
              </div>
            </div>
          </div>

          <Button onClick={save} disabled={!city || !state || saving} className="w-full h-12 rounded-full mt-8" data-testid="onboarding-submit">
            {saving ? "Saving…" : "Enter BarterGrid"}
          </Button>
        </div>
      </div>
    </div>
  );
}
