# The monitoring services on Railway

Three services in the development environment, all from public images, no image build: their
configuration travels in variables and is written to disk by a start command. Everything here is
repeated from `docs/13-observability/OBSERVABILITY.md` so the repository holds the commands Railway runs.

| Service | Image | Start command | Variables (secrets set by the owner with `railway variables --set-from-stdin`) |
|---------|-------|---------------|-------------------------------------------------------------------------------|
| `prometheus` | `prom/prometheus:v3.5.0` | `sh -c 'printf "%s" "$PROMETHEUS_CONFIG" \| sed -e "s\|__DEV_TOKEN__\|$DEV_METRICS_TOKEN\|" -e "s\|__PROD_TOKEN__\|$PROD_METRICS_TOKEN\|" > /prometheus/prometheus.yml && printf "%s" "$PROMETHEUS_ALERTS" > /prometheus/alerts.yml && exec prometheus --config.file=/prometheus/prometheus.yml --storage.tsdb.path=/prometheus --storage.tsdb.retention.time=30d --web.listen-address=:9090'` | `PROMETHEUS_CONFIG` (`../prometheus.railway.yml`), `PROMETHEUS_ALERTS` (`../alerts.yml`), `DEV_METRICS_TOKEN`, `PROD_METRICS_TOKEN`, `RAILWAY_RUN_UID=0`; volume `/prometheus`; private network only |
| `grafana` | `grafana/grafana-oss:12.1.0` | `sh -c 'printf "%s" "$GF_START_SCRIPT" > /tmp/start.sh && exec sh /tmp/start.sh'` (`GF_START_SCRIPT` is `../grafana-start.sh`) | `GF_PROVISION_DATASOURCE`, `GF_PROVISION_DASHBOARDS`, `GF_DASHBOARD_PERMITFLOW`, `GF_ALERTING_RULES`, `GF_ALERTING_CONTACT_POINTS`, `GF_ALERTING_POLICIES`, `GF_ALERTING_TEMPLATES` (the files under `../grafana/`), `GF_PATHS_PROVISIONING=/var/lib/grafana/pf/provisioning`, `PROMETHEUS_URL=http://prometheus.railway.internal:9090`, `GF_SECURITY_ADMIN_USER`, `GF_SECURITY_ADMIN_PASSWORD`, `GF_SERVER_ROOT_URL=https://grafana.dev.permitflow.space`, `GF_SERVER_HTTP_PORT=3000`, `PORT=3000`, `GF_AUTH_ANONYMOUS_ENABLED=false`, `GF_USERS_ALLOW_SIGN_UP=false`, analytics off, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `RAILWAY_RUN_UID=0`; volume `/var/lib/grafana`; healthcheck `/api/health`; custom domain plus a `_railway-verify` TXT record |
| `telegram-bot` | `python:3.12-alpine` | `sh -c 'printf "%s" "$BOT_SOURCE" > /tmp/bot.py && exec python -u /tmp/bot.py'` (`BOT_SOURCE` is `../telegram-bot/bot.py`) | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `PROMETHEUS_URL=http://prometheus.railway.internal:9090`, `DASHBOARD_URL`, `PYTHONUNBUFFERED=1`; restart policy always; no volume, no domain |

Two things learned the hard way: `RAILWAY_RUN_UID=0` is required because the images run as a non-root user and Railway mounts volumes owned by root (the first Prometheus deploy failed with "permission denied" on `/prometheus`); and a `railway redeploy` re-runs the previous deployment's snapshot, start command included, so a changed start command needs a fresh deployment (setting any variable without `--skip-deploys` makes one).

Refreshing a file-backed variable after an edit, from the repository root:

    railway variables -s grafana -e development --skip-deploys --set-from-stdin GF_DASHBOARD_PERMITFLOW < docker/observability/grafana/dashboards/permitflow.json
    railway variables -s grafana -e development --set-from-stdin GF_ALERTING_RULES < docker/observability/grafana/alerting/rules.yaml   # without --skip-deploys: redeploys with the new file
