/** Injected by Vite from package.json (see vite.config.ts). */
declare const __APP_VERSION__: string

/** The repository's RELEASE_NOTES.md as one string, read at build time (see vite.config.ts, US-094). */
declare module 'virtual:release-notes' {
  const raw: string
  export default raw
}
