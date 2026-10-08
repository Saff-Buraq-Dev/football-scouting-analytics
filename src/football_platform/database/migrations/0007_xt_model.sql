-- Fitted Expected Threat surfaces (Phase 11.1, D025). Stored by the player report so the API can
-- value actions of a single match without refitting on millions of events.
CREATE TABLE xt_models (
    id          uuid PRIMARY KEY,
    created_at  timestamptz NOT NULL DEFAULT now(),
    grid_columns integer NOT NULL CHECK (grid_columns > 0),
    grid_rows    integer NOT NULL CHECK (grid_rows > 0),
    cell_values  double precision[] NOT NULL,
    actions      integer NOT NULL,
    iterations   integer NOT NULL,
    CHECK (cardinality(cell_values) = grid_columns * grid_rows)
);
