"""PermitFlow Telegram command bot (US-077). Standard library only. Long-polls the Telegram Bot API,
answers a fixed set of commands from one chat by querying Prometheus, and formats replies in Telegram
HTML. It reads nothing but Prometheus and writes nothing anywhere; the alerts and the hourly digest
come from Grafana, not from here.

Environment: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID (the only chat answered), PROMETHEUS_URL
(default http://prometheus:9090), DASHBOARD_URL (link at the foot of every reply)."""

import json
import os
import sys
import time
import urllib.parse
import urllib.request

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = str(os.environ["TELEGRAM_CHAT_ID"])
PROM = os.environ.get("PROMETHEUS_URL", "http://prometheus:9090").rstrip("/")
DASHBOARD = os.environ.get("DASHBOARD_URL", "https://grafana.dev.permitflow.space/d/permitflow/permitflow")
API = f"https://api.telegram.org/bot{TOKEN}"
PRICE_IN, PRICE_CACHED, PRICE_OUT = 0.40, 0.10, 1.60  # USD per million tokens, gpt-4.1-mini list price
RULE = "━━━━━━━━━━━━━━━━━━━━━━"

HELP = (
    "<b>PermitFlow monitor</b>\n"
    "/status  ·  every environment in one message\n"
    "/dev  ·  development only\n"
    "/prod  ·  production only\n"
    "/checks  ·  the document checks in the last hour\n"
    "/cost  ·  what the checks cost (list price)\n"
    "/queue  ·  applications by status, who is waiting\n"
    "/alerts  ·  rules firing right now\n"
    "/help  ·  this list\n"
    f"{RULE}\nDashboard  {DASHBOARD}"
)


def prom(expr: str) -> float | None:
    url = f"{PROM}/api/v1/query?" + urllib.parse.urlencode({"query": expr})
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            data = json.load(r)["data"]["result"]
    except Exception:  # noqa: BLE001 - one failed query must not kill the reply
        return None
    if not data:
        return None
    try:
        v = float(data[0]["value"][1])
    except (KeyError, ValueError, IndexError):
        return None
    return None if v != v else v  # NaN -> None


def prom_series(expr: str) -> list[tuple[dict, float]]:
    url = f"{PROM}/api/v1/query?" + urllib.parse.urlencode({"query": expr})
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            return [(row["metric"], float(row["value"][1])) for row in json.load(r)["data"]["result"]]
    except Exception:  # noqa: BLE001
        return []


def environments() -> list[str]:
    envs = sorted({m.get("environment", "") for m, _ in prom_series('up{job="permitflow-api"}')} - {""})
    order = {"development": 0, "production": 1, "local": 2}
    return sorted(envs, key=lambda e: order.get(e, 9))


def n(v: float | None, fmt: str = "%.0f", none: str = "n/a") -> str:
    return none if v is None else fmt % v


def cost_expr(e: str) -> str:
    return (f'((sum(increase(permitflow_openai_tokens_total{{{e}, kind="prompt"}}[1h])) - sum(increase(permitflow_openai_tokens_total{{{e}, kind="cached"}}[1h]))) * {PRICE_IN}'
            f' + sum(increase(permitflow_openai_tokens_total{{{e}, kind="cached"}}[1h])) * {PRICE_CACHED}'
            f' + sum(increase(permitflow_openai_tokens_total{{{e}, kind="completion"}}[1h])) * {PRICE_OUT}) / 1e6')


def build_of(env: str) -> str:
    """The version and commit the API in this environment reports (permitflow_build_info), or n/a."""
    rows = prom_series(f'max by (version, commit) (permitflow_build_info{{environment="{env}"}})')
    if not rows:
        return "n/a"
    m = rows[-1][0]
    return f"{m.get('version', '?')}  ({m.get('commit', '?')})"


