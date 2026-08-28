import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { GoogleLogo } from "@phosphor-icons/react";

function getSubmitLabel(loading, mode) {
  if (loading) return "Please wait…";
  return mode === "signup" ? "Create account" : "Sign in";
}

export default function Login({ mode = "login" }) {
  const nav = useNavigate();
  const { login, signup } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      if (mode === "signup") {
        await signup(email, password, name || email.split("@")[0]);
        toast.success("Welcome to BarterGrid!");
        nav("/onboarding");
      } else {
        await login(email, password);
        toast.success("Signed in");
        nav("/dashboard");
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || "Auth failed");
    } finally {
      setLoading(false);
    }
  };

  const googleLogin = () => {
    // REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
    const redirectUrl = window.location.origin + "/dashboard";
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
  };

  return (
    <div className="min-h-screen grid lg:grid-cols-2" data-testid={`${mode}-page`}>
      <div className="hidden lg:block relative mesh-bg">
        <div className="absolute inset-0 dot-grid opacity-40" />
        <div className="relative h-full flex flex-col justify-between p-12">
          <Link to="/" className="flex items-center gap-2 w-fit">
            <div className="w-9 h-9 rounded-xl bg-primary text-primary-foreground grid place-items-center font-heading font-bold">B</div>
            <span className="font-heading font-bold text-xl">BarterGrid</span>
          </Link>
          <div className="max-w-md space-y-4">
            <h2 className="font-heading text-3xl font-bold leading-tight">Local exchange, real people, no price tags.</h2>
            <p className="text-muted-foreground">Trade what you have for what you need. Build reputation. Meet safely.</p>
          </div>
          <p className="text-xs text-muted-foreground">© BarterGrid — a community exchange network.</p>
        </div>
      </div>

      <div className="flex items-center justify-center p-6 sm:p-12">
        <div className="w-full max-w-md">
          <div className="lg:hidden mb-8">
            <Link to="/" className="flex items-center gap-2">
              <div className="w-9 h-9 rounded-xl bg-primary text-primary-foreground grid place-items-center font-heading font-bold">B</div>
              <span className="font-heading font-bold text-xl">BarterGrid</span>
            </Link>
          </div>

          <h1 className="font-heading text-3xl font-bold mb-2">{mode === "signup" ? "Create your account" : "Welcome back"}</h1>
          <p className="text-muted-foreground mb-8">{mode === "signup" ? "Start trading with your community." : "Sign in to continue trading."}</p>

          <Button variant="outline" className="w-full h-12 rounded-full mb-4" onClick={googleLogin} data-testid="google-signin">
            <GoogleLogo size={20} weight="bold" className="mr-2" /> Continue with Google
          </Button>

          <div className="relative my-6">
            <div className="absolute inset-0 flex items-center"><div className="w-full border-t border-border" /></div>
            <div className="relative flex justify-center text-xs uppercase tracking-widest"><span className="bg-background px-3 text-muted-foreground">or</span></div>
          </div>

          <form onSubmit={submit} className="space-y-4">
            {mode === "signup" && (
              <div>
                <Label htmlFor="name">Display name</Label>
                <Input id="name" value={name} onChange={(e) => setName(e.target.value)} className="h-12 rounded-xl mt-1" placeholder="Maya P." data-testid="signup-name" />
              </div>
            )}
            <div>
              <Label htmlFor="email">Email</Label>
              <Input id="email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} className="h-12 rounded-xl mt-1" placeholder="you@example.com" data-testid="auth-email" />
            </div>
            <div>
              <Label htmlFor="password">Password</Label>
              <Input id="password" type="password" required minLength={6} value={password} onChange={(e) => setPassword(e.target.value)} className="h-12 rounded-xl mt-1" placeholder="••••••••" data-testid="auth-password" />
            </div>
            <Button type="submit" className="w-full h-12 rounded-full" disabled={loading} data-testid="auth-submit">
              {getSubmitLabel(loading, mode)}
            </Button>
          </form>

          <p className="text-sm text-muted-foreground mt-6 text-center">
            {mode === "signup" ? (
              <>Already have an account? <Link to="/login" className="text-primary font-medium">Sign in</Link></>
            ) : (
              <>New here? <Link to="/signup" className="text-primary font-medium">Create an account</Link></>
            )}
          </p>
          <p className="text-xs text-muted-foreground mt-6 text-center">By continuing you agree to our Community Rules and Safety guidelines.</p>
        </div>
      </div>
    </div>
  );
}
