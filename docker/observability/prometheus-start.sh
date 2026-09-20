#!/bin/sh
# Render prometheus.yml from the template with the environment (target, scheme, token, label), then start.
# Used by Docker Compose (mounted) and, as a one-line start command, by the Railway service (OPERATIONS.md).
set -eu
sed -e "s|__TARGET__|${METRICS_TARGET:-host.docker.internal:8000}|" \
    -e "s|__SCHEME__|${METRICS_SCHEME:-http}|" \
    -e "s|__TOKEN__|${METRICS_TOKEN:?METRICS_TOKEN is required}|" \
    -e "s|__ENVIRONMENT__|${ENVIRONMENT_LABEL:-local}|" \
    /etc/prometheus/prometheus.tpl.yml > /prometheus/prometheus.yml
cp /etc/prometheus/alerts.yml /prometheus/alerts.yml
exec prometheus --config.file=/prometheus/prometheus.yml --storage.tsdb.path=/prometheus \
    --storage.tsdb.retention.time=30d --web.enable-lifecycle
