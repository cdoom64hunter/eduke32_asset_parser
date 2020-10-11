#!/bin/python3
# Author: Dino Bollinger
# Licensed under BSD 3-Clause License, see included LICENSE file
"""
Parse extracted CON command instances to retrieve indicator arrays for use in filtering Duke3D tiles.
This is a static analysis script and hence make use of the values stored in gamevars. Only constants and names are counted, the rest is filtered.
This python script relies on the output of the `get_con_instances.sh` bash script.
----------------------------------------------------------------------------------------
The following arrays are constructed, and output as pickle files:
 > actor tile array: binary numpy array which marks every tile that is defined as an actor.
 > spawned tile array: binary numpy array which marks each tile that is either spawned or created using cactor.
 > projectile array: binary numpy array, marks every tile defined as a projectile
 > screen tile array: binary numpy array, marks every tile referenced by the rotatesprite/myospal commands, used to display sprites in the HUD
----------------------------------------------------------------------------------------
The size of each array can be defined by the user using the first input argument.
Tilenums that exceed the size of the array, or which are otherwise malformed (e.g. negative indices) will be printed to stderr.
----------------------------------------------------------------------------------------
Usage: parse_con_instances.py <maxtiles>
"""
import sys
import re
import os
import numpy as np
import pickle

MAXTILES=-1
if len(sys.argv) >= 2:
    MAXTILES = int(sys.argv[1])
else:
    print("Must specify maxtiles a first argument!", file=sys.stderr)
    exit(1)

defined_names = dict()
defined_vars = set()

actor_tiles = np.zeros(MAXTILES)
spawned_tiles = np.zeros(MAXTILES)
projectiles = np.zeros(MAXTILES)
screen_tiles = np.zeros(MAXTILES)


def get_tilenum_for_name(name, line=None):
    """
    Lookup tilenum for given tile name based on the defined_names dictionary.
    :param name: tile name
    :param line: if specified, will print this line if name is not found
    :return: tile number as integer
    """
    tilenum = None
    try:
        if name.startswith("0x"): tilenum = int(name, 16)
        else: tilenum = int(name)
    except ValueError:
        try:
            tilenum = defined_names[name]
        except KeyError:
            if line != None: print(f"Name '{name}' is unknown:: {line.strip()}", file=sys.stderr)
            else: print(f"Name '{name}' is unknown.")

    return tilenum


def clean_line(line):
    """
    Preprocess the line such that it can be parsed without false positives.
    :param line: line to clean
    :return:cleaned line
    """
    cleaned_line = line.strip()
    cleaned_line = re.sub("^.*\.CON:[0-9]*:", "", cleaned_line) # remove line indicator
    cleaned_line = re.sub("//.*$", "", cleaned_line) # remove comments

    # remove quote strings because they can contain tokens that can screw up stuff
    cleaned_line = re.sub("qputs.*$", "", cleaned_line)
    cleaned_line = re.sub("definequote.*$", "", cleaned_line)
    cleaned_line = cleaned_line.strip()
    return cleaned_line


