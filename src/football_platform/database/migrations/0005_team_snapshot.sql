-- Team-season analytics snapshot (Phase 8, decision D021). Computed by
-- reports.team_season_report; each store replaces the previous snapshot.

CREATE TABLE team_seasons (
    team_id        uuid NOT NULL REFERENCES teams (id),
    season_id      uuid NOT NULL REFERENCES seasons (id),
    matches        integer NOT NULL CHECK (matches > 0),
    points         integer NOT NULL,
    goals_for      integer NOT NULL,
    goals_against  integer NOT NULL,
    league_size    integer,
    computed_at    timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (team_id, season_id)
);

CREATE TABLE team_season_metrics (
    team_id     uuid NOT NULL,
    season_id   uuid NOT NULL,
    metric_key  text NOT NULL,
    value       double precision,  -- NULL = unavailable from the source
    percentile  double precision CHECK (percentile BETWEEN 0 AND 100),  -- within the league-season
    PRIMARY KEY (team_id, season_id, metric_key),
    FOREIGN KEY (team_id, season_id) REFERENCES team_seasons (team_id, season_id) ON DELETE CASCADE
);