def section_status(env: str) -> str:
    e = f'environment="{env}"'
    up = prom(f'min(up{{job="permitflow-api", {e}}})')
    api = "n/a" if up is None else ("up" if up >= 1 else "DOWN")
    build = build_of(env)
    rpm = prom(f'sum(rate(permitflow_http_requests_total{{{e}}}[5m])) * 60')
    p995 = prom(f'histogram_quantile(0.995, sum by (le) (rate(permitflow_http_request_seconds_bucket{{{e}}}[5m]))) * 1000')
    err = prom(f'sum(rate(permitflow_http_requests_total{{{e}, status=~"5.."}}[5m])) / sum(rate(permitflow_http_requests_total{{{e}}}[5m]))')
    checks = prom(f'sum(increase(permitflow_verification_runs_total{{{e}}}[1h]))')
    spend = prom(cost_expr(e))
    apps = prom(f'sum(permitflow_applications{{{e}}})')
    officer = prom(f'sum(permitflow_applications{{{e}, status=~"application_received|under_review|pre_site_resubmitted|site_visit_scheduled|site_visit_done|post_site_clarification_resubmitted|pending_approval"}})')
    operator = prom(f'sum(permitflow_applications{{{e}, status=~"pending_pre_site_resubmission|awaiting_post_site_clarification|pending_post_site_resubmission"}})')
    quiet = not rpm  # no request in the last five minutes: latency and error share have no meaning
    traffic = ("Requests  <b>0</b> / min   ·   <i>quiet for five minutes</i>" if quiet else
               f"Requests  <b>{n(rpm)}</b> / min   ·   p99.5  <b>{n(p995)}</b> ms   ·   5xx  <b>{n((err or 0) * 100, '%.1f')} %</b>")
    return (f"<b>{env.capitalize()}</b>  ·  API {api}  ·  version <b>{build}</b>\n{traffic}\n"
            f"Checks (1 h)  <b>{n(checks, none='0')}</b>   ·   spend  <b>USD {n(spend, '%.3f', '0.000')}</b>\n"
            f"Applications  <b>{n(apps)}</b>   ·   officer's turn  <b>{n(officer)}</b>   ·   operator's turn  <b>{n(operator)}</b>")


def status(envs: list[str], title: str) -> str:
    if not envs:
        return f"<b>{title}</b>\nNo environment is being scraped yet."
    return f"<b>{title}</b>\n{RULE}\n" + f"\n{RULE}\n".join(section_status(e) for e in envs) + f"\n{RULE}\nDashboard  {DASHBOARD}"


def checks(envs: list[str]) -> str:
    parts = []
    for env in envs:
        e = f'environment="{env}"'
        by = prom_series(f'sum by (outcome) (increase(permitflow_verification_runs_total{{{e}}}[1h]))')
        outcomes = "   ·   ".join(f"{m.get('outcome')} <b>{v:.0f}</b>" for m, v in sorted(by, key=lambda x: -x[1]) if v >= 0.5) or "none in the last hour"
        p95 = prom(f'histogram_quantile(0.95, sum by (le) (rate(permitflow_verification_run_seconds_bucket{{{e}}}[1h])))')
        parts.append(f"<b>{env.capitalize()}</b>\n{outcomes}\np95 check time  <b>{n(p95, '%.1f')}</b> s  <i>(objective 180 s)</i>")
    return f"<b>Document checks · the last hour</b>\n{RULE}\n" + f"\n{RULE}\n".join(parts) + f"\n{RULE}\nDashboard  {DASHBOARD}"


def cost(envs: list[str]) -> str:
    parts = []
    for env in envs:
        e = f'environment="{env}"'
        tokens = {k: prom(f'sum(increase(permitflow_openai_tokens_total{{{e}, kind="{k}"}}[24h]))') or 0 for k in ("prompt", "cached", "completion")}
        spend24 = ((tokens["prompt"] - tokens["cached"]) * PRICE_IN + tokens["cached"] * PRICE_CACHED + tokens["completion"] * PRICE_OUT) / 1e6
        runs = prom(f'sum(increase(permitflow_verification_runs_total{{{e}, provider="openai"}}[24h]))') or 0
        per = spend24 / runs if runs else 0
        parts.append(f"<b>{env.capitalize()}</b>  ·  last 24 h\nTokens  prompt <b>{tokens['prompt']:.0f}</b>  ·  cached <b>{tokens['cached']:.0f}</b>  ·  output <b>{tokens['completion']:.0f}</b>\n"
                     f"Spend  <b>USD {spend24:.3f}</b>   ·   per check  <b>USD {per:.4f}</b>   ·   at this rate  <b>USD {spend24 * 30:.2f}</b> a month")
    return (f"<b>Cost of the document checks</b>\n<i>gpt-4.1-mini list price: 0.40 / 0.10 cached / 1.60 USD per million tokens; the invoice is the truth</i>\n{RULE}\n"
            + f"\n{RULE}\n".join(parts) + f"\n{RULE}\nDashboard  {DASHBOARD}")