def main():
    """
    Parse the outputs of the bash script and output pickled numpy indicator arrays.
    """
    # Load name definitions for lookup purposes
    with open("./statistics/defs.txt", "r") as fd:
        for line in fd:
            tokens = (line.strip()).split()
            try:
                if tokens[2] == "YES": new_value = 1
                elif tokens[2] == "NO": new_value = 0
                elif tokens[2].startswith("0x"): new_value = int(tokens[2], 16)
                else: new_value = int(tokens[2])

                defined_names[tokens[1]] = new_value
            except ValueError:
                print(f"Non integer define: {line.strip()}", file=sys.stderr)

    # Load var definitions to filter variables, prevent unnecessary error messages
    with open("./statistics/vars.txt", "r") as fd:
        for line in fd:
            tokens = (line.strip()).split()
            defined_vars.add(tokens[1])


    # Collect actor tile information
    with open("./statistics/actor_instances.txt", "r") as fd:
        for line in fd:
            cleaned_line = clean_line(line)
            tokens = cleaned_line.split()
            s = tokens.index("actor")
            name = tokens[s+1]

            tilenum = get_tilenum_for_name(name, cleaned_line)

            if tilenum is not None:
                actor_tiles[tilenum] = 1


    # Collect useractor tile information
    with open("./statistics/useractor_instances.txt", "r") as fd:
        for line in fd:
            cleaned_line = clean_line(line)
            tokens = cleaned_line.split()
            s = tokens.index("useractor")
            name = tokens[s+2]

            tilenum = get_tilenum_for_name(name, cleaned_line)

            if tilenum is not None:
                actor_tiles[tilenum] = 1


    # Collect spawn instance information
    with open("./statistics/spawn_instances.txt", "r") as fd:
        for line in fd:
            cleaned_line = clean_line(line)
            cleaned_line = re.sub("eqspawn", "spawn", cleaned_line)
            cleaned_line = re.sub("qspawn", "spawn", cleaned_line)
            cleaned_line = re.sub("espawn", "spawn", cleaned_line)
            cleaned_line = re.sub("spawnvar", "spawn", cleaned_line)
            tokens = cleaned_line.split()
            stopiter = False
            s = -1
            while not stopiter:
                s += 1
                try:
                    s = tokens.index("spawn", s)
                except ValueError:
                    stopiter = True
                    continue

                name = tokens[s + 1]
                name = re.sub("\\[[0-9]+\\]", "", name)  # remove potential array index
                if name not in defined_vars:

                    tilenum = get_tilenum_for_name(name, cleaned_line)

                    if tilenum is not None:
                        spawned_tiles[tilenum] = 1


    # collect changeactor instances
    with open("./statistics/cactor_lines.txt", "r") as fd:
        for line in fd:
            cleaned_line = clean_line(line)

            tokens = cleaned_line.split()
            stopiter = False
            s = -1
            while not stopiter:
                s += 1
                try:
                    s = tokens.index("cactor", s)
                except ValueError:
                    stopiter = True
                    continue

                name = tokens[s+1]
                name = re.sub("\\[[0-9]+\\]", "", name)  # remove potential array index
                if name not in defined_vars:
                    tilenum = get_tilenum_for_name(name, cleaned_line)

                    if tilenum is not None:
                        spawned_tiles[tilenum] = 1


    # collect projectile definitions
    with open("./statistics/projectile_instances.txt", "r") as fd:
        for line in fd:
            cleaned_line = clean_line(line)

            tokens = cleaned_line.split()
            stopiter = False
            s = -1
            while not stopiter:
                s += 1
                try:
                    s = tokens.index("defineprojectile", s)
                except ValueError:
                    stopiter = True
                    continue

                name = tokens[s+1]
                name = re.sub("\\[[0-9]+\\]", "", name)  # remove potential array index
                if name not in defined_vars:
                    tilenum = get_tilenum_for_name(name, cleaned_line)

                    if tilenum is not None:
                        projectiles[tilenum] = 1


    # collect screen tiles
    with open("./statistics/myospal.txt", "r") as fd:
        for line in fd:
            cleaned_line = clean_line(line)

            tokens = cleaned_line.split()

            s = -1
            while True:
                s += 1
                try:
                    s = tokens.index("myospal", s)
                except ValueError:
                    break

                name = tokens[s+3]
                name = re.sub("\\[[0-9]+\\]", "", name)  # remove potential array index
                if name not in defined_vars:
                    tilenum = get_tilenum_for_name(name, cleaned_line)

                    if tilenum is not None:
                        screen_tiles[tilenum] = 1

            s = -1
            while True:
                s += 1
                try:
                    s = tokens.index("myospalx", s)
                except ValueError:
                    break

                name = tokens[s+3]
                name = re.sub("\\[[0-9]+\\]", "", name)  # remove potential array index
                if name not in defined_vars:
                    tilenum = get_tilenum_for_name(name, cleaned_line)

                    if tilenum is not None:
                        screen_tiles[tilenum] = 1


    # more screen tiles
    with open("./statistics/rotatesprite.txt", "r") as fd:
        for line in fd:
            cleaned_line = clean_line(line)

            tokens = cleaned_line.split()

            s = -1
            while True:
                s += 1
                try:
                    s = tokens.index("rotatesprite", s)
                except ValueError:
                    break

                name = tokens[s+5]
                name = re.sub("\\[[0-9]+\\]", "", name)  # remove potential array index
                if name not in defined_vars:
                    tilenum = get_tilenum_for_name(name, cleaned_line)

                    if tilenum is not None:
                        screen_tiles[tilenum] = 1

            s = -1
            while True:
                s += 1
                try:
                    s = tokens.index("rotatespritea", s)
                except ValueError:
                    break

                name = tokens[s+5]
                name = re.sub("\\[[0-9]+\\]", "", name) # remove potential array index
                if name not in defined_vars:
                    tilenum = get_tilenum_for_name(name, cleaned_line)

                    if tilenum is not None:
                        screen_tiles[tilenum] = 1

    os.makedirs("./pickled_stats/", exist_ok=True)

    # dump the collected stats into pickled numpy arrays on disk
    outfile1 = "./pickled_stats/actor_tile_array.pkl"
    outfile2 = "./pickled_stats/spawned_tile_array.pkl"
    outfile3 = "./pickled_stats/projectiles_array.pkl"
    outfile4 = "./pickled_stats/screen_tiles.pkl"

    print(f"Number of distinct actor tiles: {np.count_nonzero(actor_tiles)}")
    with open(outfile1, "wb") as fd:
        pickle.dump(actor_tiles, fd, pickle.HIGHEST_PROTOCOL)
        print(f"Actor tile array written to: '{outfile1}'")

    print(f"Number of distinct spawned tiles: {np.count_nonzero(spawned_tiles)}")
    with open(outfile2, "wb") as fd:
        pickle.dump(spawned_tiles, fd, pickle.HIGHEST_PROTOCOL)
        print(f"Spawned tile array written to: '{outfile2}'")

    print(f"Number of projectiles: {np.count_nonzero(projectiles)}")
    with open(outfile3, "wb") as fd:
        pickle.dump(projectiles, fd, pickle.HIGHEST_PROTOCOL)
        print(f"Spawned tile array written to: '{outfile3}'")

    print(f"Number of screen tiles: {np.count_nonzero(screen_tiles)}")
    with open(outfile4, "wb") as fd:
        pickle.dump(screen_tiles, fd, pickle.HIGHEST_PROTOCOL)
        print(f"Spawned tile array written to: '{outfile4}'")

    return 0


if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)