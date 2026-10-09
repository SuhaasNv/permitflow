"""The settings an administrator may tune without a redeploy, and the bounds that keep them safe (US-101).

Pure rules, no I/O. Each setting names the environment variable that is its default and, for a number,
its ceiling: the panel can move a value only inside `[minimum, ceiling]`, so a stolen administrator session
can lower a limit but never remove or raise one. Zero ("off") is not reachable from the panel: the lowest
value is always at least 1. Where the environment itself says 0 (no limit), the ceiling is the setting's
own absolute cap, and the default stays "no limit" until someone sets a row.

`effective()` is also the read-time guard: a stored value that has fallen outside the bounds since it was
written (the environment ceiling was lowered, or a row was edited by hand) is clamped or ignored, so the
database alone can never loosen a limit past the environment.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

SettingKind = Literal["int", "bool", "choice"]
SettingGroup = Literal["traffic", "ai", "uploads", "system"]

# 10 MB: the upload cap of the brief. The panel (and the environment) cannot go above it.
UPLOAD_HARD_MAX_BYTES = 10 * 1024 * 1024


@dataclass(frozen=True)
class SettingSpec:
    key: str
    label: str
    description: str
    group: SettingGroup
    kind: SettingKind
    # The attribute on `core.settings.Settings` that is this setting's default and ceiling. None: the
    # default is `fallback` and there is no environment value.
    env_field: str | None
    unit: str = ""
    minimum: int = 0
    # The ceiling when the environment value is 0 (no limit) or absent; also an upper clamp on the env.
    absolute_max: int = 0
    fallback: int | bool | str = 0
    choices: tuple[str, ...] = ()
    # False while the consumer is a later story: the value is stored and audited but nothing reads it yet.
    in_use: bool = True


SPECS: tuple[SettingSpec, ...] = (
    SettingSpec(
        key="rate_limit_per_minute",
        label="Requests per minute per client",
        description="Every request from one client address, sliding minute.",
        group="traffic",
        kind="int",
        env_field="rate_limit_per_minute",
        unit="requests",
        minimum=10,
        absolute_max=100_000,
    ),
    SettingSpec(
        key="login_attempts_per_minute",
        label="Sign-in attempts per minute per client",
        description="Sign-in attempts of any outcome from one client address, sliding minute.",
        group="traffic",
        kind="int",
        env_field="login_attempts_per_minute",
        unit="attempts",
        minimum=3,
        absolute_max=10_000,
    ),
    SettingSpec(
        key="ai_runs_per_user_per_day",
        label="AI checks per person per day",
        description="Document checks one applicant may start over a rolling day.",
        group="ai",
        kind="int",
        env_field="ai_runs_per_user_per_day",
        unit="checks",
        minimum=1,
        absolute_max=100_000,
    ),
    SettingSpec(
        key="ai_runs_per_day",
        label="AI checks per platform per day",
        description="Document checks the whole platform may start over a rolling day (the cost brake).",
        group="ai",
        kind="int",
        env_field="ai_runs_per_day",
        unit="checks",
        minimum=1,
        absolute_max=1_000_000,
    ),
    SettingSpec(
        key="max_drafts_per_user",
        label="Drafts per person",
        description="Open draft applications one operator may hold.",
        group="traffic",
        kind="int",
        env_field="max_drafts_per_user",
        unit="drafts",
        minimum=1,
        absolute_max=1_000,
    ),
    SettingSpec(
        key="upload_max_bytes",
        label="Upload size",
        description="Largest single file accepted, in bytes (never above 10 MB).",
        group="uploads",
        kind="int",
        env_field="upload_max_bytes",
        unit="bytes",
        minimum=1024 * 1024,
        absolute_max=UPLOAD_HARD_MAX_BYTES,
    ),
    SettingSpec(
        key="ai_max_text_chars",
        label="AI text characters",
        description="Characters of document text sent to the model for one check.",
        group="ai",
        kind="int",
        env_field="ai_max_text_chars",
        unit="characters",
        minimum=1_000,
        absolute_max=200_000,
    ),
    SettingSpec(
        key="worker_concurrency",
        label="Worker concurrency",
        description="Checks the worker runs at the same time. Read live by the worker (US-098).",
        group="ai",
        kind="int",
        env_field="worker_concurrency",
        unit="checks",
        minimum=1,
        absolute_max=32,
    ),
    SettingSpec(
        key="ai_paused",
        label="Pause AI checks",
        description=(
            "While on, no new check is sent to the AI provider: each is stored as unavailable with the "
            "reason ai_paused, and the application can still be submitted."
        ),
        group="ai",
        kind="bool",
        env_field=None,
        fallback=False,
    ),
    SettingSpec(
        key="telegram_per_check_messages",
        label="Telegram message per check",
        description="Send one Telegram message for every document check. Stored now; read by US-100.",
        group="system",
        kind="bool",
        env_field=None,
        fallback=False,
        in_use=False,
    ),
    SettingSpec(
        key="scanner_fail_mode",
        label="Virus scanner failure mode",
        description=(
            "What happens to an upload when the scanner is down: closed refuses it, open lets it through. "
            "Open is refused in production. Stored now; read by US-099."
        ),
        group="uploads",
        kind="choice",
        env_field=None,
        fallback="closed",
        choices=("closed", "open"),
        in_use=False,
    ),
)

_BY_KEY: dict[str, SettingSpec] = {s.key: s for s in SPECS}


class UnknownSetting(KeyError):  # noqa: N818 - a lookup miss, translated to a 404 by the service
    pass


class SettingRejected(Exception):  # noqa: N818 - a value object the service turns into a 422
    def __init__(self, message: str, *, reason: str, details: Mapping[str, object] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.reason = reason
        self.details: dict[str, object] = dict(details or {})


def spec_for(key: str) -> SettingSpec:
    try:
        return _BY_KEY[key]
    except KeyError as exc:
        raise UnknownSetting(key) from exc


@dataclass(frozen=True)
class Bounds:
    minimum: int | None
    maximum: int | None
    max_source: Literal["env", "cap", "none"]


def default_for(spec: SettingSpec, env_value: int | None) -> int | bool | str:
    """What applies with no row: the environment value, or the built-in default for a switch."""
    if spec.env_field is None:
        return spec.fallback
    assert env_value is not None, spec.key  # the caller reads the field the spec names
    return env_value


def bounds_for(spec: SettingSpec, env_value: int | None) -> Bounds:
    """`[minimum, ceiling]` for a number. The ceiling is the environment value, further limited by the
    setting's absolute cap; an environment value of 0 (no limit) leaves the cap as the ceiling."""
    if spec.kind != "int":
        return Bounds(None, None, "none")
    assert env_value is not None, spec.key
    env = env_value
    if env > 0:
        ceiling = min(env, spec.absolute_max) if spec.absolute_max else env
        source: Literal["env", "cap", "none"] = "env" if ceiling == env else "cap"
    else:
        ceiling = spec.absolute_max
        source = "cap"
    return Bounds(min(spec.minimum, ceiling), ceiling, source)


