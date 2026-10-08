import { useAuth } from "../auth/AuthContext";

/** Top-bar login state. Nothing when login is disabled on the server. */
export function UserMenu() {
  const { client, user, login, logout } = useAuth();
  if (!client || client.mode === "disabled") return null;
  if (client.mode === "dev") return <span className="user-chip" title="AUTH_PROVIDER=dev: single local user">Local user</span>;
  if (!user) return <button className="button small" onClick={login}>Log in</button>;
  return (
    <span className="user-chip">
      {user.name ?? user.email ?? "Signed in"} <button className="link-button" onClick={logout}>Log out</button>
    </span>
  );
}
