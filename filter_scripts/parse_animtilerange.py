#!/bin/python3
# Author: Dino Bollinger
# Licensed under BSD 3-Clause License, see included LICENSE file
"""
  To make use of this script, it is recommended to utilize
  mapster32 and BAFed to construct a DEF file containing all animtileranges.

  This is done by first dumping a single ART file containing all tiles using mapster32
  with the `artdump` console command, and then using BAFed to dump a DEF file for all tiles.
  This script then parses the contents of the DEF file structure,
  to report animtile ranges, and non-empty tile slots.

  It can also be used to determine which tiles are used as tilefromtexture normally.
  Results are dumped as pickled numpy arrays.
  """

import sys
import numpy as np
import pickle

# format:
# tilefromtexture 12007 { file "12007.png" xoffset 0 yoffset 0 ifcrc -460055260 }
# animtilerange 12007 12010 3 2

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

nonempty_tiles = np.zeros(MAXTILES)
animtiles = np.zeros(MAXTILES)

with open(DEF_DIR, "r") as fd:
    for line in fd:
        if line.startswith("tilefromtexture"):
            tilenum = int(line.strip().split()[1])
            nonempty_tiles[tilenum] = 1

        elif line.startswith("animtilerange"):

            start = int(line.strip().split()[1])
            end = int(line.strip().split()[2]) + 1
            animtiles[start:end] = 1

outfile1 = "nonempty.pkl"
outfile2 = "animation.pkl"

print(f"Number of nonempty tiles: {np.count_nonzero(nonempty_tiles)}")
with open(outfile1, "wb") as fd:
    pickle.dump(nonempty_tiles, fd, pickle.HIGHEST_PROTOCOL)
    print(f"Spawned tile array written to: '{outfile1}'")

print(f"Number of animated tiles: {np.count_nonzero(animtiles)}")
with open(outfile2, "wb") as fd:
    pickle.dump(animtiles, fd, pickle.HIGHEST_PROTOCOL)
    print(f"Spawned tile array written to: '{outfile2}'")

