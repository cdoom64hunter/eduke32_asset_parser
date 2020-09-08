#!/bin/python3
# Author: Dino Bollinger
# Licensed under BSD 3-Clause License, see included LICENSE file

""" Mapster32 Asset Count Parser
Parses and aggregates the statistics as output by the `dump_used_assets.m32` script in verbose mode.
Said script is part of the eduke32 package, and can be found in the main eduke32 repository.
------------------------------------------------------------------------------------------
Usage: asset_parser.py <logfile> [--maxtiles <max>] (--format (excel|csv))
       asset_parser.py --help
       asset_parser.py --version
Options:
    --maxtiles -m    Defines the maximum expected tilenum. (Default: 8192)
    --format -f      Use either "excel" or "csv" output format.
"""

import sys
import os
import re
import argparse
import pandas as pd
import numpy as np

from typing import Dict, List, Tuple

__version__ = "1.01"

# Indicates the start of a map in the log. Comes in several variations depending on version and corruption.
mapload_pattern = "Loaded V[0-9]+ map (.*) (successfully|\(EXTREME corruption\)|\(HEAVY corruption\)|\(moderate corruption\)|\(removed [0-9]+ sprites\)).*"

# Indicate the start and end of the tile search of dump_used_assets.m32
tile_start = "Searching for tiles used in current map..."
tile_end = "Tile search finished."

# Indicate the start and end of the sound search of dump_used_assets.m32
sound_start = "Searching for sounds used in current map..."
sound_end = "Sound search finished."


def parse_log(logpath: str) -> Tuple[Dict[str, List[str]], Dict[str, List[str]]]:
    """
    Parse the mapster32.log for asset information as output by dump_used_assets.m32.
    Make sure that the variable "verbose" is set to 1 inside mapster32!
    :param logpath: log file from which to read the dump
    :return Two dicts containing per-map tile and sound statistics respectively.
    """
    tiles_per_map = dict()
    sounds_per_map = dict()

    curr_map = None
    with open(logpath, 'r', encoding="utf8") as fd:
        try:
            while True:
                line = next(fd).strip()
                match = re.match(mapload_pattern, line)
                if match:
                    curr_map = match.group(1)
                    tiles_per_map[curr_map] = list()
                    sounds_per_map[curr_map] = list()
                elif line.startswith(tile_start):
                    line = next(fd)
                    while not line.startswith(tile_end):
                        tiles_per_map[curr_map].append(line.strip())
                        line = next(fd)
                elif line.startswith(sound_start):
                    line = next(fd)
                    while not line.startswith(sound_end):
                        sounds_per_map[curr_map].append(line.strip())
                        line = next(fd)
        except StopIteration:
            print("Statistics parsed from log file")

    return tiles_per_map, sounds_per_map


def aggregate_tilestats(tpm: Dict[str, List[str]], maxtiles: int, skip_overwall0: bool = True):
    """
    Takes as argument a dict of tile stats per level, and sums them.
    This also produces totals per map, and a total over all maps given as input.
    Hereby it is assumed that there exists one line per sprite, floor, ceiling wall and overwall.
    :param tpm: A dictionary of tile stats. Each dictionary key is a map filename which
                is assumed to contain a list of stats as output by dump_used_assets.m32 in verbose mode.
    :param maxtiles: Maximum expected tilenum. This determines the size of the resulting columns.
                Tilenums that exceed the expected maximum will be
    :param skip_overwall0: Tile 0 is used by default for all overwalls that are transparent.
                Set to false to count these as well.
    :return: Tuple: (tile_stats, reject_stats)
            tile_stats: Dict of aggregates stats for each map. Each dict entry is a dict with the following keys:
            {"sprite", "floor", "ceiling", "wall", "overwall", "total"}
             Each entry for these keys is a numpy array of `maxtiles` entries, storing the number of times the respective tile is used.
             reject_stats: Dict of rejected tile lines (negative or too large tilenum)
    """

    tile_stats: Dict[str, Dict[str, np.ndarray]] = dict()
    reject_stats: Dict[str, List[str]] = dict()
    for map_filename in tpm.keys():

        # use numpy arrays for correct tiles
        newstats = {"sprite": np.zeros(maxtiles), "floor": np.zeros(maxtiles), "ceiling": np.zeros(maxtiles),
                    "wall": np.zeros(maxtiles), "overwall": np.zeros(maxtiles)}

        # rejected entries
        newreject = []

        for line in tpm[map_filename]:
            k = line.split(sep=',')
            ttype = k[0]
            tidx = int(k[1])

            if tidx >= maxtiles:
                print(f"WARNING: Tile index {tidx} in map {map_filename} exceeds MAXTILES of {maxtiles}::{line}", file=sys.stderr)
                newreject.append(line)
            elif tidx < 0:
                print(f"WARNING: Negative picnum {tidx} found in map {map_filename}::{line}", file=sys.stderr)
                newreject.append(line)
            else:
                newstats[ttype][tidx] += 1

        # overpicnum == 0 is transparent; don't count
        if skip_overwall0:
            newstats["overwall"][0] = 0

        # aggregate total column for each map
        maptotal = np.zeros(maxtiles)
        for cat in newstats.keys():
            maptotal += newstats[cat]
        newstats["TOTAL"] = maptotal

        tile_stats[map_filename] = newstats
        reject_stats[map_filename] = newreject

    # aggregate total over all maps
    if len(tile_stats.keys()) > 1:
        allmaptotal = {"sprite": np.zeros(maxtiles), "floor": np.zeros(maxtiles), "ceiling": np.zeros(maxtiles),
                       "wall": np.zeros(maxtiles), "overwall": np.zeros(maxtiles), "TOTAL": np.zeros(maxtiles)}

        for k in tile_stats.keys():
            for cat in tile_stats[k].keys():
                allmaptotal[cat] += tile_stats[k][cat]

        tile_stats["TOTAL"] = allmaptotal

    return tile_stats, reject_stats


