"""The one place the API's version lives (the release ritual bumps it here, in `frontend/package.json`,
the lockfile, `pyproject.toml` and `uv.lock`). The commit is baked into the image by CI (`GIT_SHA`), so
the metrics, the Telegram bot and the hourly digest can say which build answers in each environment.

US-111, build once and promote: the `APP_VERSION` environment variable overrides the literal at start, so
production runs the tested candidate's image labelled with the release version. The commit stays the one the
image was built from (the candidate's), never the merge commit."""

import os

APP_VERSION = "0.5.0-rc.8"
APP_VERSION = (os.environ.get("APP_VERSION") or "").strip() or APP_VERSION
BUILD_COMMIT = (os.environ.get("GIT_SHA") or "")[:7] or "local"

__all__ = ["APP_VERSION", "BUILD_COMMIT"]
