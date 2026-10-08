// Login, abstracted (D032). The app asks an AuthClient for a bearer token and never sees a password.
// - "disabled": no personal features. - "dev": the server treats every request as one local user.
// - "oidc": authorization-code flow with PKCE against Cognito (or any OpenID Connect provider), public client.
import { codeChallenge, randomString, tokenExpiry } from "./pkce";

export interface AuthConfig {
  mode: "disabled" | "dev" | "oidc";
  issuer?: string;
  client_id?: string;
  scopes?: string;
  authorization_endpoint?: string;
  token_endpoint?: string;
  end_session_endpoint?: string | null;
  error?: string;
}

export interface AuthClient {
  mode: AuthConfig["mode"];
  /** Bearer token for API calls, or null (not logged in, or not needed). */
  token(): string | null;
  /** Whether the user must log in before using personal features. */
  needsLogin(): boolean;
  login(returnTo: string): Promise<void>;
  logout(): void;
  /** Finish a login on the callback page; returns the path to go back to. */
  completeLogin(search: string): Promise<string>;
}

export const CALLBACK_PATH = "/auth/callback";
const TOKEN_KEY = "auth.token";
const PENDING_KEY = "auth.pending";
const EXPIRY_MARGIN_MS = 60_000;

// sessionStorage: the token is forgotten when the tab closes. Wrapped: storage can be unavailable.
const storage = {
  get(key: string): string | null {
    try { return sessionStorage.getItem(key); } catch { return null; }
  },
  set(key: string, value: string) {
    try { sessionStorage.setItem(key, value); } catch { /* storage unavailable: stay logged out */ }
  },
  remove(key: string) {
    try { sessionStorage.removeItem(key); } catch { /* ignore */ }
  },
};

function simpleClient(mode: "disabled" | "dev"): AuthClient {
  return {
    mode,
    token: () => null,
    needsLogin: () => false,
    login: async () => undefined,
    logout: () => undefined,
    completeLogin: async () => "/",
  };
}

function oidcClient(config: AuthConfig): AuthClient {
  const redirectUri = `${window.location.origin}${CALLBACK_PATH}`;
  const token = () => {
    const value = storage.get(TOKEN_KEY);
    if (!value) return null;
    const expiry = tokenExpiry(value);
    if (expiry !== null && expiry - EXPIRY_MARGIN_MS < Date.now()) {
      storage.remove(TOKEN_KEY); // expired: log in again (no refresh token in v1)
      return null;
    }
    return value;
  };
  return {
    mode: "oidc",
    token,
    needsLogin: () => token() === null,
    async login(returnTo) {
      if (!config.authorization_endpoint || !config.client_id) throw new Error("Identity provider unavailable");
      const verifier = randomString(48);
      const state = randomString(16);
      storage.set(PENDING_KEY, JSON.stringify({ verifier, state, returnTo }));
      const params = new URLSearchParams({
        response_type: "code", client_id: config.client_id, redirect_uri: redirectUri,
        scope: config.scopes ?? "openid", state, code_challenge: await codeChallenge(verifier),
        code_challenge_method: "S256",
      });
      window.location.assign(`${config.authorization_endpoint}?${params}`);
    },
    logout() {
      storage.remove(TOKEN_KEY);
    },
    async completeLogin(search) {
      const params = new URLSearchParams(search);
      const pending = JSON.parse(storage.get(PENDING_KEY) ?? "null") as
        { verifier: string; state: string; returnTo: string } | null;
      storage.remove(PENDING_KEY);
      if (params.get("error")) throw new Error(params.get("error_description") ?? params.get("error")!);
      if (!pending || params.get("state") !== pending.state) throw new Error("Login state mismatch: try again");
      const response = await fetch(config.token_endpoint!, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: new URLSearchParams({
          grant_type: "authorization_code", client_id: config.client_id!, code: params.get("code") ?? "",
          redirect_uri: redirectUri, code_verifier: pending.verifier,
        }),
      });
      if (!response.ok) throw new Error(`Login failed (HTTP ${response.status})`);
      const tokens = (await response.json()) as { access_token?: string; id_token?: string };
      const value = tokens.access_token ?? tokens.id_token;
      if (!value) throw new Error("Login failed: no token");
      storage.set(TOKEN_KEY, value);
      return pending.returnTo || "/";
    },
  };
}

export function createAuthClient(config: AuthConfig): AuthClient {
  return config.mode === "oidc" ? oidcClient(config) : simpleClient(config.mode);
}
