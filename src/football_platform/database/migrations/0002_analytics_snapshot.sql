-- Analytics snapshot (decision D018): results of reports.player_season_report,
-- stored so the API reads them instead of recomputing from 5M events.
-- The computation stays in tested Python code; these tables only hold its output.
-- Each store replaces the current snapshot; analytics_runs keeps the history.

CREATE TABLE analytics_runs (
    id                  uuid PRIMARY KEY,
    created_at          timestamptz NOT NULL DEFAULT now(),
    min_minutes         double precision NOT NULL,
    population_seasons  uuid[] NOT NULL,
    source_provider     text NOT NULL,
    row_count           integer NOT NULL
);

CREATE TABLE player_seasons (
    player_id            uuid NOT NULL REFERENCES players (id),
    season_id            uuid NOT NULL REFERENCES seasons (id),
    analytics_run_id     uuid NOT NULL REFERENCES analytics_runs (id),
    team_ids             uuid[] NOT NULL,
    minutes              double precision NOT NULL CHECK (minutes > 0),
    appearances          integer NOT NULL,
    starts               integer NOT NULL,
    primary_role         text CHECK (primary_role IN ('GK', 'CB', 'FB', 'WB', 'DM', 'CM', 'WM', 'AM', 'W', 'CF')),
    primary_role_share   double precision,
    position_group       text CHECK (position_group IN (
                             'goalkeeper', 'centre_back', 'full_back', 'central_midfield',
                             'attacking_midfield_winger', 'striker')),
    team_possession_pct  double precision,
    eligible             boolean NOT NULL,
    population_size      integer,
    PRIMARY KEY (player_id, season_id)
);
CREATE INDEX player_seasons_group_idx ON player_seasons (season_id, position_group);

CREATE TABLE player_season_metrics (
    player_id    uuid NOT NULL,
    season_id    uuid NOT NULL,
    metric_key   text NOT NULL,
    total        double precision,  -- season total (counts) or numerator (ratios)
    value        double precision,  -- per 90 (counts) or ratio
    percentile   double precision CHECK (percentile BETWEEN 0 AND 100),
    regressed    double precision,  -- regressed per-90 estimate (counts only)
    reliability  double precision CHECK (reliability BETWEEN 0 AND 1),
    PRIMARY KEY (player_id, season_id, metric_key),
    FOREIGN KEY (player_id, season_id) REFERENCES player_seasons (player_id, season_id) ON DELETE CASCADE
);
CREATE INDEX player_season_metrics_metric_idx ON player_season_metrics (metric_key, season_id);
