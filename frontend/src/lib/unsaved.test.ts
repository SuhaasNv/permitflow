import { guardUnload, hasUnsaved, setUnsaved, subscribeUnsaved } from './unsaved'

describe('unsaved changes flag', () => {
  afterEach(() => setUnsaved(false))

  it('notifies subscribers only on change', () => {
    const seen: boolean[] = []
    const stop = subscribeUnsaved((v) => seen.push(v))
    setUnsaved(true)
    setUnsaved(true)
    setUnsaved(false)
    stop()
    setUnsaved(true)
    expect(seen).toEqual([true, false])
    expect(hasUnsaved()).toBe(true)
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
