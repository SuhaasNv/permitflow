#!/bin/bash
set -e
cd "$(dirname "$0")"
# expects chunk0..3.mp4 from `node render.mjs full 120 4` and score.wav from `python3 audio.py`
FF=${FFMPEG:-ffmpeg}
printf "file 'chunk%d.mp4'\n" 0 1 2 3 > list.txt
$FF -y -loglevel error -f concat -safe 0 -i list.txt -i score.wav \
  -filter_complex "[0:v]tmix=frames=2:weights='1 1',select='not(mod(n\,2))',setpts=N/60/TB,format=yuv420p[v]" \
  -map "[v]" -map 1:a -r 60 -c:v libx264 -preset slow -crf 16 -profile:v high -tune film \
  -c:a aac -b:a 256k -movflags +faststart -t 20 permitflow-showreel.mp4
$FF -y -loglevel error -ss 18.95 -i permitflow-showreel.mp4 -frames:v 1 -q:v 2 permitflow-showreel-poster.jpg
ls -la permitflow-showreel.mp4 permitflow-showreel-poster.jpg
