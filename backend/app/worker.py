"""The verification worker (US-098, ADR-016): `python -m app.worker`, the same image as the API.

It runs the document checks that the API only queued (`VERIFICATION_MODE=worker`). `verification_runs` is
the queue; there is no broker. The loop:

- wakes on Postgres `NOTIFY verification_runs`, and polls every `POLL_SECONDS` in case a notification was
  missed or a slot freed;
- claims the oldest queued run with one atomic statement and commits the claim at once; a run is then
  held by its lease, not by an open transaction;
- runs up to `WORKER_CONCURRENCY` checks at a time (the administrator's panel value, read live);
- leaves queued runs alone while the administrator has paused the AI (US-101); they run after unpause;
- every `REAP_SECONDS` takes back runs whose lease has expired (requeue, or `dead` after three claims);
- on SIGTERM stops claiming, gives running checks `SHUTDOWN_GRACE_SECONDS` to finish, and hands any
  still unfinished run back to the queue.

Everything it executes is idempotent: a run executed twice (a lease that expired under a slow check) writes
its result once, because the write is fenced on the lease holder.
"""

import logging
import os
import signal
import socket
import threading
import time
import uuid
from types import FrameType

from prometheus_client import start_http_server

from app.core.logging import configure_logging
from app.core.settings import get_settings
from app.infra.db import listen_connection, session_factory, set_lock_timeout
from app.services.metrics import refresh_queue_gauges
from app.services.platform_settings import live
from app.services.verification import claim_next_run, execute_run, reap_expired_runs, release_run

logger = logging.getLogger("permitflow.worker")

CHANNEL = "verification_runs"
POLL_SECONDS = 2.0
REAP_SECONDS = 60.0
GAUGE_SECONDS = 10.0
# `docker stop` waits 10 s before SIGKILL; whatever is still unfinished after this goes back to the queue.
SHUTDOWN_GRACE_SECONDS = 8.0


class Worker:
    def __init__(self) -> None:
        self.id = f"{socket.gethostname()[:30]}-{os.getpid()}-{uuid.uuid4().hex[:6]}"
        self.stop = threading.Event()
        self.wake = threading.Event()
        # Keyed by (run, claim): the same run can be claimed again while a hung thread of its old claim lives.
        self._active: dict[tuple[uuid.UUID, str], threading.Thread] = {}
        self._lock = threading.Lock()

    # ---- the loop ----

    def serve(self) -> None:
        settings = get_settings()
        settings.validate_for_startup()
        configure_logging()
        set_lock_timeout(settings.worker_lock_timeout_seconds)
        live().refresh()
        start_http_server(settings.worker_metrics_port)
        if settings.verification_mode != "worker":
            logger.warning("worker_started_in_inline_mode", extra={"extra_fields": {"worker": self.id}})
        signal.signal(signal.SIGTERM, self._on_signal)
        signal.signal(signal.SIGINT, self._on_signal)
        threading.Thread(target=self._listen, name="worker-listen", daemon=True).start()
        logger.info("worker_started", extra={"extra_fields": {"worker": self.id}})

        last_reap = last_gauges = 0.0
        while not self.stop.is_set():
            now = time.monotonic()
            if now - last_reap >= REAP_SECONDS:
                self.reap()
                last_reap = now
            if now - last_gauges >= GAUGE_SECONDS:
                self.publish_gauges()
                last_gauges = now
            self.fill_slots()
            self.wake.wait(POLL_SECONDS)
            self.wake.clear()
        self.drain()

    def _on_signal(self, signum: int, frame: FrameType | None) -> None:
        self.stop.set()
        self.wake.set()

    def _listen(self) -> None:
        while not self.stop.is_set():
            try:
                with listen_connection() as conn:
                    conn.execute(f"LISTEN {CHANNEL}")
                    while not self.stop.is_set():
                        for _ in conn.notifies(timeout=1.0):
                            self.wake.set()
            except Exception:  # noqa: BLE001 - polling still works; reconnect after a pause
                logger.exception("worker_listen_failed")
                self.stop.wait(POLL_SECONDS)

    # ---- one step each, so tests can drive them ----

    def free_slots(self) -> int:
        with self._lock:
            for key in [k for k, t in self._active.items() if not t.is_alive()]:
                del self._active[key]
            return max(1, live().int_value("worker_concurrency")) - len(self._active)

    def fill_slots(self) -> int:
        """Claim queued runs into the free slots; returns how many were started. Nothing is claimed while
        the AI is paused (US-101): the runs stay queued."""
        started = 0
        try:
            if live().bool_value("ai_paused"):
                return 0
            for _ in range(self.free_slots()):
                # One id per claim, not per worker: if a hung thread outlives its lease and this worker
                # reclaims the run, the old thread is no longer the holder and its write is dropped.
                claim = f"{self.id}:{uuid.uuid4().hex[:8]}"
                run_id = claim_next_run(claim)
                if run_id is None:
                    break
                thread = threading.Thread(
                    target=self._work, args=(run_id, claim), name=f"run-{run_id}", daemon=True
                )
                with self._lock:
                    self._active[(run_id, claim)] = thread
                thread.start()
                started += 1
        except Exception:  # noqa: BLE001 - a database blip must not stop the worker
            logger.exception("worker_claim_failed")
        return started

    def _work(self, run_id: uuid.UUID, claim: str) -> None:
        try:
            execute_run(run_id, claim)
        except Exception:  # noqa: BLE001 - execute_run records failures itself; an expired lease covers the rest
            logger.exception("worker_run_crashed", extra={"extra_fields": {"run_id": str(run_id)}})
        finally:
            self.wake.set()

    def reap(self) -> None:
        try:
            requeued, dead = reap_expired_runs()
            if requeued or dead:
                logger.warning("worker_reaped", extra={"extra_fields": {"requeued": requeued, "dead": dead}})
        except Exception:  # noqa: BLE001
            logger.exception("worker_reap_failed")

    def publish_gauges(self) -> None:
        try:
            with session_factory()() as db:
                refresh_queue_gauges(db)
        except Exception:  # noqa: BLE001
            logger.exception("worker_gauges_failed")

    def drain(self) -> None:
        """Shutdown: let running checks finish for a few seconds, then release what is left."""
        deadline = time.monotonic() + SHUTDOWN_GRACE_SECONDS
        with self._lock:
            running = dict(self._active)
        for thread in running.values():
            thread.join(max(0.0, deadline - time.monotonic()))
        for (run_id, claim), thread in running.items():
            if thread.is_alive():
                logger.warning("worker_released_run", extra={"extra_fields": {"run_id": str(run_id)}})
                try:
                    release_run(run_id, claim)
                except Exception:  # noqa: BLE001 - the lease expires and the reaper takes it back
                    logger.exception("worker_release_failed")
        logger.info("worker_stopped", extra={"extra_fields": {"worker": self.id}})


def main() -> None:
    Worker().serve()


if __name__ == "__main__":
    main()
