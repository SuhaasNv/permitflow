"""US-101, domain layer: the bounds are the control. The panel moves a value inside [minimum, ceiling] and
cannot remove, switch off or raise a limit; a stored value outside today's bounds never takes effect."""

import pytest

from app.core.settings import Settings
from app.domain.platform_settings import (
    SPECS,
    UPLOAD_HARD_MAX_BYTES,
    SettingRejected,
    UnknownSetting,
    bounds_for,
    default_for,
    effective,
    spec_for,
    validate,
)

MB = 1024 * 1024


def test_every_environment_backed_setting_names_a_real_settings_field() -> None:
    s = Settings(_env_file=None)  # type: ignore[call-arg]
    for spec in SPECS:
        if spec.env_field is not None:
            assert hasattr(s, spec.env_field), spec.key


def test_defaults_are_the_environment_values_so_an_empty_table_changes_nothing() -> None:
    s = Settings(_env_file=None)  # type: ignore[call-arg]
    for spec in SPECS:
        if spec.env_field is not None:
            assert default_for(spec, getattr(s, spec.env_field)) == getattr(s, spec.env_field)
    assert default_for(spec_for("ai_paused"), None) is False
    assert default_for(spec_for("scanner_fail_mode"), None) == "closed"
    assert default_for(spec_for("telegram_per_check_messages"), None) is False


def test_the_ceiling_is_the_environment_value() -> None:
    b = bounds_for(spec_for("rate_limit_per_minute"), 240)
    assert (b.minimum, b.maximum, b.max_source) == (10, 240, "env")


def test_an_environment_value_of_zero_means_no_limit_and_the_cap_becomes_the_ceiling() -> None:
    spec = spec_for("ai_runs_per_day")
    b = bounds_for(spec, 0)
    assert b.maximum == spec.absolute_max and b.max_source == "cap"
    # The panel can still only set a real limit, never 0 and never above the cap.
    assert validate(spec, 500, 0, "production") == 500
    with pytest.raises(SettingRejected) as below:
        validate(spec, 0, 0, "production")
    assert below.value.reason == "below_minimum"
    with pytest.raises(SettingRejected) as above:
        validate(spec, spec.absolute_max + 1, 0, "production")
    assert above.value.reason == "above_maximum"


def test_upload_size_never_exceeds_10_mb_even_if_the_environment_does() -> None:
    spec = spec_for("upload_max_bytes")
    b = bounds_for(spec, 50 * MB)
    assert b.maximum == UPLOAD_HARD_MAX_BYTES and b.max_source == "cap"
    with pytest.raises(SettingRejected):
        validate(spec, UPLOAD_HARD_MAX_BYTES + 1, 50 * MB, "development")
    assert validate(spec, UPLOAD_HARD_MAX_BYTES, 50 * MB, "development") == UPLOAD_HARD_MAX_BYTES


def test_a_minimum_above_a_tiny_environment_ceiling_gives_way_to_it() -> None:
    b = bounds_for(spec_for("rate_limit_per_minute"), 4)
    assert (b.minimum, b.maximum) == (4, 4)


@pytest.mark.parametrize(
    ("key", "env", "value", "reason", "bound"),
    [
        ("rate_limit_per_minute", 240, 241, "above_maximum", "maximum"),
        ("rate_limit_per_minute", 240, 9, "below_minimum", "minimum"),
        ("rate_limit_per_minute", 240, 0, "below_minimum", "minimum"),
        ("rate_limit_per_minute", 240, -5, "below_minimum", "minimum"),
        ("login_attempts_per_minute", 20, 2, "below_minimum", "minimum"),
        ("ai_runs_per_user_per_day", 60, 61, "above_maximum", "maximum"),
        ("max_drafts_per_user", 20, 0, "below_minimum", "minimum"),
        ("ai_max_text_chars", 20_000, 999, "below_minimum", "minimum"),
        ("worker_concurrency", 2, 3, "above_maximum", "maximum"),
    ],
)
def test_out_of_bounds_numbers_are_refused_naming_the_bound(
    key: str, env: int, value: int, reason: str, bound: str
) -> None:
    with pytest.raises(SettingRejected) as exc:
        validate(spec_for(key), value, env, "development")
    assert exc.value.reason == reason
    assert exc.value.details["bound"] == bound
    assert str(exc.value.details[bound]) in exc.value.message


@pytest.mark.parametrize("value", ["12", 12.5, None, True, [12]])
def test_a_number_setting_takes_only_a_whole_number(value: object) -> None:
    with pytest.raises(SettingRejected) as exc:
        validate(spec_for("rate_limit_per_minute"), value, 240, "development")
    assert exc.value.reason == "wrong_type"


def test_switches_take_only_a_boolean_and_choices_only_their_choices() -> None:
    assert validate(spec_for("ai_paused"), True, None, "production") is True
    for bad in (1, "true", None):
        with pytest.raises(SettingRejected):
            validate(spec_for("ai_paused"), bad, None, "production")
    with pytest.raises(SettingRejected) as exc:
        validate(spec_for("scanner_fail_mode"), "maybe", None, "development")
    assert exc.value.reason == "not_a_choice"


def test_the_scanner_may_fail_open_in_development_but_never_in_production() -> None:
    spec = spec_for("scanner_fail_mode")
    assert validate(spec, "open", None, "development") == "open"
    assert validate(spec, "open", None, "test") == "open"
    with pytest.raises(SettingRejected) as exc:
        validate(spec, "open", None, "production")
    assert exc.value.reason == "production_fail_open"
    assert validate(spec, "closed", None, "production") == "closed"


def test_effective_follows_the_environment_without_a_row() -> None:
    spec = spec_for("rate_limit_per_minute")
    assert effective(spec, None, 240, "production", present=False) == 240


def test_effective_uses_a_valid_stored_value() -> None:
    spec = spec_for("rate_limit_per_minute")
    assert effective(spec, 100, 240, "production", present=True) == 100


def test_a_stored_value_above_a_ceiling_lowered_since_is_clamped() -> None:
    spec = spec_for("rate_limit_per_minute")
    assert effective(spec, 200, 120, "production", present=True) == 120


def test_a_stored_value_below_the_minimum_or_of_the_wrong_type_is_ignored() -> None:
    spec = spec_for("rate_limit_per_minute")
    for bad in (0, 3, -1, "50", True, None, 1.5):
        assert effective(spec, bad, 240, "production", present=True) == 240


def test_a_stored_fail_open_is_ignored_in_production() -> None:
    spec = spec_for("scanner_fail_mode")
    assert effective(spec, "open", None, "production", present=True) == "closed"
    assert effective(spec, "open", None, "development", present=True) == "open"


def test_unknown_key() -> None:
    with pytest.raises(UnknownSetting):
        spec_for("jwt_secret")


def test_the_editable_settings_are_exactly_the_eleven_of_the_story() -> None:
    assert {s.key for s in SPECS} == {
        "rate_limit_per_minute",
        "login_attempts_per_minute",
        "ai_runs_per_user_per_day",
        "ai_runs_per_day",
        "max_drafts_per_user",
        "upload_max_bytes",
        "ai_max_text_chars",
        "worker_concurrency",
        "ai_paused",
        "telegram_per_check_messages",
        "scanner_fail_mode",
    }
