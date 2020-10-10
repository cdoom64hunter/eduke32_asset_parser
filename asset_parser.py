#!/bin/python3
# Author: Dino Bollinger
# Licensed under BSD 3-Clause License, see included LICENSE file

""" Mapster32 Asset Count Parser
Parses and aggregates the statistics as output by the `dump_used_assets.m32` script in verbose mode.
Said script is part of the eduke32 package, and can be found in the main eduke32 repository.
Statistics can be output as an sqlite database, as xlsx or as csv.
------------------------------------------------------------------------------------------
Usage: asset_parser.py <logfile> (sqlite|xlsx|csv) [--maxtiles <max_tiles>] [--use_extra_stats]
       asset_parser.py --help -h
       asset_parser.py --version
Required Arguments:
    logfile            Mapster32 log file path that contains the statistics to parse
    sqlite|xlsx|csv    Output statistics as an SQLite database, an Excel document or as multiple CSV files.
Options:
    --maxtiles -m <max_tiles>   Defines the maximum expected tilenum. [default: 8192]
    --use_extra_stats -u        Looks for additional stats files and includes them. [default: 1]
"""

import sys
import os
import re
import sqlite3
import pickle

import pandas as pd
import numpy as np

from typing import Dict, List, Tuple, Optional

from docopt import docopt

TILE_SCHEMA = "./databases/tiles.sql"
SOUND_SCHEMA = "./databases/sounds.sql"
DBPATH = "./databases/asset_stats.sqlite"

__version__ = "2.0"

# Indicates the start of a map in the log. Comes in several variations depending on version and corruption.
mapload_pattern = re.compile("Loaded V[0-9]+ map (.*) (successfully|\(EXTREME corruption\)|\(HEAVY corruption\)|\(moderate corruption\)|\(removed [0-9]+ sprites\)).*")
map_ext_pattern = re.compile("\\.map$", re.IGNORECASE)

# Indicate the start and end of the tile search of dump_used_assets.m32
tile_start = "Searching for tiles used in current map..."
tile_end = "Tile search finished."

# Indicate the start and end of the sound search of dump_used_assets.m32
sound_start = "Searching for sounds used in current map..."
sound_end = "Sound search finished."

