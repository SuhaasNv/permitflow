#!/bin/bash
set -e
cd "$(dirname "$0")"
# Voice lines (voice/v1..v7.wav) were made with Kokoro af_heart:
#   HYPERFRAMES_PYTHON=<python 3.12> npx hyperframes@0.8.50 tts "<line>" -o voice/vN.wav
# v1 Licensing, without the back and forth.   v2 Apply once, in four short sections.
# v3 Every document is checked before you submit.   v4 Fix only what was flagged.
# v5 Every step is on record.   v6 And your licence is issued.   v7 Checks help you. Officers decide.
# Each line is placed on its scene (ms below); the score ducks under the voice.
FF=${FFMPEG:-ffmpeg}
MS=(900 4100 6900 10300 13400 16000 17850); in=(); f=""; mix=""
for n in 1 2 3 4 5 6 7; do in+=(-i voice/v$n.wav); m=${MS[$((n-1))]}; f="$f[$n:a]aresample=48000,aformat=channel_layouts=stereo,adelay=${m}|${m}[d$n];"; mix="$mix[d$n]"; done
$FF -y -loglevel error -i ../permitflow-showreel.mp4 "${in[@]}" -filter_complex "${f}${mix}amix=inputs=7:normalize=0,apad=whole_dur=20,volume=1.6,asplit=2[vo][sc];[0:a]volume=0.8[bed];[bed][sc]sidechaincompress=threshold=0.03:ratio=6:attack=15:release=350[duck];[duck][vo]amix=inputs=2:normalize=0,alimiter=limit=0.95[a]" \
  -map 0:v -map "[a]" -c:v copy -c:a aac -b:a 256k -movflags +faststart -t 20 ../permitflow-showreel-voiceover.mp4
ls -la ../permitflow-showreel-voiceover.mp4
