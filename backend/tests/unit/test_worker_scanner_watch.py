"""The worker's clamd watch: one alert when the scanner goes down, one when it is back, none in between."""

import pytest
from prometheus_client import REGISTRY

from app import worker as worker_module
from app.core.settings import get_settings
from app.infra.clamd import ScannerError
from app.worker import Worker


class FakeClamd:
    def __init__(self) -> None:
        self.up = True

    def ping(self) -> None:
        if not self.up:
            raise ScannerError("clamd connection failed: ConnectionRefusedError")


@pytest.fixture
def clamd(monkeypatch: pytest.MonkeyPatch) -> FakeClamd:
    fake = FakeClamd()
    monkeypatch.setattr(get_settings(), "scan_mode", "enforce")
    monkeypatch.setattr(worker_module, "client_from_settings", lambda: fake)
    return fake


@pytest.fixture
def alerts(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    sent: list[str] = []
    monkeypatch.setattr(worker_module, "alert_scanner_down", lambda: sent.append("down"))
    monkeypatch.setattr(worker_module, "alert_scanner_back", lambda: sent.append("back"))
    return sent


def test_down_alerts_once_and_recovery_alerts_once(clamd: FakeClamd, alerts: list[str]) -> None:
    w = Worker()
    w.check_scanner()
    assert alerts == [] and REGISTRY.get_sample_value("permitflow_scanner_up") == 1
    clamd.up = False
    for _ in range(3):  # still down: no repeat
        w.check_scanner()
    assert alerts == ["down"] and REGISTRY.get_sample_value("permitflow_scanner_up") == 0
    clamd.up = True
    for _ in range(3):  # still up: no repeat
        w.check_scanner()
    assert alerts == ["down", "back"] and REGISTRY.get_sample_value("permitflow_scanner_up") == 1
    clamd.up = False
    w.check_scanner()
    assert alerts == ["down", "back", "down"]  # a second outage alerts again


def test_a_scanner_that_is_down_at_start_alerts(clamd: FakeClamd, alerts: list[str]) -> None:
    clamd.up = False
    Worker().check_scanner()
    assert alerts == ["down"]


def test_nothing_is_pinged_with_the_scan_off(monkeypatch: pytest.MonkeyPatch, alerts: list[str]) -> None:
    def boom() -> None:
        raise AssertionError("clamd must not be contacted")

    monkeypatch.setattr(get_settings(), "scan_mode", "off")
    monkeypatch.setattr(worker_module, "client_from_settings", boom)
    Worker().check_scanner()
    assert alerts == []
