# Showreel source

`../permitflow-showreel.mp4` (20 s, 1920 x 1080, 60 fps, stereo) is rendered entirely from these files: no footage, no stock audio.

| File | What it does |
|------|--------------|
| `reel.html` | The film as one page. `seek(t)` sets every element for time `t`, so any frame can be drawn on its own. Open `reel.html?play` through a local server to watch it, or `?t=12.5` for one frame. Brand tokens, fonts and the mark come from `docs/04-design/`. |
| `render.mjs` | Draws the page in headless Chromium at 120 fps across four workers and pipes the frames into ffmpeg. Fonts are served from `frontend/public/fonts`. |
| `audio.py` | Synthesises the score with numpy and scipy (120 BPM, A minor), with each hit, tick and whoosh placed on a visual event. Writes `score.wav`. |
| `assemble.sh` | Blends each pair of 120 fps frames into one 60 fps frame (motion blur), adds the score and writes the MP4 and the poster frame. |

```bash
npm i playwright-core                 # Chromium via CHROME_PATH, or a Playwright browser
pip install numpy scipy
CHROME_PATH=/path/to/chrome node render.mjs full 120 4
python3 audio.py
FFMPEG=ffmpeg ./assemble.sh           # ffmpeg with libx264
```

Scenes: the mark builds itself, the wordmark, apply once, checked before you submit, fix only what was flagged, every step on record, the licence issued, the end card with the disclaimer that this is a fictional service.
