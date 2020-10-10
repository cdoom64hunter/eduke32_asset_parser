DROP TABLE IF EXISTS <REPLACE_MAPNAME>_tiles;

CREATE TABLE <REPLACE_MAPNAME>_tiles (
    id SMALLINT PRIMARY KEY,    -- tilenum
    sprite INTEGER NOT NULL,    -- number of instances as sprite
    floor INTEGER NOT NULL,     -- number of instances as floor texture
    ceiling INTEGER NOT NULL,   -- number of instances as ceiling texture
    wall INTEGER NOT NULL,      -- number of instances as solid wall texture
    overwall INTEGER NOT NULL,  -- number of instances as thin wall texture
    total INTEGER NOT NULL     -- total usage count
    -- the following will be added dynamically
    -- spawned BIT,         -- whether the tile was spawned by a CON script
    -- actor BIT,           -- whether the tile is part of an actor
    -- hardcoded BIT,       -- whether the tile is used in the engine
    -- empty BIT,           -- whether the tile is empty
    -- cactor BIT,          -- whether the tile is used for cactor
    -- projectile BIT,      -- whether the tile is a projectile
    -- animation BIT,       -- whether the tile is part of an animation
    -- screentile BIT,      -- whether the tile is used as part of the HUD
    -- voxel BIT,           -- whether the tile is defined as a voxel
    -- tilefromtexture BIT  -- whether the tile is sourced from a folder
);