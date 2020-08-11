#!/bin/python3
# Author: Dino Bollinger
# Licensed under BSD 3-Clause License, see included LICENSE file

import sys
import os
import re
import argparse
import pandas as pd
import numpy as np

MAXTILES = 32256

mapload_pattern = "Loaded V. map (.*) (successfully|\(moderate corruption\)).*"

tile_start = "Searching for tiles used in current map..."
tile_end = "Tile search finished."
sound_start = "Searching for sounds used in current map..."
sound_end = "Sound search finished."

def parse_log(logfile):
    """
    Parse the mapster32.log for statistics as output by dump_used_assets.m32.
    Make sure that the variable "verbose" is set to 1 inside mapster32!
    :param logfile: log file to which the statistics were dumped to
    :return Two dicts containing per-map tile and sound statistics respectively.
    """
    tiles_per_map = dict()
    sounds_per_map = dict()

    curr_map = None
    with open(logfile, 'r', encoding="utf8") as fd:
        try:
            while True:
                line = next(fd)
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


def aggregate_tilestats(tpm, skip_overwall0):
    """
    Takes as argument a dict of tile stats per level, and sums them.
    This also produces totals per map, and a total over all maps given as input.
    Hereby it is assumed that there exists one line per sprite, floor, ceiling wall and overwall.
    :param tpm: A dictionary of tile stats. Each dictionary key is a map filename which
                is assumed to contain a list of stats as output by dump_used_assets.m32 in verbose mode.
    :param skip_overwall0: Tile 0 is used by default for all overwalls that are transparent. Set to true to not count these.
    :return: Dict of aggregates stats for each map. Each dict entry is a dict with the following keys:
            {"sprite", "floor", "ceiling", "wall", "overwall", "total"}
             Each entry for these keys is a numpy array of MAXTILES entries, storing the number of times the respective tile is used.
    """

    tile_stats = dict()
    reject_stats = dict()
    for map_filename in tpm.keys():

        # use numpy arrays for correct tiles
        newstats = {"sprite": np.zeros(MAXTILES), "floor": np.zeros(MAXTILES), "ceiling": np.zeros(MAXTILES),
                    "wall": np.zeros(MAXTILES), "overwall": np.zeros(MAXTILES)}

        # rejected entries
        newreject = []

        for line in tpm[map_filename]:
            k = line.split(sep=',')
            ttype = k[0]
            tidx = int(k[1])

            if tidx >= MAXTILES:
                print(f"WARNING: Tile index {tidx} in map {map_filename} exceeds MAXTILES of {MAXTILES}::{line}", file=sys.stderr)
                newreject.append(line)
            elif tidx < 0:
                print(f"WARNING: Negative picnum found in map {map_filename}::{line}", file=sys.stderr)
                newreject.append(line)
            else:
                newstats[ttype][tidx] += 1

        # overpicnum == 0 is transparent; don't count
        if skip_overwall0:
            newstats["overwall"][0] = 0

        # aggregate total column for each map
        maptotal = np.zeros(MAXTILES)
        for cat in newstats.keys():
            maptotal += newstats[cat]
        newstats["TOTAL"] = maptotal

        tile_stats[map_filename] = newstats
        reject_stats[map_filename] = newreject

    # aggregate total over all maps
    if len(tile_stats.keys()) > 1:
        allmaptotal = {"sprite": np.zeros(MAXTILES), "floor": np.zeros(MAXTILES), "ceiling": np.zeros(MAXTILES),
                       "wall": np.zeros(MAXTILES), "overwall": np.zeros(MAXTILES), "TOTAL": np.zeros(MAXTILES)}

        for k in tile_stats.keys():
            for cat in tile_stats[k].keys():
                allmaptotal[cat] += tile_stats[k][cat]

        tile_stats["TOTAL"] = allmaptotal

    return tile_stats, reject_stats


def aggregate_soundstats(spm):
    """
    Takes as argument a dict of sound stats per level, and computes the aggregate sum.
    :param spm: Dict of sound stats per map, stored as lines of strings. (emitter,  soundnum)
    :return: dict of dicts, storing number of times sounds are used per emitter type
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
                print(f"WARNING: Negative sound index found in map {map_filename}::{line}", file=sys.stderr)
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

    # after data is aggregated, reformat into numpy arrays and compute totals
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



def export_stats_to_csv(stat_dict: dict, outfile_prefix: str):
    outdir = "./csv_out"
    if not os.path.exists(outdir):
        os.mkdir(outdir, mode=0o755)

    for k in stat_dict.keys():
        ts_dataframe = pd.DataFrame(stat_dict[k])

        # ensure this column is placed last
        total_col = ts_dataframe.pop("TOTAL")
        ts_dataframe.insert(len(ts_dataframe.columns), "TOTAL", total_col)

        mapname = re.sub('(\.MAP$|\.map$)', '', re.sub('.*/', '', k))
        ts_dataframe.to_csv(f"{outdir}/{outfile_prefix}_{mapname}.csv", sep=',', na_rep="N/A", float_format="%d")


def export_stats_to_excel(stat_dict:dict, outfile_prefix:str):
    writer = pd.ExcelWriter(outfile_prefix +".xlsx", engine='xlsxwriter')

    for k in stat_dict.keys():
        ts_dataframe = pd.DataFrame(stat_dict[k])

        # ensure this column is placed last
        total_col = ts_dataframe.pop("TOTAL")
        ts_dataframe.insert(len(ts_dataframe.columns), "TOTAL", total_col)

        mapname = re.sub('.*/', '', k)
        ts_dataframe.to_excel(writer, sheet_name=f"{mapname}", na_rep="N/A")

    writer.save()
    writer.close()


def main(log_path, format):

    # parse tile and sound information from log file
    tpm, spm = parse_log(log_path)

    # Aggregate stats for tiles
    tile_stats, reject = aggregate_tilestats(tpm, skip_overwall0=True)
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


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("logfile", type=str, help="Logfile as output by dump_used_assets.m32 in verbose mode.")
    parser.add_argument("-f", "--format", default="excel", choices=["excel", "csv"], help="Format to output the stats to.")
    args = parser.parse_args()

    main(args.logfile, args.format)

# REFERENCE: Output format of dump_used_assets.m32
### Loaded V9 map <path>/<map> successfully
### Searching for tiles used in current map...
### sprite,<num>,
### floor,<num>,
### ceiling,<num>,
### wall,<num>,
### overwall,<num>,
### Tile search finished.
### Searching for sounds used in current map...
### MUSICANDSFX ambient,<num>,
### MUSICANDSFX triggered,<num>,
### switch,44,
### MIRROR,252,
### Sound search finished.
### Search finished.
