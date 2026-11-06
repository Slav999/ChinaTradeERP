import test from 'node:test'
import assert from 'node:assert/strict'
import { mergeMessages, readStatusRows, visibleMessageIds } from './chatThread.js'
import { clearChatDrafts, draftKey, readDraft, removeDraft, writeDraft } from './chatDrafts.js'

test('edits and tombstones replace existing rows without losing simultaneous arrivals', () => {
  const rows = mergeMessages([{ id: 2, text: 'Old' }, { id: 4, text: 'Other' }],
    [{ id: 2, text: 'Сообщение удалено', deleted_at: 'now' }, { id: 3, text: 'Concurrent' }, { id: 5, text: 'Own send' }])
  assert.deepEqual(rows.map(row => row.id), [2, 3, 4, 5])
  assert.equal(rows[0].deleted_at, 'now')
  assert.deepEqual(mergeMessages(rows, [{ id: 8, text: 'Later' }], { append: false, hiddenBefore: 2 }).map(row => row.id), [3, 4, 5])
})
test('reading a visible late mention never includes earlier off-screen or half-visible messages', () => {
  const element = (id, top, bottom) => ({ dataset: { messageId: String(id) }, getBoundingClientRect: () => ({ top, bottom }) })
  const ids = visibleMessageIds([element(1, -100, -10), element(50, 10, 60), element(51, 70, 130)], { top: 0, bottom: 100 })
  assert.deepEqual(ids, [50])
})

test('read status counts only current recipients and separates readers from waiting colleagues', () => {
  const rows = readStatusRows({ recipients: [{ id: 2, name: 'Bob' }, { id: 3, name: 'Carol' }],
    results: [{ id: 10, read_by: [{ user_id: 2, read_at: '2026-11-07T10:00:00Z' }, { user_id: 9, read_at: 'old' }] },
      { id: 11, read_by: [] }] })
  assert.equal(rows[10].total, 2); assert.equal(rows[10].count, 1)
  assert.equal(rows[10].readers[0].name, 'Bob')
  assert.equal(rows[10].readers[0].read_at, '2026-11-07T10:00:00Z')
  assert.deepEqual(rows[10].unread.map(person => person.id), [3])
  assert.equal(rows[11].count, 0)
})

test('late responses cannot restore edited or deleted message content', () => {
  const current = [{ id: 10, revision: 8, text: 'Сообщение удалено', deleted_at: 'now' }]
  const rows = mergeMessages(current, [{ id: 10, revision: 7, text: 'Private old content' }])
  assert.equal(rows[0].deleted_at, 'now')
  assert.equal(rows[0].revision, 8)
})

test('incremental edits outside the loaded window cannot create a gap in history', () => {
  const current = [{ id: 100, revision: 100 }, { id: 101, revision: 101 }]
  const rows = mergeMessages(current, [{ id: 20, revision: 102 }, { id: 102, revision: 103 }], { includeOlder: false })
  assert.deepEqual(rows.map(row => row.id), [100, 101, 102])
  // Explicitly loading older history must still be able to prepend rows.
  assert.deepEqual(mergeMessages(rows, [{ id: 99, revision: 99 }]).map(row => row.id), [99, 100, 101, 102])
})
test('drafts are scoped, survive reload, expire and are cleared on logout', t => {
  const previous = globalThis.localStorage, values = new Map()
  globalThis.localStorage = { get length() { return values.size }, key: index => [...values.keys()][index],
    getItem: key => values.get(key), setItem: (key, value) => values.set(key, value), removeItem: key => values.delete(key) }
  try {
    let now = Date.now(); t.mock.method(Date, 'now', () => now)
    const own = draftKey(1, 2, 3), otherCompany = draftKey(1, 4, 3), otherUser = draftKey(5, 2, 3)
    writeDraft(own, { text: 'Unsent', pendingClientId: 'retry-id', fileCount: 1 })
    assert.equal(readDraft(own).text, 'Unsent')
    assert.equal(readDraft(otherCompany), null); assert.equal(readDraft(otherUser), null)
    writeDraft(otherCompany, { text: 'Other company' })
    removeDraft(own); assert.equal(readDraft(own), null)
    now += 8 * 24 * 60 * 60 * 1000
    assert.equal(readDraft(otherCompany), null)
    writeDraft(own, { text: 'Private draft' }); values.set('unrelated-setting', 'keep')
    clearChatDrafts(); assert.equal(readDraft(own), null); assert.equal(values.get('unrelated-setting'), 'keep')
  } finally { if (previous === undefined) delete globalThis.localStorage; else globalThis.localStorage = previous }
})
