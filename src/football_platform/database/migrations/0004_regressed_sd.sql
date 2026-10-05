-- Posterior standard deviation of the regressed per-90 estimate (Phase 6, decision D019).
-- Used to tell real differences between players from noise.
ALTER TABLE player_season_metrics
    ADD COLUMN regressed_sd double precision CHECK (regressed_sd >= 0);