def validate(spec: SettingSpec, value: object, env_value: int | None, app_env: str) -> int | bool | str:
    """The value, if the panel may store it; `SettingRejected` naming the bound otherwise."""
    if spec.kind == "bool":
        if not isinstance(value, bool):
            raise SettingRejected(f"{spec.label} takes on or off.", reason="wrong_type")
        return value
    if spec.kind == "choice":
        if not isinstance(value, str) or value not in spec.choices:
            raise SettingRejected(
                f"{spec.label} must be one of: {', '.join(spec.choices)}.",
                reason="not_a_choice",
                details={"choices": list(spec.choices)},
            )
        if spec.key == "scanner_fail_mode" and value == "open" and app_env == "production":
            raise SettingRejected(
                "The scanner cannot be set to fail open in production; it stays closed.",
                reason="production_fail_open",
                details={"allowed": ["closed"]},
            )
        return value
    if isinstance(value, bool) or not isinstance(value, int):
        raise SettingRejected(f"{spec.label} must be a whole number.", reason="wrong_type")
    b = bounds_for(spec, env_value)
    assert b.minimum is not None and b.maximum is not None
    if value < b.minimum:
        raise SettingRejected(
            f"{spec.label} cannot go below {b.minimum}; a limit cannot be switched off from the panel.",
            reason="below_minimum",
            details={"bound": "minimum", "minimum": b.minimum, "maximum": b.maximum},
        )
    if value > b.maximum:
        where = "the environment ceiling" if b.max_source == "env" else "the absolute cap"
        raise SettingRejected(
            f"{spec.label} cannot go above {b.maximum} ({where}).",
            reason="above_maximum",
            details={"bound": "maximum", "minimum": b.minimum, "maximum": b.maximum},
        )
    return value


def effective(
    spec: SettingSpec, stored: object, env_value: int | None, app_env: str, *, present: bool
) -> int | bool | str:
    """The value in force: the stored one when it is valid inside today's bounds, else the default.

    A stored number above the ceiling is clamped to it (the environment was lowered after the row was
    written); one below the minimum, of the wrong type or, for the scanner in production, open is ignored.
    """
    default = default_for(spec, env_value)
    if not present:
        return default
    if spec.kind == "int":
        if isinstance(stored, bool) or not isinstance(stored, int):
            return default
        b = bounds_for(spec, env_value)
        assert b.minimum is not None and b.maximum is not None
        if stored < b.minimum:
            return default
        return min(stored, b.maximum)
    try:
        return validate(spec, stored, env_value, app_env)
    except SettingRejected:
        return default
