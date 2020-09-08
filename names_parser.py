#!/bin/python3
# Author: Dino Bollinger
# Licensed under BSD 3-Clause License, see included LICENSE file
"""
Parses names.h and namesdyn.h of the Duke3D source and finds all actual usages of the contained tile definitions.
This is output as individual csv files, and as combined report. Individual usage lines are also reported.
The resulting output is a csv with markers for which tiles have hardcoded behavior, and which do not. (1/0)
Usage: namesh_parser.py
"""
import sys
import os
import subprocess

# Output directory for all reports
output_dir = "./namesh_report"

tilenum_to_hardc = dict()
tilenum_to_name = dict()

def dump_name_stats(infile:str, outfile:str, outfile_second:str) -> None:
    usages_writer = open(outfile_second, 'w')
    report_writer = open(outfile, "w")
    report_writer.write("used, name, tilenum\n")
    with open(infile, "r") as fd:
        for line in fd:
            line = line.strip()
            if line.startswith("#define"):
                newsplit = line.split(maxsplit=2)

                # format: #define SECTOREFFECTOR 1
                if len(newsplit) != 3:
                    continue

                name, number = newsplit[1], newsplit[2]
                if not number.isnumeric():
                    continue

                usages_writer.write(f"Usages for: {name}\n")
                out = subprocess.Popen(['grep', "-wnr", f"{name}", "source/duke3d/src"],
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.STDOUT)

                stdout, stderr = out.communicate()

                decoded_lines = stdout.strip().decode("utf-8").split("\n")

                sanitized_lines = [grepline for grepline in decoded_lines if ("source/duke3d/src/names.h" not in grepline) \
                                   and ("source/duke3d/src/namesdyn.cpp" not in grepline) \
                                   and ("source/duke3d/src/namesdyn.h" not in grepline)]

                if len(sanitized_lines) > 0:
                    for sl in sanitized_lines:
                        usages_writer.write(sl + "\n")
                    report_writer.write(f"1, {name}, {number}\n")
                else:
                    report_writer.write(f"0, {name}, {number}\n")
    usages_writer.close()
    report_writer.close()



def read_dump(fd):
    headers = fd.readline()
    if headers.strip() != "used, name, tilenum":
        return 1

    for line in fd:
        entries = line.strip().split(sep=",")
        tile_num = int(entries[2])
        if tile_num not in tilenum_to_hardc:
            tilenum_to_hardc[tile_num] = int(entries[0])
            tilenum_to_name[tile_num] = [entries[1].strip()]
        else:
            tilenum_to_hardc[tile_num] |= int(entries[0])
            tilenum_to_name[tile_num].append(entries[1].strip())
    return 0



def main() -> int:

    os.makedirs(output_dir, exist_ok=True)

    infile = "./source/duke3d/src/names.h"
    if not os.path.exists(infile):
        print("ERROR: Failed to find names.h -- check duke3d source code path", file=sys.stderr)
        return 1

    print(f"Parsing {infile}")
    nh_outfile = os.path.join(output_dir, "names_report.csv")
    nh_outfile_second = os.path.join(output_dir, "names_usages.txt")

    dump_name_stats(infile, nh_outfile, nh_outfile_second)

    infile = "./source/duke3d/src/namesdyn.h"
    if not os.path.exists(infile):
        print("ERROR: Failed to find namesdyn.h -- check duke3d source code path", file=sys.stderr)
        return 1

    print(f"Parsing {infile}")
    nd_outfile = os.path.join(output_dir, "namesdyn_report.csv")
    nd_outfile_second = os.path.join(output_dir, "namesdyn_usages.txt")

    dump_name_stats(infile, nd_outfile, nd_outfile_second)

    # Read dump to fill dicts
    with open(nh_outfile, 'r') as fr:
        if read_dump(fr) != 0:
            print(f"Error while reading dumpfile {nh_outfile}", file=sys.stderr)
            return 1

    with open(nd_outfile, 'r') as fr:
        if read_dump(fr) != 0:
            print(f"Error while reading dumpfile {nd_outfile}", file=sys.stderr)
            return 1

    print(f"Combining reports...")

    cb = os.path.join(output_dir, "combined.csv")
    with open(cb, "w") as fd:
        fd.write("tilenum, used, names\n")
        for tile_num in sorted(list(tilenum_to_hardc.keys())):
            used = tilenum_to_hardc[tile_num]
            names = tilenum_to_name[tile_num]
            fd.write(f"{tile_num}, {used}, {'::'.join(names)}\n")

    print(f"Combined report written to {cb}")
    return 0

if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)
