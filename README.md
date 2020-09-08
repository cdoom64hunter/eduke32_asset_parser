# Parser for EDuke32 Map Statistics Output
This repository contains Python scripts to parse and aggregate Duke 3D map file statistics as reported by the `dump_used_assets.m32` mapster32 script. 
Said script originates from: https://voidpoint.io/terminx/eduke32/-/blob/master/package/sdk/samples/dump_used_assets.m32
For ease of access it is also included in this repository. I take no credit for the work in said M32 script, credit goes to the respective authors.

The `dump_used_assets.m32` script can be loaded in mapster32 by executing the command `include dump_used_assets` in the console. 
Instructions on how to compile the statistics are given in the script documentation itself.

By running it with the verbose setting active, it will generate single lines of output for each ART tile and sound used inside a map, 
which are printed into the `mapster32.log` file. The script `asset_parser.py` in this repository serves to parse said log file, aggregate 
the reported tile usages into fine-grained counts, separated by type and map, and finally output them in Excel or CSV format.

The generated tables contain the number of times each art tile and sound is used per entity (e.g. walls, sprites, floors), as well as 
total aggregates per map, and additionally totals over all maps. 

Suplemental scripts are provided which serve to extract additional useful information around the context of the map file in order
to be able to better filter the list of tiles. This includes:
* `names_parser.py`: Script to find usages of hardcoded Duke3D tiles. Allows filtering hardcoded tiles which have behavior associated with them in the Duke3D source.


## Requirements

* Python 3.8
* Pandas 1.03+
* Numpy 1.18+
* Additional xlsx modules for use with Pandas (if exporting to excel file)

## Usage
```    
   asset_parser.py <logfile> [--maxtiles <max>] (--format (excel|csv))
   asset_parser.py --help
   asset_parser.py --version

Options:
    --maxtiles -m    Defines the maximum expected tilenum, and thus the resulting column size. (Default: 8192)
    --format -f      Use either "excel" or "csv" output format.
```

## TODO

Additional features will be implemented at a later date, including:
* Marking tile and sound indices that are hardcoded in the Duke3D engine source code.
* Marking empty tile spaces.
* Marking tiles used as actor rotations.
* Marking tiles spawned in CON code.
* Other improvements

## Credits and License
All python scripts are licensed under BSD 3-clause license and have been created by Dino Bollinger.

Thanks go to whoever authored the `dump_used_assets.m32` script, unfortunately no original authors are listed in the file itself.
