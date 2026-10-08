import { useEffect, useRef, useState } from "react";
import { useAuth } from "../auth/AuthContext";

/** Landing page of the identity provider's redirect: exchanges the code, then returns to where the user was. */
export function AuthCallbackPage() {
  const { client } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const started = useRef(false);
  useEffect(() => {
    if (!client || started.current) return;
    started.current = true; // the code can be exchanged only once (StrictMode runs effects twice)
    client.completeLogin(window.location.search)
      .then((returnTo) => window.location.replace(returnTo)) // full reload: the app starts signed in
      .catch((e: Error) => setError(e.message));
  }, [client]);
  return <div className="card empty">{error ?? "Signing in…"}</div>;
}
