"""The one place the API's version lives (the release ritual bumps it here, in `frontend/package.json`,
the lockfile, `pyproject.toml` and `uv.lock`). The commit is baked into the image by CI (`GIT_SHA`), so
the metrics, the Telegram bot and the hourly digest can say which build answers in each environment."""

import os

APP_VERSION = "0.4.0-rc.1"
BUILD_COMMIT = (os.environ.get("GIT_SHA") or "")[:7] or "local"

__all__ = ["APP_VERSION", "BUILD_COMMIT"]
