import test from 'node:test'
import assert from 'node:assert/strict'
import { effectScope, nextTick, ref } from 'vue'
import { useChatDrafts } from './useChatDrafts.js'
import { useChatDelivery } from './useChatDelivery.js'
import { clearChatDrafts, draftKey, readDraft, writeDraft } from '../utils/chatDrafts.js'

function deferred() {
  let resolve, reject
  const promise = new Promise((yes, no) => { resolve = yes; reject = no })
  return { promise, resolve, reject }
}
function setup(t, api = {}) {
  const previous = globalThis.localStorage, values = new Map(), scope = effectScope()
  globalThis.localStorage = { get length() { return values.size }, key: index => [...values.keys()][index],
    getItem: key => values.get(key), setItem: (key, value) => values.set(key, value), removeItem: key => values.delete(key) }
  const userId = ref(1), companyId = ref(2), rooms = ref([{ id: 11 }, { id: 12 }]), selected = ref({ id: 11 })
  const error = ref(''), failures = [], accepted = []
  let epoch = 0, drafts, delivery
  api.get ||= async () => ({ data: { results: [] } })
  scope.run(() => {
    drafts = useChatDrafts({ api, userId, companyId, rooms, selected, hasSession: () => true,
      isCurrent: token => token === epoch, reportError: value => { error.value = value } })
    delivery = useChatDelivery({ api, drafts, selected, companyId, loadingMessages: ref(false), error,
      getEpoch: () => epoch, onFailure: async err => { failures.push(err) },
      onAccepted: async (...args) => { accepted.push(args) } })
  })
  t.after(() => {
    scope.stop()
    if (previous === undefined) delete globalThis.localStorage
    else globalThis.localStorage = previous
  })
  async function open(roomId) {
    drafts.save(); drafts.resetContext(); epoch++; selected.value = { id: roomId }
    drafts.activeDraftKey.value = draftKey(userId.value, companyId.value, roomId)
    await drafts.restore(epoch)
  }
  return { drafts, delivery, open, error, failures, accepted, selected, companyId, userId }
}

test('drafts and previews stay separate per room; file objects never enter persistent storage', async t => {
  const { drafts: d, open } = setup(t)
  await open(11)
  const file = new File(['document'], 'order.txt')
  d.draft.value = 'First draft'; d.files.value = [file]
  d.pendingReference.value = { type: 'product', id: 7, title: 'Fabric' }
  d.save()
  const stored = readDraft(draftKey(1, 2, 11))
  assert.equal(stored.fileCount, 1); assert.equal(stored.files, undefined)
  await open(12)
  d.draft.value = 'Second draft'; d.save()
  assert.equal(d.draftPreviews.value[11], 'First draft')
  assert.equal(d.draftPreviews.value[12], 'Second draft')
  await open(11)
  assert.equal(d.files.value[0], file)
  assert.equal(d.pendingReference.value.id, 7)
  d.clearMemory()
  await d.restore(3)
  assert.equal(d.draft.value, 'First draft')
  assert.equal(d.missingDraftFiles.value, true)
  assert.deepEqual(d.files.value, [])
})

test('saving before history/draft restoration cannot erase a persisted draft', t => {
  const { drafts: d } = setup(t), key = draftKey(1, 2, 11)
  writeDraft(key, { text: 'Keep after failed history request' })
  d.activeDraftKey.value = key
  d.save()
  assert.equal(readDraft(key).text, 'Keep after failed history request')
})

test('a late reply lookup cannot change another room after switching conversations', async t => {
  const lookup = deferred()
  const { drafts: d, open } = setup(t, { get: () => lookup.promise })
  writeDraft(draftKey(1, 2, 11), { text: 'Reply draft', replyId: 5 })
  const first = open(11)
  await open(12)
  d.draft.value = 'Other room'; d.save()
  lookup.resolve({ data: { id: 5, text: 'Original', sender_id: 9 } })
  await first
  assert.equal(d.draft.value, 'Other room')
  assert.equal(d.replyTarget.value, null)
  assert.equal(readDraft(draftKey(1, 2, 12)).text, 'Other room')
})

