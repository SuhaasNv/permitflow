#!/usr/bin/env python3
"""Generates the Grafana alerting provisioning files (US-077, Telegram): the six incident rules (one alert
per environment, from the `environment` label) and an hourly digest per environment, one Telegram contact
point, the notification policy, the message template. Run after editing; the YAML files under alerting/
are what Grafana provisions. The start script copies them only when TELEGRAM_BOT_TOKEN and
TELEGRAM_CHAT_ID are set; the placeholders in contact-points.yaml are filled by that script with sed,
inside quotes, because Grafana's own ${VAR} expansion hands an all-digit chat id over as a number."""

import json
from pathlib import Path

OUT = Path(__file__).with_name("alerting")
DS = "prometheus"
ENVIRONMENTS = ("development", "production", "local")
DASHBOARD = "https://grafana.dev.permitflow.space/d/permitflow/permitflow"
ALERTS = "https://grafana.dev.permitflow.space/alerting/list"
PRICE_IN, PRICE_CACHED, PRICE_OUT = 0.40, 0.10, 1.60  # USD per million tokens, gpt-4.1-mini list price


def query(ref, expr, seconds=600):
    return {"refId": ref, "relativeTimeRange": {"from": seconds, "to": 0}, "datasourceUid": DS,
            "model": {"refId": ref, "expr": expr, "instant": True, "intervalMs": 15000, "maxDataPoints": 43200}}


def reduce(ref, src):
    return {"refId": ref, "datasourceUid": "__expr__",
            "model": {"refId": ref, "type": "reduce", "expression": src, "reducer": "last", "settings": {"mode": "dropNN"}}}


def threshold(ref, src, op, value):
    return {"refId": ref, "datasourceUid": "__expr__",
            "model": {"refId": ref, "type": "threshold", "expression": src,
                      "conditions": [{"evaluator": {"type": op, "params": [value]}, "operator": {"type": "and"},
                                      "query": {"params": [src]}, "reducer": {"type": "last", "params": []}, "type": "query"}]}}


def incident(uid, title, expr, op, value, for_, severity, summary, nodata="OK"):
    """One rule; the query keeps the environment label, so each environment fires its own alert."""
    return {"uid": uid, "title": title, "condition": "C",
            "data": [query("A", expr), reduce("B", "A"), threshold("C", "B", op, value)],
            "for": for_, "labels": {"severity": severity, "kind": "incident"},
            "annotations": {"summary": summary, "value": "{{ printf \"%.3g\" $values.B.Value }}"},
            "noDataState": nodata, "execErrState": "Error", "isPaused": False}


incidents = [
    incident("pf-api-down", "PermitFlow API down", 'min by (environment) (up{job="permitflow-api"})', "lt", 1, "2m", "critical",
             "The API's metrics endpoint has not answered for two minutes.", nodata="Alerting"),
    incident("pf-api-5xx", "PermitFlow API error burst",
             '(sum by (environment) (rate(permitflow_http_requests_total{status=~"5.."}[5m])) or sum by (environment) (rate(permitflow_http_requests_total[5m])) * 0) / sum by (environment) (rate(permitflow_http_requests_total[5m]))',
             "gt", 0.01, "5m", "critical", "More than 1 % of API answers are 5xx over five minutes."),
    incident("pf-api-slow", "PermitFlow API slow",
             'histogram_quantile(0.995, sum by (environment, le) (rate(permitflow_http_request_seconds_bucket[10m])))',
             "gt", 0.5, "10m", "warning", "The 99.5th percentile of API latency is above 500 ms."),
    incident("pf-checks-failing", "PermitFlow document checks failing",
             '(sum by (environment) (rate(permitflow_verification_runs_total{outcome=~"failed|unavailable"}[30m])) or sum by (environment) (rate(permitflow_verification_runs_total[30m])) * 0) / sum by (environment) (rate(permitflow_verification_runs_total[30m]))',
             "gt", 0.2, "15m", "warning", "More than 20 % of document checks fail or are unavailable."),
    incident("pf-checks-slow", "PermitFlow document checks slow",
             'histogram_quantile(0.95, sum by (environment, le) (rate(permitflow_verification_run_seconds_bucket[30m])))',
             "gt", 180, "15m", "warning", "The 95th percentile of document check time is above three minutes."),
    incident("pf-rate-limiting", "PermitFlow rate limiting",
             'sum by (environment) (rate(permitflow_rate_limited_total[5m]))', "gt", 1, "10m", "info",
             "The per-client limiter is refusing more than one request a second."),
]


