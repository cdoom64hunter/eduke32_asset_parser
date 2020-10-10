DROP TABLE IF EXISTS <REPLACE_MAPNAME>_sounds;

CREATE TABLE <REPLACE_MAPNAME>_sounds (
    id SMALLINT PRIMARY KEY,    -- sound id
    total INTEGER               -- total usages for this sound
    -- TODO: add common entries -- but will need to alter table as the entries here can vary greatly
);
