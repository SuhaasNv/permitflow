"""The same three requests as permitflow.js without k6 (US-086): threads of httpx against a running
API, p50 and p95 per request kind, exit 1 when a budget is missed. Use k6 when it is installed; this
runner exists so the numbers can be produced on a machine without it.

    uv run python scripts/load/run_load.py --base http://localhost:8001/api/v1 --app <checklist case id>
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import os
import statistics
import time
from urllib.parse import urlparse

import httpx

BUDGETS_MS = {"checklist_save": 300, "admin_overview": 500, "audit_feed": 200}


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, round(fraction * len(ordered) + 0.5) - 1))
    return ordered[index]


def local_target(base: str) -> bool:
    """Only a local API or a host set aside for load runs is ever driven by this script."""
    host = urlparse(base).hostname or ""
    return host in ("localhost", "127.0.0.1", "::1") or "load" in host or "scratch" in host


def login(client: httpx.Client, base: str, email: str, password: str) -> dict[str, str]:
    r = client.post(f"{base}/auth/login", json={"email": email, "password": password, "take_over": True})
    r.raise_for_status()
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://localhost:8001/api/v1")
    parser.add_argument("--app", required=True, help="the application id with a confirmed visit")
    parser.add_argument("--seconds", type=int, default=20)
    parser.add_argument("--vus", type=int, default=5)
    args = parser.parse_args()
    if not local_target(args.base):
        # The demo credentials are the same everywhere, so nothing else stands between a mistyped base
        # and a load run against a live environment (review finding, 21 Sep).
        raise SystemExit(f"refusing: {args.base} is not a local host or one named for load runs")
    password = os.environ.get("SEED_PASSWORD", "PermitFlow!2026")
    with httpx.Client(timeout=30) as c:
        officer = login(c, args.base, "officer@permitflow.example.sg", password)
        admin = login(c, args.base, "admin@permitflow.example.sg", password)
        schema = c.get(f"{args.base}/checklist-schema", headers=officer).json()
        keys = [i["key"] for s in schema["sections"] for i in s["items"]]
        c.post(f"{args.base}/officer/applications/{args.app}/checklist", headers=officer)

    def worker(kind: str, vu: int) -> list[float]:
        out: list[float] = []
        with httpx.Client(timeout=30) as c:
            deadline = time.monotonic() + args.seconds
            n = 0
            while time.monotonic() < deadline:
                n += 1
                if kind == "checklist_save":
                    current = c.get(
                        f"{args.base}/officer/applications/{args.app}/checklist", headers=officer
                    ).json()
                    items = [
                        {
                            "key": k,
                            "result": "unsatisfactory" if i % 3 == 0 else "satisfactory",
                            "comment": "x" * 1800 if i % 3 == 0 else None,
                            "needs_clarification": i % 6 == 0,
                        }
                        for i, k in enumerate(keys)
                    ]
                    t = time.perf_counter()
                    r = c.put(
                        f"{args.base}/officer/applications/{args.app}/checklist",
                        headers=officer,
                        json={"items": items, "version": current["version"], "save_id": f"{vu}-{n}"},
                    )
                    out.append((time.perf_counter() - t) * 1000)
                    assert r.status_code in (200, 409), r.text
                elif kind == "admin_overview":
                    t = time.perf_counter()
                    r = c.get(f"{args.base}/admin/overview", headers=admin)
                    out.append((time.perf_counter() - t) * 1000)
                    assert r.status_code == 200, r.text
                else:
                    cursor = None
                    for _ in range(3):
                        url = f"{args.base}/admin/audit-feed?limit=50" + (
                            f"&before={cursor}" if cursor else ""
                        )
                        t = time.perf_counter()
                        r = c.get(url, headers=admin)
                        out.append((time.perf_counter() - t) * 1000)
                        assert r.status_code == 200, r.text
                        cursor = r.json()["next_cursor"]
                        if not cursor:
                            break
        return out

    failed = False
    for kind in BUDGETS_MS:
        vus = args.vus * 2 if kind == "audit_feed" else args.vus
        with cf.ThreadPoolExecutor(max_workers=vus) as pool:
            batches = pool.map(worker, [kind] * vus, range(vus))
            samples = [s for batch in batches for s in batch]
        p50, p95 = statistics.median(samples), percentile(samples, 0.95)
        ok = p95 < BUDGETS_MS[kind]
        failed |= not ok
        verdict = "ok" if ok else "MISSED"
        print(
            f"{kind:16s} n={len(samples):5d} p50={p50:7.1f} ms p95={p95:7.1f} ms "
            f"budget={BUDGETS_MS[kind]} ms {verdict}"
        )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
