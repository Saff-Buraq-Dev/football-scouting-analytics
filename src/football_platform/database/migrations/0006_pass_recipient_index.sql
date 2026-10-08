-- Passes received by a player (reception zone maps, Phase 11.2).
CREATE INDEX events_pass_recipient_idx ON events (pass_recipient_id) WHERE pass_recipient_id IS NOT NULL;
