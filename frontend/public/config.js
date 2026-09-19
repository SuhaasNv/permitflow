// Runtime configuration. In the container this file is rewritten at start from the API_URL variable
// (docker/entrypoint.sh), so one image serves every environment. In development it stays empty and
// VITE_API_URL (build time) or the localhost default applies.
window.__PERMITFLOW__ = {};
