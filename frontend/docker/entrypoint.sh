#!/bin/sh
# Writes the runtime configuration the app reads before it boots, then renders the nginx template.
set -eu
: "${PORT:=8080}"
: "${API_URL:?API_URL must be set (for example https://api.example.com/api/v1)}"
export PORT
escaped=$(printf '%s' "$API_URL" | sed 's/[\\"]/\\&/g')
printf 'window.__PERMITFLOW__ = { apiUrl: "%s" };\n' "$escaped" > /usr/share/nginx/html/config.js
envsubst '${PORT}' < /etc/nginx/templates/default.conf.template > /etc/nginx/conf.d/default.conf
exec nginx -g 'daemon off;'