def queue(envs: list[str]) -> str:
    parts = []
    for env in envs:
        e = f'environment="{env}"'
        by = [(m.get("status"), v) for m, v in prom_series(f'permitflow_applications{{{e}}}') if v > 0]
        lines = "\n".join(f"{s}  <b>{v:.0f}</b>" for s, v in sorted(by, key=lambda x: -x[1])) or "no applications"
        moved = prom(f'sum(increase(permitflow_transitions_total{{{e}}}[1h]))')
        post_site = prom(f'sum(permitflow_applications{{{e}, status=~"site_visit_scheduled|site_visit_done|awaiting_post_site_clarification|pending_post_site_resubmission|post_site_clarification_resubmitted"}})')
        checklists = prom(f'sum(increase(permitflow_checklists_submitted_total{{{e}}}[24h]))')
        rounds = prom(f'sum(increase(permitflow_clarification_rounds_total{{{e}}}[24h]))')
        parts.append(f"<b>{env.capitalize()}</b>\n{lines}\ntransitions in the last hour  <b>{n(moved, none='0')}</b>\n"
                     f"post-site (visit to clarification)  <b>{n(post_site, none='0')}</b>   ·   checklists (24 h)  <b>{n(checklists, none='0')}</b>   ·   rounds (24 h)  <b>{n(rounds, none='0')}</b>")
    return f"<b>The queue</b>\n{RULE}\n" + f"\n{RULE}\n".join(parts) + f"\n{RULE}\nDashboard  {DASHBOARD}"


def alerts() -> str:
    try:
        with urllib.request.urlopen(f"{PROM}/api/v1/alerts", timeout=15) as r:
            active = json.load(r)["data"]["alerts"]
    except Exception:  # noqa: BLE001
        return "Prometheus did not answer."
    firing = [a for a in active if a.get("state") == "firing"]
    if not firing:
        return f"<b>Alerts</b>\nNothing is firing. Six rules watch the objective (API down, 5xx above 1 %, p99.5 above 500 ms, checks failing above 20 %, checks slower than 3 min, rate limiting).\n{RULE}\nDashboard  {DASHBOARD}"
    lines = [f"<b>{a['labels'].get('alertname')}</b>  ·  {a['labels'].get('environment', '')}  ·  {a['labels'].get('severity', '')}\n{a.get('annotations', {}).get('summary', '')}" for a in firing]
    return f"<b>Alerts firing</b>\n{RULE}\n" + f"\n{RULE}\n".join(lines) + f"\n{RULE}\nDashboard  {DASHBOARD}"


def reply(text: str) -> None:
    body = json.dumps({"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True}).encode()
    req = urllib.request.Request(f"{API}/sendMessage", data=body, headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=15).read()
    except Exception as exc:  # noqa: BLE001
        print("send failed:", exc, file=sys.stderr)


def handle(command: str) -> str:
    envs = environments()
    if command in ("/start", "/help"):
        return HELP
    if command == "/status":
        return status(envs, "PermitFlow · right now")
    if command == "/dev":
        return status([e for e in envs if e == "development"], "PermitFlow · development")
    if command == "/prod":
        return status([e for e in envs if e == "production"], "PermitFlow · production")
    if command == "/checks":
        return checks(envs)
    if command == "/cost":
        return cost(envs)
    if command == "/queue":
        return queue(envs)
    if command == "/alerts":
        return alerts()
    return "Not a command I know. /help lists them."


def main() -> None:
    offset = None
    print("permitflow telegram bot: polling", file=sys.stderr)
    while True:
        params = {"timeout": 50, "allowed_updates": json.dumps(["message"])}
        if offset is not None:
            params["offset"] = offset
        try:
            with urllib.request.urlopen(f"{API}/getUpdates?" + urllib.parse.urlencode(params), timeout=60) as r:
                updates = json.load(r)["result"]
        except Exception as exc:  # noqa: BLE001
            print("poll failed:", exc, file=sys.stderr)
            time.sleep(5)
            continue
        for u in updates:
            offset = u["update_id"] + 1
            msg = u.get("message") or {}
            if str(msg.get("chat", {}).get("id")) != CHAT_ID:
                continue  # one chat only; anyone else who finds the bot gets silence
            text = (msg.get("text") or "").strip().split()[0].split("@")[0].lower() if msg.get("text") else ""
            if text.startswith("/"):
                reply(handle(text))


if __name__ == "__main__":
    main()
