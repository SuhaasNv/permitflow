/** Written by public/config.js (development) or docker/entrypoint.sh (container) before the app loads. */
interface Window {
  __PERMITFLOW__?: { apiUrl?: string }
}
