#!/bin/bash

pushd ../snoggle/static/images/letters-shadow

for f in *.png
do
    letter=${f%.*}
    for color in red green purple orange yellow teal
    do
        convert $f \( ../overlay-$color.png -scale 10% +level 0,100% -bordercolor none -border 20x20 \) -compose multiply -composite $letter-with-$color.png
    done
done
