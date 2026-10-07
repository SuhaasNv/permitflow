import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { StorageRoom, storageRoomSentence } from './StorageRoom'

const MB = 1024 * 1024

describe('StorageRoom (US-085)', () => {
  it('says how much room is left before an upload, in whole megabytes from 10 MB up', () => {
    expect(storageRoomSentence({ used_bytes: 3 * MB, budget_bytes: 150 * MB, remaining_bytes: 147 * MB })).toBe(
      "147 MB of the application's 150 MB storage room is left.",
    )
    expect(storageRoomSentence({ used_bytes: 148.5 * MB, budget_bytes: 150 * MB, remaining_bytes: 1.5 * MB })).toBe(
      "1.5 MB of the application's 150 MB storage room is left.",
    )
  })

  it('tells the operator to remove a file once the room is used up', () => {
    render(<StorageRoom storage={{ used_bytes: 150 * MB, budget_bytes: 150 * MB, remaining_bytes: 0 }} />)
    expect(screen.getByTestId('storage-room')).toHaveTextContent(
      'This application has used its 150 MB of storage room. Remove a file you no longer need before adding one.',
    )
  })

  it('renders nothing when the server sent no storage block', () => {
    const { container } = render(<StorageRoom storage={null} />)
    expect(container).toBeEmptyDOMElement()
  })
})
