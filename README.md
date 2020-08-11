# Parser for EDuke32 Map Statistics Output
This repository contains Python scripts to parse and aggregate Duke 3D map file statistics as reported by the `dump_used_assets.m32` mapster32 script, which can be found here: https://voidpoint.io/terminx/eduke32/-/blob/master/package/sdk/samples/dump_used_assets.m32

The `dump_used_assets.m32` script is to be loaded in mapster32 by executing the command `include mapster32`. Instructions on how to use it are given in the file itself. By running it with the verbose setting active, it will generate single lines of output for each ART tile and sound used inside a map, which are printed into the `mapster32.log` file. The Python scripts in this repository serve to parse said log file, aggregate the reported statistics produced by the verbose setting and finally output them in Excel or CSV format.

The generated tables contain the number of times each art tile and sound is used per entity (e.g. walls, sprites, floors), as well as total aggregates per map, and totals over all maps.


## Requirements

* Python 3.8
* Pandas 1.03+
* Numpy 1.18+
* Additional xlsx modules for use with Pandas (if exporting to excel file)

## Usage

Execute the script in a terminal with the following parameters:

`python3 assets_parser.py [-f {excel,csv}] logfile`

## TODO

Additional features will be implemented at a later date, including:
* Marking tile and sound indices that are hardcoded in the Duke3D engine source code.
* Marking empty tile spaces.
* Marking tiles used as actor rotations.
* Marking tiles spawned in CON code.
* Other improvements

## License
All python scripts are licensed under BSD 3-clause license and have been authored by Dino Bollinger.

Thanks go to whoever authored the `dump_used_assets.m32` script.
