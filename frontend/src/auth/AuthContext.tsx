import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { createAuthClient, type AuthClient, type AuthConfig } from "./client";

export interface CurrentUser { id: string; email: string | null; name: string | null }

interface AuthState {
  /** null while the server's auth configuration loads. */
  client: AuthClient | null;
  config: AuthConfig | null;
  user: CurrentUser | null;
  /** Bumped after login/logout so views reload personal data. */
  version: number;
  login(): void;
  logout(): void;
}

const AuthContext = createContext<AuthState | null>(null);

/** Loads the server's auth mode, then the current user when a session exists (D032). */
export function AuthProvider({ children }: { children: ReactNode }) {
  const [config, setConfig] = useState<AuthConfig | null>(null);
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [version, setVersion] = useState(0);

  useEffect(() => {
    fetch("/api/auth/config")
      .then((r) => (r.ok ? (r.json() as Promise<AuthConfig>) : { mode: "disabled" as const }))
      .catch(() => ({ mode: "disabled" as const }))
      .then(setConfig);
  }, []);

  const client = useMemo(() => (config ? createAuthClient(config) : null), [config]);

  useEffect(() => {
    if (!client || client.mode === "disabled" || client.needsLogin()) {
      setUser(null);
      return;
    }
    const token = client.token();
    fetch("/api/me", { headers: token ? { Authorization: `Bearer ${token}` } : {} })
      .then((r) => (r.ok ? (r.json() as Promise<CurrentUser>) : null))
      .catch(() => null)
      .then(setUser);
  }, [client, version]);

  const login = useCallback(() => {
    client?.login(window.location.pathname + window.location.search).catch((e: Error) => alert(e.message));
  }, [client]);
  const logout = useCallback(() => {
    client?.logout();
    setVersion((v) => v + 1);
  }, [client]);

  const value = useMemo(() => ({ client, config, user, version, login, logout }), [client, config, user, version, login, logout]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const state = useContext(AuthContext);
  if (!state) throw new Error("useAuth outside AuthProvider");
  return state;
}