def aggregate_soundstats(spm: Dict[str, List[str]], maxsounds: int = 16384):
    """
    Takes as argument a dict of sound stats per level, and computes the aggregate sum.
    :param spm: Dict of sound stats per map, stored as lines of strings. (emitter,  soundnum)
    :param maxsounds: Maximum sound index. Does not determine column size in this case!
            Column size is instead determined by the maximum sound index found in the log.
    :return: (sound_stats, reject_stats)
            sound_stats: dict of dicts, storing number of times sounds are used per emitter type
            reject_stats: negative
    """
    sound_stats = dict()
    reject_stats = dict()

    for map_filename in spm.keys():
        sound_by_emitter = dict()
        newreject = []

        for line in spm[map_filename]:
            k = line.split(sep=',')
            stype = k[0]
            sidx = int(k[1])

            if sidx < 0:
                print(f"WARNING: Negative sound index {sidx} found in map {map_filename}::{line}", file=sys.stderr)
                newreject.append(line)
            elif sidx > maxsounds:
                print(f"WARNING: Sound index {sidx} in map {map_filename} exceeds maxsounds of {maxsounds}::{line}", file=sys.stderr)
                newreject.append(line)
            else:
                # If emitter is not known yet, create dict for it
                if stype not in sound_by_emitter:
                    sound_by_emitter[stype] = dict()

                # If index unknown, add to dict
                if sidx not in sound_by_emitter[stype]:
                    sound_by_emitter[stype][sidx] = 0

                sound_by_emitter[stype][sidx] += 1

        sound_stats[map_filename] = sound_by_emitter
        reject_stats[map_filename] = newreject

    # after stats are collected, reformat into numpy arrays and compute totals
    new_sound_dict = dict()
    for k in sound_stats.keys():
        new_sound_dict[k] = dict()
        emitters = sound_stats[k].keys()  # emitters

        map_maxsound = 0
        for e in emitters:
            emitter_max = max(sound_stats[k][e].keys())
            if emitter_max > map_maxsound:
                map_maxsound = emitter_max

        total_stats = np.zeros(map_maxsound + 1)
        for e in emitters:
            stat_array = np.zeros(map_maxsound + 1)
            for index, count in sound_stats[k][e].items():
                stat_array[index] = count
            new_sound_dict[k][e] = stat_array
            total_stats += stat_array

        new_sound_dict[k]["TOTAL"] = total_stats

    # aggregate total over all maps
    if len(new_sound_dict.keys()) > 1:
        allmaptotal = dict()
        max_len = 0
        for k in new_sound_dict.keys():
            for cat in new_sound_dict[k].keys():
                if cat not in allmaptotal:
                    allmaptotal[cat] = np.zeros(new_sound_dict[k][cat].shape)
                if len(new_sound_dict[k][cat]) > len(allmaptotal[cat]):
                    allmaptotal[cat].resize(new_sound_dict[k][cat].shape)

                allmaptotal[cat] += np.resize(new_sound_dict[k][cat], allmaptotal[cat].shape)
                if allmaptotal[cat].shape[0] > max_len:
                    max_len = allmaptotal[cat].shape[0]

        for cat in allmaptotal:
            allmaptotal[cat].resize((max_len,))

        new_sound_dict["TOTAL"] = allmaptotal

    return new_sound_dict, reject_stats



