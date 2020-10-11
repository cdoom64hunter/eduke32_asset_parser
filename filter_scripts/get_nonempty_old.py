#!/bin/python3
# Author: Dino Bollinger
# Licensed under BSD 3-Clause License, see included LICENSE file
"""
This script outputs a pickled numpy array indicating which indices are non-empty tiles.
"""

import os
import re
import sys
import pickle
import numpy as np

outfilename = "./non_empty.pkl"

MAXTILES:int = -1
if len(sys.argv) >= 2:
    MAXTILES = int(sys.argv[1])
else:
    print("Must specify maxtiles a first argument!", file=sys.stderr)
    exit(1)

indicator = np.zeros(MAXTILES)

tile_dir = "./tiles"
filename_prefix = "tile"
filename_suffix = ".PNG"

image_filenames = os.listdir(tile_dir)

for i in image_filenames:
    new_i = re.sub(filename_prefix, "", i)
    new_i = re.sub(filename_suffix, "", new_i)
    tile_num = int(new_i)
    indicator[tile_num] = 1

print(f"Total number of tiles in ART: {np.count_nonzero(indicator)}")
with open(outfilename, "wb") as fd:
    pickle.dump(indicator, fd, pickle.HIGHEST_PROTOCOL)
    print(f"Indicator array written to '{outfilename}'")
