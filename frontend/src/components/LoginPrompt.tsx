import { useAuth } from "../auth/AuthContext";

/** Shown where personal features would be, when a login is possible but the user is signed out. */
export function LoginPrompt({ what }: { what: string }) {
  const { client, login } = useAuth();
  if (!client || client.mode !== "oidc") return null;
  return (
    <p className="secondary">
      <button className="button small" onClick={login}>Log in</button> to {what}.
    </p>
  );
}