def export_stats_to_csv(stat_dict: dict, outfile_prefix: str) -> None:
    """
    Export the given stats dictionary to csv.
    :param stat_dict: Dictionary containing the collected statistics
    :param outfile_prefix: Filename prefix
    """
    outdir = "./csv_out"
    if not os.path.exists(outdir):
        os.mkdir(outdir, mode=0o755)

    for k in stat_dict.keys():
        ts_dataframe = pd.DataFrame(stat_dict[k])

        #TODO: add additional mark columns for filtering

        # ensure this column is placed last
        total_col = ts_dataframe.pop("TOTAL")
        ts_dataframe.insert(len(ts_dataframe.columns), "TOTAL", total_col)

        mapname = re.sub('(\.MAP$|\.map$)', '', re.sub('.*/', '', k))
        ts_dataframe.to_csv(f"{outdir}/{outfile_prefix}_{mapname}.csv", sep=',', na_rep="N/A", float_format="%d")


def export_stats_to_excel(stat_dict:dict, outfile_prefix:str) -> None:
    """
    Export the given stats dictionary to excel format.
    :param stat_dict:
    :param outfile_prefix:
    :return:
    """
    writer = pd.ExcelWriter(outfile_prefix +".xlsx", engine='xlsxwriter')

    for k in stat_dict.keys():
        ts_dataframe = pd.DataFrame(stat_dict[k])

        #TODO: add additional mark columns for filtering

        # ensure this column is placed last
        total_col = ts_dataframe.pop("TOTAL")
        ts_dataframe.insert(len(ts_dataframe.columns), "TOTAL", total_col)

        mapname = re.sub('.*/', '', k)
        ts_dataframe.to_excel(writer, sheet_name=f"{mapname}", na_rep="N/A")

    writer.save()
    writer.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("logfile", nargs="?", type=str, help="Logfile as output by dump_used_assets.m32 in verbose mode.")
    parser.add_argument("-m", "--maxtiles", type=int, default=8192, help="Maximum tile number that can appear in the stats. Required for the column length.")
    parser.add_argument("-f", "--format", default="excel", choices=["excel", "csv"], help="Format to output the stats to.")
    parser.add_argument("--version", action='store_true', help="Display Version Info")
    args = parser.parse_args()

    if args.version:
        print(__version__)
        return 0

    # some basic sanity checks
    if not args.logfile:
        print("ERROR: Must specify logfile!", file=sys.stderr)
        return 1
    elif not (args.logfile.endswith(".log") and os.path.exists(args.logfile)):
        print("ERROR: Provided logfile path is invalid!", file=sys.stderr)
        return 1

    logpath = args.logfile
    max_tilenum = args.maxtiles

    # parse tile and sound information from log file
    tpm, spm = parse_log(logpath)

    # Aggregate stats for tiles
    tile_stats, reject = aggregate_tilestats(tpm, maxtiles=max_tilenum, skip_overwall0=True)
    if format == "excel":
        export_stats_to_excel(tile_stats, "tile_usage_stats")
    else:
        export_stats_to_csv(tile_stats, "tilestats")

    with open("tilestats_reject.txt", "w") as fd:
        for mapname, lines in reject.items():
            if len(lines) > 0:
                fd.write(re.sub('.*/', '', mapname) + "\n")
                for l in lines:
                    fd.write(l)
                    fd.write('\n')


    # Aggregate stats for sounds
    sound_stats, reject = aggregate_soundstats(spm)
    if format == "excel":
        export_stats_to_excel(tile_stats, "sound_usage_stats")
    else:
        export_stats_to_csv(tile_stats, "soundstats")

    with open("soundstats_reject.txt", "w") as fd:
        for mapname, lines in reject.items():
            if len(lines) > 0:
                fd.write(re.sub('.*/', '', mapname) + "\n")
                for l in lines:
                    fd.write(l)
                    fd.write('\n')

    return 0

if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)