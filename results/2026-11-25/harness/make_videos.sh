#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-only
set -euo pipefail
F=~/.local/bin/ffmpeg
cd ~/models/sparkling/claude-runs/bench/video
tmp=$(mktemp -d); : > "$tmp/list.txt"
colors=(red orange yellow green blue purple black gray)
for i in 1 2 3 4 5 6 7 8; do
  c=${colors[$((i-1))]}
  $F -hide_banner -loglevel error -y -f lavfi -i "color=c=white:s=640x360:d=1:r=24" \
     -vf "drawbox=x=0:y=0:w=640:h=60:color=$c:t=fill,drawtext=fontsize=220:fontcolor=black:x=(w-tw)/2:y=(h-th)/2+30:text=$i" \
     -c:v libx264 -pix_fmt yuv420p "$tmp/s$i.mp4"
  echo "file '$tmp/s$i.mp4'" >> "$tmp/list.txt"
done
$F -hide_banner -loglevel error -y -f concat -safe 0 -i "$tmp/list.txt" -c copy count8.mp4
$F -hide_banner -loglevel error -y -i count8.mp4 -vf "fps=6,scale=320:-1" count8.gif
$F -hide_banner -loglevel error -y -f lavfi -i "testsrc2=s=1280x720:d=90:r=30" -c:v libx264 -pix_fmt yuv420p long90.mp4
rm -rf "$tmp"; ls -la
