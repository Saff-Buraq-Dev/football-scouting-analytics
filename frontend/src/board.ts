// Typed client for the recruitment board API (src/football_platform/api/board.py, D032).
import type { AuthClient } from "./auth/client";

export interface Shortlist { id: string; name: string; description: string; size: number; updated_at: string }

export interface ShortlistEntry {
  player_id: string;
  season_id: string;
  player_name: string;
  season_label: string;
  competition: string;
  teams: string[] | null;
  minutes: number | null;
  position_group: string | null;
  primary_role: string | null;
  eligible: boolean | null;
  tags: string[];
  notes: number;
  added_at: string;
}

export interface Note {
  id: string;
  player_id: string;
  season_id: string | null;
  season_label: string | null;
  body: string;
  created_at: string;
  updated_at: string;
}

export interface PlayerBoard {
  shortlists: { shortlist_id: string; name: string; season_id: string }[];
  tags: string[];
  notes: Note[];
}

export class BoardApi {
  constructor(private readonly auth: AuthClient) {}

  private async request<T>(method: string, path: string, body?: unknown): Promise<T> {
    const headers: Record<string, string> = {};
    const token = this.auth.token();
    if (token) headers.Authorization = `Bearer ${token}`;
    if (body !== undefined) headers["Content-Type"] = "application/json";
    const response = await fetch(path, { method, headers, body: body === undefined ? undefined : JSON.stringify(body) });
    if (!response.ok) {
      const detail = await response.json().then((d) => (typeof d.detail === "string" ? d.detail : null)).catch(() => null);
      throw new Error(detail ?? `HTTP ${response.status}`);
    }
    return (response.status === 204 ? undefined : await response.json()) as T;
  }

  shortlists = () => this.request<Shortlist[]>("GET", "/api/shortlists");
  createShortlist = (name: string, description = "") =>
    this.request<Shortlist>("POST", "/api/shortlists", { name, description });
  renameShortlist = (id: string, name: string, description?: string) =>
    this.request<Shortlist>("PATCH", `/api/shortlists/${id}`, { name, description });
  deleteShortlist = (id: string) => this.request<void>("DELETE", `/api/shortlists/${id}`);
  entries = (id: string) => this.request<ShortlistEntry[]>("GET", `/api/shortlists/${id}/entries`);
  addEntry = (id: string, playerId: string, seasonId: string) =>
    this.request<void>("PUT", `/api/shortlists/${id}/entries/${playerId}/${seasonId}`);
  removeEntry = (id: string, playerId: string, seasonId: string) =>
    this.request<void>("DELETE", `/api/shortlists/${id}/entries/${playerId}/${seasonId}`);
  tags = () => this.request<{ tag: string; players: number }[]>("GET", "/api/tags");
  playerBoard = (playerId: string) => this.request<PlayerBoard>("GET", `/api/players/${playerId}/board`);
  addTag = (playerId: string, tag: string) =>
    this.request<{ tag: string }>("PUT", `/api/players/${playerId}/tags/${encodeURIComponent(tag)}`);
  removeTag = (playerId: string, tag: string) =>
    this.request<void>("DELETE", `/api/players/${playerId}/tags/${encodeURIComponent(tag)}`);
  addNote = (playerId: string, body: string, seasonId?: string) =>
    this.request<Note>("POST", `/api/players/${playerId}/notes`, { body, season_id: seasonId ?? null });
  updateNote = (id: string, body: string) => this.request<Note>("PATCH", `/api/notes/${id}`, { body });
  deleteNote = (id: string) => this.request<void>("DELETE", `/api/notes/${id}`);
}
