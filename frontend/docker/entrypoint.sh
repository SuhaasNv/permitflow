#!/bin/sh
# Writes the runtime configuration the app reads before it boots, then renders the nginx template.
set -eu
: "${PORT:=8080}"
: "${API_URL:?API_URL must be set (for example https://api.example.com/api/v1)}"
export PORT
escape() { printf '%s' "$1" | sed 's/[\\"]/\\&/g'; }
# US-111: APP_VERSION (optional) relabels a promoted image; without it the app shows the version it was built with.
config="apiUrl: \"$(escape "$API_URL")\""
if [ -n "${APP_VERSION:-}" ]; then config="$config, appVersion: \"$(escape "$APP_VERSION")\""; fi
printf 'window.__PERMITFLOW__ = { %s };\n' "$config" > /usr/share/nginx/html/config.js
# The CSP admits one API origin: the scheme and host of API_URL (US-058).
API_ORIGIN=$(printf '%s' "$API_URL" | sed -E 's#^(https?://[^/]+).*#\1#')
export API_ORIGIN
envsubst '${API_ORIGIN}' < /etc/nginx/templates/security-headers.conf.template > /etc/nginx/snippets/security-headers.conf
envsubst '${PORT}' < /etc/nginx/templates/default.conf.template > /etc/nginx/conf.d/default.conf
exec nginx -g 'daemon off;'
