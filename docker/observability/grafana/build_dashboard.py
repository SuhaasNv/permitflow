#!/usr/bin/env python3
"""Generates dashboards/permitflow.json (US-077). Run after editing; the JSON is what Grafana provisions.
Every query is filtered by the `environment` variable (local, development, production)."""

import json
from pathlib import Path

ENV = 'environment=~"$environment"'
DS = {"type": "prometheus", "uid": "prometheus"}
# OpenAI list prices for gpt-4.1-mini in USD per million tokens (developers.openai.com/api/docs/pricing, checked
# 20 Sep 2026): input 0.40, cached input 0.10, output 1.60. An estimate: the invoice is the truth.
PRICE_IN, PRICE_CACHED, PRICE_OUT = 0.40, 0.10, 1.60
COST = (
    f'(sum(increase({{M_PROMPT}}[$__range])) - sum(increase({{M_CACHED}}[$__range]))) * {PRICE_IN} / 1e6'
    f' + sum(increase({{M_CACHED}}[$__range])) * {PRICE_CACHED} / 1e6'
    f' + sum(increase({{M_COMPLETION}}[$__range])) * {PRICE_OUT} / 1e6'
)


def m(name: str, sel: str = "") -> str:
    """A metric selector with the environment filter."""
    return f"{name}{{{ENV}{', ' + sel if sel else ''}}}"


def panel(pid, title, exprs, x, y, w=12, h=8, unit=None, kind="timeseries", stack=False, extra=None, desc=None):
    p = {
        "id": pid, "type": kind, "title": title, "gridPos": {"x": x, "y": y, "w": w, "h": h}, "datasource": DS,
        "targets": [{"refId": chr(65 + i), "expr": e, "legendFormat": lg, "datasource": DS} for i, (e, lg) in enumerate(exprs)],
        "fieldConfig": {"defaults": {}, "overrides": []}, "options": {},
    }
    if desc:
        p["description"] = desc
    if unit:
        p["fieldConfig"]["defaults"]["unit"] = unit
    if kind == "timeseries":
        p["options"] = {"legend": {"displayMode": "list", "placement": "bottom"}, "tooltip": {"mode": "multi"}}
        p["fieldConfig"]["defaults"]["custom"] = {"lineWidth": 2, "fillOpacity": 35 if stack else 12, "stacking": {"mode": "normal" if stack else "none"}}
    if extra:
        for k, v in extra.items():
            if isinstance(v, dict) and isinstance(p.get(k), dict):
                p[k].update(v)
            else:
                p[k] = v
    return p


def stat(pid, title, expr, x, y, w, h=4, unit="short", color="blue", mappings=None, thresholds=None, decimals=None):
    p = panel(pid, title, [(expr, title)], x, y, w, h, kind="stat")
    p["options"] = {"reduceOptions": {"calcs": ["lastNotNull"]}, "colorMode": "value", "graphMode": "none", "textMode": "value", "justifyMode": "center"}
    p["fieldConfig"]["defaults"] = {"unit": unit, "color": {"mode": "fixed", "fixedColor": color}}
    if decimals is not None:
        p["fieldConfig"]["defaults"]["decimals"] = decimals
    if mappings:
        p["fieldConfig"]["defaults"]["mappings"] = mappings
    if thresholds:
        p["fieldConfig"]["defaults"]["color"] = {"mode": "thresholds"}
        p["fieldConfig"]["defaults"]["thresholds"] = thresholds
    return p


def row(pid, title, y):
    return {"id": pid, "type": "row", "title": title, "gridPos": {"x": 0, "y": y, "w": 24, "h": 1}, "collapsed": False}


HEADER = (
    "<div style=\"text-align:center;padding:6px 0 2px\">"
    "<div style=\"font-size:34px;font-weight:700;letter-spacing:-0.5px\">PermitFlow observability layer</div>"
    "<div style=\"font-size:15px;opacity:.75;margin-top:6px\">Environment: <b>$environment</b> · "
    "Prometheus scrapes the API's <code>/api/v1/metrics</code> every 15 s · three questions: is the API healthy, "
    "are the document checks healthy, is the queue moving</div></div>"
)

up_map = [{"type": "value", "options": {"0": {"text": "DOWN", "color": "red"}, "1": {"text": "UP", "color": "green"}}}]
up_thr = {"mode": "absolute", "steps": [{"color": "red", "value": None}, {"color": "green", "value": 1}]}

