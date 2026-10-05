-- Canonical football data model v1.1 (docs/ARCHITECTURE.md §5, decisions D012, D015).
-- Mirrors the canonical Parquet tables. No analytics here: metrics live in code.
-- Enumerations are TEXT + CHECK (easier to evolve than PostgreSQL ENUM types);
-- tests/database/test_schema_enums.py keeps them in sync with canonical/enums.py.

CREATE TABLE ingestion_runs (
    id              uuid PRIMARY KEY,
    provider        text NOT NULL,
    source_release  text NOT NULL,
    started_utc     timestamptz NOT NULL,
    finished_utc    timestamptz NOT NULL,
    manifest        jsonb NOT NULL,
    loaded_at       timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE competitions (
    id                uuid PRIMARY KEY,
    name              text NOT NULL,
    area              text NOT NULL,
    gender            text NOT NULL CHECK (gender IN ('male', 'female')),
    competition_type  text NOT NULL CHECK (competition_type IN ('league', 'cup', 'international_tournament')),
    is_youth          boolean,
    tier              integer
);

CREATE TABLE seasons (
    id                 uuid PRIMARY KEY,
    competition_id     uuid NOT NULL REFERENCES competitions (id),
    label              text NOT NULL,
    coverage_scope     text NOT NULL CHECK (coverage_scope IN ('complete', 'partial', 'unknown')),
    has_events         boolean NOT NULL,
    has_lineups        boolean NOT NULL,
    has_freeze_frames  boolean NOT NULL,
    coverage_note      text,
    start_date         date,
    end_date           date
);

CREATE TABLE teams (
    id          uuid PRIMARY KEY,
    name        text NOT NULL,
    team_type   text NOT NULL CHECK (team_type IN ('club', 'national')),
    gender      text NOT NULL CHECK (gender IN ('male', 'female')),
    area        text,
    short_name  text
);

CREATE TABLE players (
    id              uuid PRIMARY KEY,
    name            text NOT NULL,
    known_name      text,
    nationality     text,
    birth_date      date,
    height_cm       double precision,
    preferred_foot  text
);

CREATE TABLE matches (
    id              uuid PRIMARY KEY,
    season_id       uuid NOT NULL REFERENCES seasons (id),
    competition_id  uuid NOT NULL REFERENCES competitions (id),
    match_date      date NOT NULL,
    home_team_id    uuid NOT NULL REFERENCES teams (id),
    away_team_id    uuid NOT NULL REFERENCES teams (id),
    home_score      integer NOT NULL CHECK (home_score >= 0),
    away_score      integer NOT NULL CHECK (away_score >= 0),
    status          text NOT NULL CHECK (status IN ('played', 'scheduled', 'abandoned')),
    kickoff_time    time,  -- local time as given by the source
    stage           text,
    matchweek       integer,
    venue           text,
    referee         text,
    CHECK (home_team_id <> away_team_id)
);
CREATE INDEX matches_season_idx ON matches (season_id);

CREATE TABLE appearances (
    match_id        uuid NOT NULL REFERENCES matches (id) ON DELETE CASCADE,
    team_id         uuid NOT NULL REFERENCES teams (id),
    player_id       uuid NOT NULL REFERENCES players (id),
    is_starter      boolean NOT NULL,
    shirt_number    integer,
    minutes_played  double precision NOT NULL CHECK (minutes_played >= 0),
    PRIMARY KEY (match_id, player_id)
);
CREATE INDEX appearances_player_idx ON appearances (player_id);

CREATE TABLE position_spells (
    id         bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    match_id   uuid NOT NULL,
    team_id    uuid NOT NULL REFERENCES teams (id),
    player_id  uuid NOT NULL,
    period     smallint NOT NULL CHECK (period BETWEEN 1 AND 5),
    start_s    double precision NOT NULL CHECK (start_s >= 0),
    end_s      double precision NOT NULL,
    line       text NOT NULL CHECK (line IN ('GK', 'DEF', 'MID', 'FWD')),
    role       text CHECK (role IN ('GK', 'CB', 'FB', 'WB', 'DM', 'CM', 'WM', 'AM', 'W', 'CF')),
    side       text CHECK (side IN ('L', 'C', 'R')),
    CHECK (end_s >= start_s),
    FOREIGN KEY (match_id, player_id) REFERENCES appearances (match_id, player_id) ON DELETE CASCADE
);
CREATE INDEX position_spells_player_idx ON position_spells (player_id);
CREATE INDEX position_spells_match_idx ON position_spells (match_id);

CREATE TABLE events (
    id                           uuid PRIMARY KEY,
    match_id                     uuid NOT NULL REFERENCES matches (id) ON DELETE CASCADE,
    period                       smallint NOT NULL CHECK (period BETWEEN 1 AND 5),
    time_s                       double precision NOT NULL CHECK (time_s >= 0),
    team_id                      uuid NOT NULL REFERENCES teams (id),
    player_id                    uuid REFERENCES players (id),
    type                         text NOT NULL CHECK (type IN (
                                     'pass', 'shot', 'own_goal', 'carry', 'ball_receipt', 'pressure',
                                     'take_on', 'dribbled_past', 'duel', 'interception', 'clearance',
                                     'block', 'ball_recovery', 'miscontrol', 'dispossessed',
                                     'foul_committed', 'foul_won', 'goalkeeper_action', 'card',
                                     'substitution', 'period_start', 'period_end', 'other')),
    outcome                      text NOT NULL CHECK (outcome IN ('success', 'fail', 'unknown', 'not_applicable')),
    -- Canonical metres on a 105 x 68 pitch, acting team attacking towards x = 105 (D005).
    start_x                      double precision CHECK (start_x BETWEEN 0 AND 105),
    start_y                      double precision CHECK (start_y BETWEEN 0 AND 68),
    end_x                        double precision CHECK (end_x BETWEEN 0 AND 105),
    end_y                        double precision CHECK (end_y BETWEEN 0 AND 68),
    body_part                    text CHECK (body_part IN ('foot_left', 'foot_right', 'head', 'hands', 'other')),
    set_piece                    text CHECK (set_piece IN ('corner', 'free_kick', 'throw_in', 'penalty', 'goal_kick', 'kick_off')),
    possession_origin            text CHECK (possession_origin IN (
                                     'regular_play', 'throw_in', 'free_kick', 'goal_kick', 'kick_off',
                                     'corner', 'keeper', 'counter', 'other')),
    possession_id                text,
    duel_kind                    text CHECK (duel_kind IN ('ground', 'aerial', 'loose_ball')),
    aerial_won                   boolean,
    under_pressure               boolean,
    related_event_ids            uuid[] NOT NULL DEFAULT '{}',
    pass_height                  text CHECK (pass_height IN ('ground', 'low', 'high')),
    pass_recipient_id            uuid REFERENCES players (id),
    pass_is_cross                boolean,
    pass_is_switch               boolean,
    pass_is_cut_back             boolean,
    pass_is_through_ball         boolean,
    pass_is_shot_assist          boolean,
    pass_is_goal_assist          boolean,
    pass_assisted_shot_event_id  uuid,  -- no FK: links within the same match, kept as provided
    shot_outcome                 text CHECK (shot_outcome IN ('goal', 'saved', 'blocked', 'off_target', 'post', 'wayward')),
    shot_technique               text,
    shot_is_first_time           boolean,
    shot_key_pass_event_id       uuid,  -- no FK, see above
    shot_end_z                   double precision,
    goalkeeper_action_kind       text CHECK (goalkeeper_action_kind IN (
                                     'shot_faced', 'save', 'goal_conceded', 'claim', 'punch', 'sweeper',
                                     'smother', 'other')),
    card_type                    text CHECK (card_type IN ('yellow', 'second_yellow', 'red')),
    substitute_player_id         uuid REFERENCES players (id),
    provider_event_type          text,
    provider_qualifiers          jsonb,
    source_provider              text NOT NULL,
    source_record_id             text NOT NULL,
    source_release               text NOT NULL,
    ingestion_run_id             uuid NOT NULL REFERENCES ingestion_runs (id),
    CHECK (type <> 'duel' OR duel_kind IS NOT NULL),
    CHECK (type <> 'shot' OR shot_outcome IS NOT NULL),
    CHECK (type <> 'card' OR card_type IS NOT NULL)
);
CREATE INDEX events_match_idx ON events (match_id);
CREATE INDEX events_player_type_idx ON events (player_id, type) WHERE player_id IS NOT NULL;

-- Provider model outputs (xG...), source-tagged and never substituted (D007).
CREATE TABLE provider_metrics (
    event_id         uuid NOT NULL REFERENCES events (id) ON DELETE CASCADE,
    match_id         uuid NOT NULL REFERENCES matches (id) ON DELETE CASCADE,
    metric_key       text NOT NULL,
    value            double precision NOT NULL,
    source_provider  text NOT NULL,
    model_version    text NOT NULL,
    PRIMARY KEY (event_id, metric_key, source_provider, model_version)
);
CREATE INDEX provider_metrics_match_idx ON provider_metrics (match_id);

-- Link between internal ids and provider ids (D006).
CREATE TABLE external_ids (
    entity_type  text NOT NULL CHECK (entity_type IN ('competition', 'season', 'team', 'player', 'match', 'event')),
    internal_id  uuid NOT NULL,
    provider     text NOT NULL,
    provider_id  text NOT NULL,
    PRIMARY KEY (provider, entity_type, provider_id),
    UNIQUE (entity_type, internal_id, provider)
);
