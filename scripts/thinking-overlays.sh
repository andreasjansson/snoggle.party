#!/bin/bash

pushd ../snoggle/static/images

function colorize-thinking {
    color=$1
    hex=$2
    convert thinking.png -alpha off -fill "$hex" -colorize 100% -alpha on /tmp/overlay.png
    convert \( thinking.png -channel RGBA -matte -colorspace gray \) \( /tmp/overlay.png +level 0,100% \) -compose multiply -composite thinking-$color.png
}

colorize-thinking teal '#39CCCC'
colorize-thinking green '#2ECC40'
colorize-thinking yellow '#FFDC00'
colorize-thinking orange '#FF851B'
colorize-thinking red '#FF4136'
colorize-thinking purple '#B10DC9'
