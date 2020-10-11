#!/bin/python3
# Author: Dino Bollinger
# Licensed under BSD 3-Clause License, see included LICENSE file
"""
Retrieves statistics on which tile indices have associated voxels, and outputs a pickled indicator numpy array.
"""

import sys
import re
import numpy as np
import pickle

# expected format:
# voxel <path> { scale 1 tile 18128 }

DEF_DIR = ""
if len(sys.argv) >= 2:
    DEF_DIR = sys.argv[1]
else:
    print("Must specify def file path as first argument!", file=sys.stderr)
    exit(1)

MAXTILES = -1
if len(sys.argv) >= 3:
    MAXTILES = int(sys.argv[2])
else:
    print("Must specify maxtiles as second argument (int)!", file=sys.stderr)
    exit(2)

voxel_tiles = np.zeros(MAXTILES)

with open(DEF_DIR, "r") as fd:
    for line in fd:
        if line.startswith("voxel"):
            match = re.match("\{.*\s*tile\s*([0-9])\s*.*}")
            tilenum = int(match.group(1))
            voxel_tiles[tilenum] = 1

outfile = "./voxel.pkl"

print(f"Number of voxel tiles: {np.count_nonzero(voxel_tiles)}")
with open(outfile, "wb") as fd:
    pickle.dump(voxel_tiles, fd, pickle.HIGHEST_PROTOCOL)
    print(f"Spawned tile array written to: '{outfile}'")
