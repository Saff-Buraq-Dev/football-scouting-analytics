-- Player archetypes (Phase 11.7, D030): types per position group and each player's nearest types.
CREATE TABLE archetypes (
    position_group  text NOT NULL,
    archetype_index integer NOT NULL,
    size            integer NOT NULL,
    more_features   text[] NOT NULL,
    less_features   text[] NOT NULL,
    prototypes      uuid[] NOT NULL,  -- player ids (with season below) closest to the centroid
    prototype_seasons uuid[] NOT NULL,
    PRIMARY KEY (position_group, archetype_index)
);

CREATE TABLE player_archetypes (
    player_id        uuid NOT NULL,
    season_id        uuid NOT NULL,
    position_group   text NOT NULL,
    archetype_index  integer NOT NULL,
    distance         double precision NOT NULL,
    second_index     integer,
    second_distance  double precision,
    PRIMARY KEY (player_id, season_id),
    FOREIGN KEY (player_id, season_id) REFERENCES player_seasons (player_id, season_id) ON DELETE CASCADE,
    FOREIGN KEY (position_group, archetype_index) REFERENCES archetypes (position_group, archetype_index)
);
