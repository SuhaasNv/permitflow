import { guardUnload, hasUnsaved, setUnsaved } from './unsaved'

describe('unsaved changes flag', () => {
  afterEach(() => setUnsaved(false))

  it('holds the flag the pages set', () => {
    expect(hasUnsaved()).toBe(false)
    setUnsaved(true)
    setUnsaved(true)
    expect(hasUnsaved()).toBe(true)
    setUnsaved(false)
    expect(hasUnsaved()).toBe(false)
  })

  it('asks the browser to confirm unload only while dirty', () => {
    const stop = guardUnload()
    const fire = () => {
      const e = new Event('beforeunload', { cancelable: true }) as BeforeUnloadEvent
      window.dispatchEvent(e)
      return e.defaultPrevented
    }
    expect(fire()).toBe(false)
    setUnsaved(true)
    expect(fire()).toBe(true)
    stop()
    expect(fire()).toBe(false)
  })
})