panels = [
    {"id": 1, "type": "text", "title": "", "gridPos": {"x": 0, "y": 0, "w": 24, "h": 3}, "options": {"mode": "html", "content": HEADER}, "transparent": True},
    stat(2, "API", f'min({m("up", "job=\"permitflow-api\"")})', 0, 3, 4, mappings=up_map, thresholds=up_thr),
    stat(3, "Requests per minute", f'sum(rate({m("permitflow_http_requests_total")}[5m])) * 60', 4, 3, 4, unit="short", decimals=0),
    stat(4, "p99.5 latency (SLO 500 ms)", f'histogram_quantile(0.995, sum by (le) (rate({m("permitflow_http_request_seconds_bucket")}[5m])))', 8, 3, 4, unit="s",
         thresholds={"mode": "absolute", "steps": [{"color": "green", "value": None}, {"color": "orange", "value": 0.3}, {"color": "red", "value": 0.5}]}),
    stat(5, "Checks in the last hour", f'sum(increase({m("permitflow_verification_runs_total")}[1h]))', 12, 3, 4, unit="short", decimals=0, color="purple"),
    stat(6, "Applications", f'sum({m("permitflow_applications")})', 16, 3, 4, unit="short", decimals=0, color="blue"),
    stat(7, "Waiting on an officer", f'sum({m("permitflow_applications", "status=~\"application_received|pre_site_resubmitted|post_site_clarification_resubmitted|pending_approval\"")})', 20, 3, 4, unit="short", decimals=0, color="orange"),

    row(100, "Is the API healthy?", 7),
    panel(11, "Requests per second, by status class", [(f'sum by (class) (label_replace(rate({m("permitflow_http_requests_total")}[5m]), "class", "${{1}}xx", "status", "(.).*"))', "{{class}}")], 0, 8, unit="reqps", stack=True),
    panel(12, "Latency p50 / p95 / p99.5 (SLO: p99.5 under 500 ms)", [
        (f'histogram_quantile(0.5, sum by (le) (rate({m("permitflow_http_request_seconds_bucket")}[5m])))', "p50"),
        (f'histogram_quantile(0.95, sum by (le) (rate({m("permitflow_http_request_seconds_bucket")}[5m])))', "p95"),
        (f'histogram_quantile(0.995, sum by (le) (rate({m("permitflow_http_request_seconds_bucket")}[5m])))', "p99.5")], 12, 8, unit="s",
        extra={"fieldConfig": {"defaults": {"unit": "s", "custom": {"lineWidth": 2, "fillOpacity": 0, "stacking": {"mode": "none"}}, "thresholds": {"mode": "absolute", "steps": [{"color": "green", "value": None}, {"color": "red", "value": 0.5}]}}, "overrides": []}}),
    panel(13, "5xx share of answers (alert above 1 %)", [(f'(sum(rate({m("permitflow_http_requests_total", "status=~\"5..\"")}[5m])) or vector(0)) / sum(rate({m("permitflow_http_requests_total")}[5m]))', "5xx share")], 0, 16, unit="percentunit",
          extra={"fieldConfig": {"defaults": {"unit": "percentunit", "min": 0, "max": 1, "decimals": 1, "custom": {"lineWidth": 2, "fillOpacity": 12, "stacking": {"mode": "none"}}}, "overrides": []}}),
    panel(14, "Slowest routes, p95", [(f'topk(6, histogram_quantile(0.95, sum by (le, route) (rate({m("permitflow_http_request_seconds_bucket")}[5m]))))', "{{route}}")], 12, 16, unit="s"),
    panel(15, "Requests refused by the per-client rate limit", [(f'rate({m("permitflow_rate_limited_total")}[5m])', "refused/s")], 0, 24, w=12, h=6, unit="reqps",
          desc="240 requests a minute per client, 20 sign-in attempts; a refusal answers 429 with Retry-After."),
    panel(16, "Quota refusals (drafts, daily check limits)", [(f'sum by (quota) (increase({m("permitflow_quota_refusals_total")}[1h]))', "{{quota}}")], 12, 24, w=12, h=6, unit="short",
          desc="drafts: an operator already holds the maximum number of open drafts. ai_runs_per_user / ai_runs_per_day: the daily allowance of automatic document checks per applicant or for the whole platform is spent; the check is stored as unavailable and no model is called."),

    row(101, "Are the document checks healthy?", 30),
    panel(21, "Checks finished per hour, by outcome", [(f'sum by (outcome) (increase({m("permitflow_verification_runs_total")}[1h]))', "{{outcome}}")], 0, 31, unit="short", stack=True),
    panel(22, "Check time p50 / p95 (SLO: p95 under 3 min)", [
        (f'histogram_quantile(0.5, sum by (le) (rate({m("permitflow_verification_run_seconds_bucket")}[30m])))', "p50"),
        (f'histogram_quantile(0.95, sum by (le) (rate({m("permitflow_verification_run_seconds_bucket")}[30m])))', "p95")], 12, 31, unit="s"),
    panel(23, "Failed or unavailable share (alert above 20 %)", [(f'(sum(rate({m("permitflow_verification_runs_total", "outcome=~\"failed|unavailable\"")}[30m])) or vector(0)) / sum(rate({m("permitflow_verification_runs_total")}[30m]))', "share")], 0, 39, unit="percentunit",
          extra={"fieldConfig": {"defaults": {"unit": "percentunit", "min": 0, "max": 1, "decimals": 1, "custom": {"lineWidth": 2, "fillOpacity": 12, "stacking": {"mode": "none"}}}, "overrides": []}}),
    panel(24, "Checks by provider, per hour", [(f'sum by (provider) (increase({m("permitflow_verification_runs_total")}[1h]))', "{{provider}}")], 12, 39, unit="short", stack=True,
          desc="openai: the live model. mock: the deterministic provider (tests, CI, no key). none: refused by a quota before any provider ran."),

    row(103, "What are the document checks costing?", 47),
    stat(41, "Estimated OpenAI spend in the selected range", COST.format(M_PROMPT=m("permitflow_openai_tokens_total", 'kind="prompt"'), M_CACHED=m("permitflow_openai_tokens_total", 'kind="cached"'), M_COMPLETION=m("permitflow_openai_tokens_total", 'kind="completion"')), 0, 48, 6, h=7, unit="currencyUSD", decimals=4, color="green"),
    stat(42, "Tokens in the selected range", f'sum(increase({m("permitflow_openai_tokens_total", chr(107)+"ind!=\"cached\"")}[$__range]))', 6, 48, 6, h=7, unit="short", decimals=0, color="purple"),
    stat(43, "Cost per check (average, range)", COST.format(M_PROMPT=m("permitflow_openai_tokens_total", 'kind="prompt"'), M_CACHED=m("permitflow_openai_tokens_total", 'kind="cached"'), M_COMPLETION=m("permitflow_openai_tokens_total", 'kind="completion"')) + f' / sum(increase({m("permitflow_verification_runs_total", chr(112)+"rovider=\"openai\"")}[$__range]))', 12, 48, 6, h=7, unit="currencyUSD", decimals=5, color="green"),
    stat(44, "Projected monthly spend at this rate", COST.format(M_PROMPT=m("permitflow_openai_tokens_total", 'kind="prompt"'), M_CACHED=m("permitflow_openai_tokens_total", 'kind="cached"'), M_COMPLETION=m("permitflow_openai_tokens_total", 'kind="completion"')) + ' / ($__range_s / 2592000)', 18, 48, 6, h=7, unit="currencyUSD", decimals=2, color="orange"),
    panel(45, "Tokens per hour, by kind", [(f'sum by (kind) (increase({m("permitflow_openai_tokens_total")}[1h]))', "{{kind}}")], 0, 55, w=12, h=7, unit="short", stack=True,
          desc="prompt: everything sent to the model (the document text, the form section, the instructions). cached: the part of the prompt OpenAI served from its cache at a quarter of the price. completion: the model's answer."),
    panel(46, "Estimated spend per hour (USD)", [(f'(sum(increase({m("permitflow_openai_tokens_total", chr(107)+"ind=\"prompt\"")}[1h])) - sum(increase({m("permitflow_openai_tokens_total", chr(107)+"ind=\"cached\"")}[1h]))) * {PRICE_IN} / 1e6 + sum(increase({m("permitflow_openai_tokens_total", chr(107)+"ind=\"cached\"")}[1h])) * {PRICE_CACHED} / 1e6 + sum(increase({m("permitflow_openai_tokens_total", chr(107)+"ind=\"completion\"")}[1h])) * {PRICE_OUT} / 1e6', "USD/hour")], 12, 55, w=12, h=7, unit="currencyUSD",
          desc="List prices for gpt-4.1-mini: USD 0.40 per million input tokens, 0.10 cached, 1.60 output. An estimate from the usage the API reports on every call; the OpenAI invoice is the truth."),

    row(102, "Is the queue moving?", 62),
    panel(31, "Applications by status (now)", [(f'{m("permitflow_applications")}', "{{status}}")], 0, 63, w=12, h=9, kind="bargauge",
          extra={"options": {"reduceOptions": {"calcs": ["lastNotNull"]}, "orientation": "horizontal", "displayMode": "gradient"}}),
    panel(32, "Transitions per hour, by target status", [(f'sum by (target) (increase({m("permitflow_transitions_total")}[1h]))', "{{target}}")], 12, 63, w=12, h=9, unit="short", stack=True),
    panel(33, "Waiting on the officer", [(f'sum({m("permitflow_applications", "status=~\"application_received|pre_site_resubmitted|post_site_clarification_resubmitted|pending_approval\"")})', "officer's turn")], 0, 72, w=12, h=6, unit="short"),
    panel(34, "Waiting on the operator", [(f'sum({m("permitflow_applications", "status=~\"pending_pre_site_resubmission|pending_post_site_resubmission\"")})', "operator's turn")], 12, 72, w=12, h=6, unit="short"),
]

dashboard = {
    "uid": "permitflow", "title": "PermitFlow", "tags": ["permitflow"], "timezone": "Asia/Singapore", "schemaVersion": 39, "version": 2,
    "editable": False, "refresh": "30s", "time": {"from": "now-6h", "to": "now"}, "panels": panels,
    "templating": {"list": [{
        "name": "environment", "label": "Environment", "type": "query", "datasource": DS,
        "query": {"query": 'label_values(up{job="permitflow-api"}, environment)', "refId": "env"},
        "definition": 'label_values(up{job="permitflow-api"}, environment)',
        "refresh": 2, "includeAll": False, "multi": False, "sort": 1, "current": {"text": "development", "value": "development"},
    }]},
    "annotations": {"list": []},
}
out = Path(__file__).with_name("dashboards") / "permitflow.json"
out.write_text(json.dumps(dashboard, indent=1) + "\n")
print(out, len(panels), "panels")
