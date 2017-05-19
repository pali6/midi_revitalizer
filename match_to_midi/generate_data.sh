#!/bin/bash

# Manual time scaling values:
# old, played -> 1
# old, score -> ~15000
# 5.0, played -> ~8
# 5.0, score -> ~4000

# Mozart & Schubert are 5.0

targetDir="../match_midi/"
script="../../match_to_midi/match_to_midi.py"
sourceDir="../data/match"

cd "$sourceDir"
for filename in Chopin*match
do
    echo $filename
    if [[ ${filename%.match} == *p01 ]]; then
        "$script" -n score -s 15000 "$filename" "$targetDir${filename%_p01.match}_score.mid"
    fi
    "$script" -n played -s 1 "$filename" "$targetDir${filename%.match}.mid"
done

for filename in Mozart*match Schubert*match
do
    echo $filename
    if [[ ${filename%.match} == *p01 ]]; then
        "$script" -n score -s 4000 "$filename" "$targetDir${filename%_p01.match}_score.mid"
    fi
    "$script" -n played -s 8 "$filename" "$targetDir${filename%.match}.mid"
done