test('failed upload retries with the same UUID, files, company, reference and reply', async t => {
  const requests = []
  const fixture = setup(t, { post: async (url, body, config) => {
    requests.push({ url, body, config })
    config.onUploadProgress({ loaded: 5, total: 10 })
    if (requests.length === 1) throw new Error('Network lost')
    return { data: { id: 99 } }
  } })
  const { drafts: d, delivery, open } = fixture
  await open(11)
  d.draft.value = 'Send this'; d.files.value = [new File(['data'], 'report.txt')]
  d.pendingReference.value = { type: 'product', id: 7 }; d.replyTarget.value = { id: 8 }
  await delivery.send()
  assert.equal(delivery.activeDelivery.value.status, 'failed')
  assert.equal(d.draft.value, 'Send this')
  await delivery.retry()
  assert.equal(requests[0].body.get('client_id'), requests[1].body.get('client_id'))
  assert.equal(requests[1].body.get('files').name, 'report.txt')
  assert.equal(requests[1].body.get('reference_id'), '7')
  assert.equal(requests[1].body.get('reply_to_id'), '8')
  assert.equal(requests[1].config.params.company_id, 2)
  assert.equal(delivery.activeDelivery.value.status, 'sent')
  assert.equal(delivery.activeDelivery.value.progress, 100)
  assert.equal(d.draft.value, '')
  assert.equal(readDraft(draftKey(1, 2, 11)), null)
  assert.equal(fixture.accepted.length, 1)
})

test('a send acknowledgement clears its own draft without touching the newly selected room', async t => {
  const request = deferred()
  const { drafts: d, delivery, open, accepted } = setup(t, { post: () => request.promise })
  await open(11); d.draft.value = 'In flight'
  const sending = delivery.send()
  assert.equal(delivery.sending.value, true)
  await open(12); d.draft.value = 'Keep this draft'; d.save()
  assert.equal(delivery.sending.value, false)
  request.resolve({ data: { id: 99 } }); await sending
  assert.equal(d.draft.value, 'Keep this draft')
  assert.equal(readDraft(draftKey(1, 2, 11)), null)
  assert.equal(accepted.length, 0)
})

test('logout invalidates in-flight delivery even when the same account opens the same room again', async t => {
  const request = deferred()
  const { drafts: d, delivery, open, accepted } = setup(t, { post: () => request.promise })
  await open(11); d.draft.value = 'Old session'
  const sending = delivery.send()
  delivery.clear(); d.clearMemory(); clearChatDrafts(); d.activeDraftKey.value = ''
  await open(11); d.draft.value = 'New session'; d.save()
  request.resolve({ data: { id: 99 } }); await sending
  assert.equal(d.draft.value, 'New session')
  assert.equal(readDraft(draftKey(1, 2, 11)).text, 'New session')
  assert.equal(accepted.length, 0)
})

test('canceling edit, including after reload, restores the draft and its retry identity', async t => {
  const { drafts: d, open } = setup(t, { get: async () => ({ data: { id: 5, sender_id: 1, text: 'Original' } }) })
  await open(11)
  d.draft.value = 'Uncertain send'
  d.pendingSend.value = { client_id: 'same-retry-id', signature: 'same-signature', text: 'Uncertain send' }
  d.beginEdit({ id: 5, sender_id: 1, text: 'Original' })
  d.draft.value = 'Changed'; d.save()
  await nextTick()
  d.clearMemory()
  await d.restore(1)
  assert.equal(d.editTarget.value.id, 5)
  d.cancelContext()
  assert.equal(d.draft.value, 'Uncertain send')
  assert.equal(d.pendingSend.value.client_id, 'same-retry-id')
})
