/// <reference types="vitest/config" />
import { existsSync, readFileSync } from 'node:fs'
import { fileURLToPath, URL } from 'node:url'

import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'
import type { Plugin } from 'vite'

import pkg from './package.json' with { type: 'json' }

/** `virtual:release-notes` is the repository's RELEASE_NOTES.md as a string, so the What's new page (US-094)
 * shows the notes of the commit it was built from and nobody types them twice. Beside the frontend in the
 * checkout; inside it in the image build, where CI copies the file into the build context. */
function releaseNotes(): Plugin {
  const id = 'virtual:release-notes'
  const resolved = `\0${id}`
  return {
    name: 'permitflow-release-notes',
    resolveId(source) {
      return source === id ? resolved : undefined
    },
    load(moduleId) {
      if (moduleId !== resolved) return undefined
      const candidates = ['../RELEASE_NOTES.md', './RELEASE_NOTES.md'].map((p) => fileURLToPath(new URL(p, import.meta.url)))
      const file = candidates.find((p) => existsSync(p))
      if (!file) throw new Error('RELEASE_NOTES.md not found beside the frontend folder or inside it')
      this.addWatchFile(file)
      return `export default ${JSON.stringify(readFileSync(file, 'utf8'))}`
    },
  }
}

export default defineConfig({
  // Release version shown in the app shell and landing footer; bumped with every `v0.<sprint>.0` tag.
  define: { __APP_VERSION__: JSON.stringify(pkg.version) },
  plugins: [react(), tailwindcss(), releaseNotes()],
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
  server: { port: 3000, strictPort: true },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    include: ['src/**/*.test.{ts,tsx}'],
    css: false,
    coverage: {
      provider: 'v8',
      // Every file matched by include counts, tested or not, so the number cannot be flattered by leaving files out.
      include: ['src/**/*.{ts,tsx}'],
      exclude: ['src/**/*.test.{ts,tsx}', 'src/test/**', 'src/main.tsx'],
      reporter: ['text-summary', 'text', 'lcov'],
      // Industry floor (US-053). Statements and lines are the numbers that matter; branches follow.
      thresholds: { statements: 80, lines: 80, functions: 75, branches: 65 },
    },
  },
})
