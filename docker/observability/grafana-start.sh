#!/bin/sh
# Grafana start for PermitFlow (US-077). Writes the provisioning files under the writable provisioning
# path, from mounted files (Compose) or from variables (Railway, where nothing can be mounted), then
# starts Grafana. The Telegram alerting files are written only when TELEGRAM_BOT_TOKEN is set, so a
# Grafana without a bot provisions no contact point and Grafana's own alerting stays empty.
set -eu
P="${GF_PATHS_PROVISIONING:-/var/lib/grafana/pf/provisioning}"
SRC="${GF_PROVISION_SRC:-/etc/grafana/provisioning-src}"   # Compose mounts the repository folder here
mkdir -p "$P/datasources" "$P/dashboards" "$P/alerting" /var/lib/grafana/pf/dashboards
if [ -d "$SRC" ]; then
  cp "$SRC/provisioning/datasources/"*.yml "$P/datasources/"
  cp "$SRC/provisioning/dashboards/"*.yml "$P/dashboards/"
  cp "$SRC/dashboards/"*.json /var/lib/grafana/pf/dashboards/
  ALERTING="$SRC/alerting"
else
  printf "%s" "${GF_PROVISION_DATASOURCE:?}" > "$P/datasources/prometheus.yml"
  printf "%s" "${GF_PROVISION_DASHBOARDS:?}" > "$P/dashboards/permitflow.yml"
  printf "%s" "${GF_DASHBOARD_PERMITFLOW:?}" > /var/lib/grafana/pf/dashboards/permitflow.json
  ALERTING=""
fi
rm -f "$P/alerting/"*.yaml
if [ -n "${TELEGRAM_BOT_TOKEN:-}" ] && [ -n "${TELEGRAM_CHAT_ID:-}" ]; then
  if [ -n "$ALERTING" ]; then
    cp "$ALERTING/"*.yaml "$P/alerting/"
  else
    printf "%s" "${GF_ALERTING_RULES:?}" > "$P/alerting/rules.yaml"
    printf "%s" "${GF_ALERTING_CONTACT_POINTS:?}" > "$P/alerting/contact-points.yaml"
    printf "%s" "${GF_ALERTING_POLICIES:?}" > "$P/alerting/policies.yaml"
    printf "%s" "${GF_ALERTING_TEMPLATES:?}" > "$P/alerting/templates.yaml"
  fi
  # the bot token and the chat id go in with sed, inside quotes, so a numeric chat id stays a string
  sed -i -e "s|__TELEGRAM_BOT_TOKEN__|$TELEGRAM_BOT_TOKEN|" -e "s|__TELEGRAM_CHAT_ID__|$TELEGRAM_CHAT_ID|" "$P/alerting/contact-points.yaml"
fi
exec /run.sh