def digest(env):
    """Always firing; the policy repeats it every hour; the numbers ride in the annotations."""
    e = f'environment="{env}"'
    cost = (f'((sum(increase(permitflow_openai_tokens_total{{{e}, kind="prompt"}}[1h])) - sum(increase(permitflow_openai_tokens_total{{{e}, kind="cached"}}[1h]))) * {PRICE_IN}'
            f' + sum(increase(permitflow_openai_tokens_total{{{e}, kind="cached"}}[1h])) * {PRICE_CACHED}'
            f' + sum(increase(permitflow_openai_tokens_total{{{e}, kind="completion"}}[1h])) * {PRICE_OUT}) / 1e6 or vector(0)')
    qs = [
        ("A", f'min(up{{job="permitflow-api", {e}}}) or vector(0)'),
        ("D", f'sum(rate(permitflow_http_requests_total{{{e}}}[1h])) * 60 or vector(0)'),
        ("E", f'histogram_quantile(0.995, sum by (le) (rate(permitflow_http_request_seconds_bucket{{{e}}}[1h]))) * 1000 or vector(0)'),
        ("F", f'sum(increase(permitflow_verification_runs_total{{{e}}}[1h])) or vector(0)'),
        ("G", cost),
        ("H", f'sum(permitflow_applications{{{e}}}) or vector(0)'),
        ("I", f'sum(permitflow_applications{{{e}, status=~"application_received|pre_site_resubmitted|post_site_clarification_resubmitted|pending_approval"}}) or vector(0)'),
        ("J", f'sum(permitflow_applications{{{e}, status=~"pending_pre_site_resubmission|pending_post_site_resubmission"}}) or vector(0)'),
    ]
    data = [query(r, x, 3600) for r, x in qs] + [reduce(r + "r", r) for r, _ in qs]
    # the environment exists when Prometheus has a target for it; otherwise the rule stays quiet (NoData -> OK)
    data += [query("Z", f'count(up{{job="permitflow-api", {e}}})'), reduce("Zr", "Z"), threshold("C", "Zr", "gt", 0)]
    v = lambda r, fmt: f"{{{{ printf \"{fmt}\" (index $values \"{r}r\").Value }}}}"
    return {"uid": f"pf-digest-{env}", "title": f"PermitFlow hourly digest ({env})", "condition": "C", "data": data,
            "for": "0s", "labels": {"severity": "info", "kind": "digest", "environment": env},
            "annotations": {
                "summary": f"PermitFlow, the last hour, {env}",
                "api": "{{ if ge (index $values \"Ar\").Value 1.0 }}up{{ else }}DOWN{{ end }}",
                "requests_per_minute": v("D", "%.0f"), "p995_ms": v("E", "%.0f"), "checks": v("F", "%.0f"),
                "spend_usd": v("G", "%.3f"), "applications": v("H", "%.0f"),
                "waiting_officer": v("I", "%.0f"), "waiting_operator": v("J", "%.0f"),
            },
            "noDataState": "OK", "execErrState": "OK", "isPaused": False}


rules_doc = {"apiVersion": 1, "deleteRules": [{"orgId": 1, "uid": "pf-digest"}], "groups": [{"orgId": 1, "name": "permitflow", "folder": "PermitFlow", "interval": "1m",
                                          "rules": incidents + [digest(e) for e in ENVIRONMENTS]}]}

