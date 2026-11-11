#!/usr/bin/env bash
# Make an upload copy that every platform accepts: H.264, 1080x1920 max, AAC 128k 48 kHz, faststart, < ~15 MB.
# Usage: tools/prep_video.sh "<source.mp4>" videos/<name>.mp4
set -euo pipefail
ffmpeg -y -i "$1" -c:v libx264 -preset veryfast -crf 23 -maxrate 4M -bufsize 8M -pix_fmt yuv420p \
  -vf "scale='min(1080,iw)':-2" -r 30 -c:a aac -b:a 128k -ar 48000 -ac 2 -movflags +faststart "$2"
ls -lh "$2"