class MapStatsParser:
    def __init__(self, maxtiles, **kwargs):
        self.stats_db: Optional[sqlite3.Connection] = None
        self.maxtiles = maxtiles

        # expected: paths to pickle files
        self.extra_tilestats: Dict[str, np.ndarray] = dict()
        for k, v in kwargs: ## path to additional files
            print(f"Using extra stats file: {v}")
            with open(v, 'r') as fd:
                loaded_arr = pickle.load(fd)
                if type(loaded_arr) != np.ndarray:
                    raise ValueError("Error: extra stats pickle file does not contain a valid ndarray!")
                elif loaded_arr.shape != (maxtiles,):
                    raise ValueError(f"Error: extra stats array size is {loaded_arr.shape}, but maxtiles is {maxtiles}!")
                self.extra_tilestats[k] = loaded_arr


    @staticmethod
    def parse_log(logpath: str) -> Tuple[Dict[str, List[str]], Dict[str, List[str]]]:
        """
        Parse the mapster32.log for asset information as output by dump_used_assets.m32.
        Make sure that the variable "verbose" is set to 1 inside mapster32!
        :param logpath: log file from which to read the dump
        :return Two dicts containing per-map tile and sound statistics respectively.
        """
        tiles_per_map: Dict[str, List[str]] = dict()
        sounds_per_map: Dict[str, List[str]] = dict()

        curr_map = None
        with open(logpath, 'r', encoding="utf8") as fd:
            try:
                while True:
                    line = next(fd).strip()
                    match = mapload_pattern.match(line)
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


    @staticmethod
    def aggregate_tilestats(tpm: Dict[str, List[str]], maxtiles: int, skip_overwall0: bool = True):
        """
        Takes as argument a dict of tile stats per level, and sums them.
        This also produces totals per map, and a total over all maps given as input.
        Hereby it is assumed that there exists one line per sprite, floor, ceiling wall and overwall.
        :param tpm: A dictionary of tile stats. Each dictionary key is a map filename which
                    is assumed to contain a list of stats as output by dump_used_assets.m32 in verbose mode.
        :param maxtiles: Maximum expected tilenum. This determines the size of the resulting columns.
                    Invalid tilenums will be collected and output as a secondary list of rejects.
        :param skip_overwall0: Tile 0 is used by default for all overwalls that are transparent,
                               hence they are not actually using this tile.
                               Default is true. Set to false to count these as well.
        :return: Tuple: (tile_stats, reject_stats)
                 tile_stats: Dict of aggregates stats for each map. Each dict entry is a dict with the following keys:
                    {"sprite", "floor", "ceiling", "wall", "overwall", "total"}
                    Each entry for these keys is a numpy array of `maxtiles` entries, storing the
                    number of times the respective tile is used.
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
            newstats["total"] = maptotal

            tile_stats[map_filename] = newstats
            reject_stats[map_filename] = newreject

        # aggregate total over all maps
        if len(tile_stats.keys()) > 1:
            allmaptotal = {"sprite": np.zeros(maxtiles), "floor": np.zeros(maxtiles), "ceiling": np.zeros(maxtiles),
                           "wall": np.zeros(maxtiles), "overwall": np.zeros(maxtiles), "total": np.zeros(maxtiles)}

            for k in tile_stats.keys():
                for cat in tile_stats[k].keys():
                    allmaptotal[cat] += tile_stats[k][cat]

            tile_stats["total"] = allmaptotal

        return tile_stats, reject_stats


    @staticmethod
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

            new_sound_dict[k]["total"] = total_stats

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

            new_sound_dict["total"] = allmaptotal

        return new_sound_dict, reject_stats


    def start_database(self):
        """ establish a connection with the sqlite database
            creates the file if not present """
        if self.stats_db is not None:
            raise RuntimeError("Database connection already established")
        self.stats_db = sqlite3.connect(DBPATH)


    def close_database(self):
        """ Commits and closes the connection. """
        if self.stats_db is None:
            raise RuntimeError("No database connection")
        self.stats_db.commit()
        self.stats_db.close()
        self.stats_db = None


    def db_setup_table(self, schema_file:str, mapname: str):
        """ Initializes the tables for the given map name.
            Deletes existing tables for this map. """
        if self.stats_db is None:
            raise RuntimeError("No database connection")

        c = self.stats_db.cursor()
        with open(schema_file, 'r') as f:
            initial_commands = f.read()
            initialize_maptable = initial_commands.replace("<REPLACE_MAPNAME>", mapname)
            c.executescript(initialize_maptable)
        c.close()
        self.stats_db.commit()


    def export_tiles_to_sqlite(self, stat_dict: Dict):
        for mapname, stats in stat_dict.items():
            tiles_known_columns = {"id", "sprite", "wall", "ceiling", "floor", "overwall", "total"}
            cleaned_mapname = map_ext_pattern.sub('', mapname)
            cleaned_mapname = re.sub('.*/', '', cleaned_mapname)
            self.db_setup_table(TILE_SCHEMA, cleaned_mapname)

            cols = []
            command_string = f"INSERT INTO {cleaned_mapname}_tiles (id"
            value_string = "VALUES (?"

            col:str
            for col, v in stats.items():
                col_name = re.sub("\s", "_", col)
                command_string += f",{col_name}"
                value_string += ",?"
                cols.append(v)

            for col, v in self.extra_tilestats.items():
                col_name = re.sub("\s", "_", col)
                if col_name not in tiles_known_columns:
                    tiles_known_columns.add(col_name)
                    add_col_command = f"ALTER TABLE {cleaned_mapname}_tiles ADD {col_name} INTEGER"
                    self.stats_db.execute(add_col_command)
                command_string += f",{col_name}"
                value_string += ",?"
                cols.append(v)

            self.stats_db.commit()

            command_string += ") " + value_string + ");"

            mat = np.vstack(cols).transpose()
            for i in range(mat.shape[0]):
                vals = (i, *mat[i, :])
                self.stats_db.execute(command_string, vals)

            self.stats_db.commit()


    def export_sounds_to_sqlite(self, stat_dict: Dict):
        for mapname, stats in stat_dict.items():
            sounds_known_columns = {"id", "total"}
            cleaned_mapname = map_ext_pattern.sub('', mapname)
            cleaned_mapname = re.sub('.*/', '', cleaned_mapname)
            self.db_setup_table(SOUND_SCHEMA, cleaned_mapname)

            cols = []
            command_string = f"INSERT INTO {cleaned_mapname}_sounds (id"
            value_string = "VALUES (?"

            # Yes this is prone to an SQL injection but screw it.
            col:str
            for col, v in stats.items():
                col_name = re.sub("\s", "_", col)
                if col_name not in sounds_known_columns:
                    sounds_known_columns.add(col_name)
                    add_col_command = f"ALTER TABLE {cleaned_mapname}_sounds ADD {col_name} INTEGER"
                    self.stats_db.execute(add_col_command)
                command_string += f",{col_name}"
                value_string += ",?"
                cols.append(v)

            self.stats_db.commit()

            command_string += ") " + value_string + ");"

            mat = np.vstack(cols).transpose()
            for i in range(mat.shape[0]):
                vals = (i, *mat[i, :])
                self.stats_db.execute(command_string, vals)

            self.stats_db.commit()


    def export_stats_to_excel(self, stat_dict:dict, outfile_prefix:str, insert_extras:bool=False) -> None:
        """
        Export the given stats dictionary to excel format.
        :param stat_dict:
        :param outfile_prefix:
        :return:
        """
        writer = pd.ExcelWriter(outfile_prefix +".xlsx", engine='xlsxwriter')

        for k in stat_dict.keys():
            ts_dataframe = pd.DataFrame(stat_dict[k])

            # ensure this column is placed behind sprite, wall etc.
            total_col = ts_dataframe.pop("total")
            ts_dataframe.insert(len(ts_dataframe.columns), "total", total_col)

            # only for tile stats
            if insert_extras:
                for j, v in self.extra_tilestats.items():
                    v.resize(total_col.shape)
                    ts_dataframe.insert(len(ts_dataframe.columns), j, v)

            mapname = re.sub('.*/', '', k)
            ts_dataframe.to_excel(writer, sheet_name=f"{mapname}", na_rep="N/A")

        writer.save()
        writer.close()


    def export_stats_to_csv(self, stat_dict: dict, outfile_prefix: str, insert_extras:bool = False) -> None:
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

            # ensure this column is placed behind the others
            total_col = ts_dataframe.pop("total")
            ts_dataframe.insert(len(ts_dataframe.columns), "total", total_col)

            # only for tile stats
            if insert_extras:
                for j, v in self.extra_tilestats.items():
                    v.resize(total_col.shape)
                    ts_dataframe.insert(len(ts_dataframe.columns), j, v)

            mapname = map_ext_pattern.sub('', k)
            mapname = re.sub('.*/', '', mapname)

            ts_dataframe.to_csv(f"{outdir}/{outfile_prefix}_{mapname}.csv", sep=',', na_rep="N/A", float_format="%d")

    def output_rejected_stats(self, reject, filename):
        # collect and output rejected lines
        reject_lines = []
        for mapname, lines in reject.items():
            if len(lines) > 0:
                reject_lines.append(re.sub('.*/', '', mapname) + "\n")
                for l in lines:
                    reject_lines.append(l + "\n")

        if len(reject_lines) > 0:
            with open(filename, "w") as fd:
                for r in reject_lines:
                    fd.write(r)
            print(f"rejected lines listed in {filename}")


def main():
    argv = None
    cargs = docopt(__doc__, argv=argv, version=__version__)

    # some basic sanity checks
    mapster32_log_path = cargs["<logfile>"]
    if not (mapster32_log_path.endswith(".log") and os.path.exists(mapster32_log_path)):
        print("ERROR: Provided logfile path is invalid!", file=sys.stderr)
        return 1

    print("Extra stats usage enabled.")
    if cargs["--use_extra_stats"]:
        files = os.listdir("./extra_input")
        extras = {f[0:-4]: f for f in files if f.endswith(".pkl")}
    else:
        extras = dict()

    max_tilenum = int(cargs["--maxtiles"])
    parser = MapStatsParser(maxtiles=max_tilenum, **extras)

    # parse tile and sound information from log file
    tpm, spm = parser.parse_log(mapster32_log_path)

    # Aggregate stats for tiles
    tile_stats, reject = parser.aggregate_tilestats(tpm, maxtiles=max_tilenum, skip_overwall0=True)
    parser.output_rejected_stats(reject, "tilestats_reject.txt")

    # Aggregate stats for sounds
    sound_stats, reject = parser.aggregate_soundstats(spm)
    parser.output_rejected_stats(reject, "soundstats_reject.txt")

    if cargs["sqlite"]:
        parser.start_database()
        parser.export_tiles_to_sqlite(tile_stats)
        print(f"tile statistics written to database at {DBPATH}")
        parser.export_sounds_to_sqlite(sound_stats)
        print(f"sound statistics written to database at {DBPATH}")
        parser.close_database()
    elif cargs["xlsx"]:
        parser.export_stats_to_excel(tile_stats, "tile_usage_stats", insert_extras=cargs["--use_extra_stats"])
        print(f"sound statistics written to xlsx file at tile_usage_stats.xlsx")
        parser.export_stats_to_excel(sound_stats, "sound_usage_stats", insert_extras=False)
        print(f"sound statistics written to xlsx file at sound_usage_stats.xlsx")
    elif cargs["csv"]:
        parser.export_stats_to_csv(tile_stats, "tilestats", insert_extras=cargs["--use_extra_stats"])
        print(f"sound statistics written to csv files in the folder './tilestats'")
        parser.export_stats_to_csv(sound_stats, "soundstats", insert_extras=False)
        print(f"sound statistics written to csv files in the folder './soundstats'")
    else:
        raise ValueError("unsupported format for exporting statistics")

    return 0


if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)