SECTION = '''{{- range .Alerts }}{{ if and (eq .Labels.kind "digest") (eq .Labels.environment "ENV") }}
<b>ENVTITLE</b>  ·  API {{ .Annotations.api }}
Requests  <b>{{ .Annotations.requests_per_minute }}</b> / min   ·   p99.5  <b>{{ .Annotations.p995_ms }}</b> ms
Checks  <b>{{ .Annotations.checks }}</b>   ·   spend  <b>USD {{ .Annotations.spend_usd }}</b>
Applications  <b>{{ .Annotations.applications }}</b>   ·   officer's turn  <b>{{ .Annotations.waiting_officer }}</b>   ·   operator's turn  <b>{{ .Annotations.waiting_operator }}</b>
━━━━━━━━━━━━━━━━━━━━━━
{{- end }}{{ end }}'''

TEMPLATE = ('{{ define "permitflow.telegram" -}}\n'
            '{{- $digest := false }}{{ range .Alerts }}{{ if eq .Labels.kind "digest" }}{{ $digest = true }}{{ end }}{{ end }}\n'
            '{{- if $digest }}\n<b>PermitFlow · hourly digest</b>\n━━━━━━━━━━━━━━━━━━━━━━'
            + "".join(SECTION.replace("ENVTITLE", e.capitalize()).replace("ENV", e) for e in ENVIRONMENTS)
            + f'\nDashboard  {DASHBOARD}\n'
            '{{- end }}\n'
            '{{- range .Alerts }}{{ if eq .Labels.kind "incident" }}\n'
            '<b>{{ if eq .Status "firing" }}FIRING{{ else }}RESOLVED{{ end }}  ·  {{ .Labels.alertname }}</b>\n'
            'Environment  <b>{{ .Labels.environment }}</b>   ·   severity  <b>{{ .Labels.severity }}</b>\n'
            '{{ .Annotations.summary }}{{ if .Annotations.value }}\nValue now  <code>{{ .Annotations.value }}</code>{{ end }}\n'
            f'Alerting  {ALERTS}\n'
            '{{- end }}{{ end }}\n'
            '{{- end }}')

contact_points = {"apiVersion": 1, "contactPoints": [{"orgId": 1, "name": "telegram", "receivers": [{
    "uid": "pf-telegram", "type": "telegram", "disableResolveMessage": False,
    "settings": {"bottoken": "__TELEGRAM_BOT_TOKEN__", "chatid": "__TELEGRAM_CHAT_ID__",
                 "message": '{{ template "permitflow.telegram" . }}', "parse_mode": "HTML", "disable_web_page_preview": True}}]}]}

policies = {"apiVersion": 1, "policies": [{"orgId": 1, "receiver": "telegram", "group_by": ["alertname", "environment"],
            "group_wait": "30s", "group_interval": "5m", "repeat_interval": "4h",
            "routes": [{"receiver": "telegram", "object_matchers": [["kind", "=", "digest"]],
                        "group_by": ["kind"], "group_wait": "10s", "group_interval": "1h", "repeat_interval": "1h"}]}]}

templates = {"apiVersion": 1, "templates": [{"orgId": 1, "name": "permitflow.telegram", "template": TEMPLATE}]}


def dump(name, doc):
    try:
        import yaml  # type: ignore[import-untyped]
        (OUT / name).write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, width=1000))
    except ImportError:  # JSON is valid YAML
        (OUT / name).write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")


OUT.mkdir(exist_ok=True)
dump("rules.yaml", rules_doc)
dump("contact-points.yaml", contact_points)
cp = OUT / "contact-points.yaml"
cp.write_text(cp.read_text().replace("chatid: __TELEGRAM_CHAT_ID__", 'chatid: "__TELEGRAM_CHAT_ID__"').replace("bottoken: __TELEGRAM_BOT_TOKEN__", 'bottoken: "__TELEGRAM_BOT_TOKEN__"'))
dump("policies.yaml", policies)
dump("templates.yaml", templates)
print(OUT, "rules:", len(incidents) + len(ENVIRONMENTS))
