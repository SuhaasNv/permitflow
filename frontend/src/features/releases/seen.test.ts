import { hasSeenRelease, markReleaseSeen } from './seen'

describe('the New mark', () => {
  beforeEach(() => localStorage.clear())

  it('shows until the page has been opened for this version, and again for the next', () => {
    expect(hasSeenRelease('0.4.0-rc.2')).toBe(false)
    markReleaseSeen('0.4.0-rc.2')
    expect(hasSeenRelease('0.4.0-rc.2')).toBe(true)
    expect(hasSeenRelease('0.5.0')).toBe(false)
  })

  it('survives storage that refuses', () => {
    const getItem = vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('blocked')
    })
    const setItem = vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('blocked')
    })
    expect(hasSeenRelease('0.4.0-rc.2')).toBe(false)
    expect(() => markReleaseSeen('0.4.0-rc.2')).not.toThrow()
    getItem.mockRestore()
    setItem.mockRestore()
  })
})
