import { useMemo } from "react";
import { BoardApi } from "../board";
import { useAuth } from "./AuthContext";

/** The board API when a user is signed in, else null. */
export function useBoardApi(): BoardApi | null {
  const { client, user } = useAuth();
  return useMemo(() => (client && user ? new BoardApi(client) : null), [client, user]);
}
