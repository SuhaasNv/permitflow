/**
 * The version this build reports (US-111). A promoted image is the tested candidate relabelled at deploy time, so
 * the version comes first from config.js (`appVersion`, written at container start from APP_VERSION) and falls back
 * to the one compiled in from package.json. Read at call time, never cached at module load.
 */
export function appVersion(): string {
  return (typeof window !== 'undefined' && window.__PERMITFLOW__?.appVersion) || __APP_VERSION__
}
