#!/bin/zsh
cd "$(dirname "$0")"
for f in static/*.html; do
  n=$(basename $f .html)
  case $n in Mobile*) vp=390,844;; NotificationsPanel) vp=420,480;; DialogRequestResubmission) vp=640,560;; DesignSystem) vp=1440,900;; TabletDocuments) vp=1024,900;; *) vp=1280,900;; esac
  npx -y playwright@1.58.0 screenshot --full-page --viewport-size=$vp --wait-for-timeout=1200 http://localhost:8765/$n.html shots/$n.png >/dev/null 2>&1 &
done
wait
ls shots | wc -l
