-- Recruitment board (Phase 11.9, D032): user-generated data, kept apart from provider and analytics data.
-- Users come from an external identity provider (Cognito, any OIDC): no password is stored here.
-- References go to players and seasons, which reloads upsert and never delete; never to player_seasons,
-- which every analytics run rebuilds.

CREATE TABLE app_users (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    issuer        text NOT NULL,          -- identity provider ("dev" or the OIDC issuer URL)
    subject       text NOT NULL,          -- the provider's stable user id ("sub" claim)
    email         text,
    display_name  text,
    created_at    timestamptz NOT NULL DEFAULT now(),
    last_seen_at  timestamptz NOT NULL DEFAULT now(),
    UNIQUE (issuer, subject)
);

CREATE TABLE shortlists (
    id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id     uuid NOT NULL REFERENCES app_users (id) ON DELETE CASCADE,
    name         text NOT NULL CHECK (length(name) BETWEEN 1 AND 80),
    description  text NOT NULL DEFAULT '' CHECK (length(description) <= 500),
    created_at   timestamptz NOT NULL DEFAULT now(),
    updated_at   timestamptz NOT NULL DEFAULT now(),
    UNIQUE (owner_id, name)
);

-- A shortlist holds player-seasons: the analytics behind a recommendation are per season.
CREATE TABLE shortlist_entries (
    shortlist_id  uuid NOT NULL REFERENCES shortlists (id) ON DELETE CASCADE,
    player_id     uuid NOT NULL REFERENCES players (id),
    season_id     uuid NOT NULL REFERENCES seasons (id),
    added_at      timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (shortlist_id, player_id, season_id)
);

-- Tags describe the player (all seasons), and are private to their owner.
CREATE TABLE player_tags (
    owner_id    uuid NOT NULL REFERENCES app_users (id) ON DELETE CASCADE,
    player_id   uuid NOT NULL REFERENCES players (id),
    tag         text NOT NULL CHECK (length(tag) BETWEEN 1 AND 30),
    created_at  timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (owner_id, player_id, tag)
);

CREATE TABLE player_notes (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id    uuid NOT NULL REFERENCES app_users (id) ON DELETE CASCADE,
    player_id   uuid NOT NULL REFERENCES players (id),
    season_id   uuid REFERENCES seasons (id),   -- the season the note is about, if any
    body        text NOT NULL CHECK (length(body) BETWEEN 1 AND 5000),
    created_at  timestamptz NOT NULL DEFAULT now(),
    updated_at  timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX player_notes_owner_player_idx ON player_notes (owner_id, player_id);
CREATE INDEX shortlist_entries_player_idx ON shortlist_entries (player_id);
