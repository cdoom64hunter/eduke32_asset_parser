#!/bin/bash
# Script to extract usages of certain CON commands, to then parse using a python script.

if [ $# -eq 0 ]; then
  echo "Usage: get_con_instances.sh <code_path>"
  exit 1
fi

code_path=$1
mkdir -p "./statistics"

# find all name definitions
grep -nwr "^\s*define" ${code_path} > "./statistics/defs.txt"
grep -nwr "^\s*\(gamevar\|var\|gamearray\) [A-Za-z0-9_]\+" ${code_path} > "./statistics/vars.txt"

# find all actor definitions
grep -nwr "^\s*useractor" ${code_path} > "./statistics/useractor_instances.txt"
grep -nwr "^\s*actor\s\+[A-Za-z0-9_]\+" ${code_path}  > "./statistics/actor_instances.txt"

# find all change actor calls
grep -nwr "\s*cactor\s\+[a-zA-Z0-9_]\+" ${code_path} > "./statistics/cactor_lines.txt"

# find all instances of spawning tiles
grep -nwr "\s*spawn\s\+[a-zA-Z0-9_]\+" ${code_path} > "./statistics/spawn_instances.txt"
# grep -nwr "\s*spawnvar\s\+[a-zA-Z0-9_]\+" ${code_path} >> "./statistics/espawn_instances.txt"
grep -nwr "\s*espawn\s\+[a-zA-Z0-9_]\+" ${code_path} >> "./statistics/spawn_instances.txt"
# grep -nwr "\s*espawnvar\s\+[a-zA-Z0-9_]\+" ${code_path} >> "./statistics/spawn_instances.txt"
grep -nwr "\s*qspawn\s\+[a-zA-Z0-9_]\+" ${code_path} >> "./statistics/espawn_instances.txt"
# grep -nwr "\s*qspawnvar\s\+[a-zA-Z0-9_]\+" ${code_path} >> "./statistics/espawn_instances.txt"
grep -nwr "\s*eqspawn\s\+[a-zA-Z0-9_]\+" ${code_path} >> "./statistics/espawn_instances.txt"
# grep -nwr "\s*eqspawnvar\s\+[a-zA-Z0-9_]\+" ${code_path} >> "./statistics/espawn_instances.txt"

# find all projectile definitions
grep -nwr "\s*defineprojectile\s\+[a-zA-Z0-9_]\+" ${code_path} > "./statistics/projectile_instances.txt"

# find all screen display calls
grep -nwr "\s*myospal" ${code_path} > "./statistics/myospal.txt"
grep -nwr "\s*myospalx" ${code_path} >> "./statistics/myospal.txt"
grep -nwr "\s*rotatesprite" ${code_path} > "./statistics/rotatesprite.txt"
grep -nwr "\s*rotatespritea" ${code_path} >> "./statistics/rotatespritea.txt"

exit 0