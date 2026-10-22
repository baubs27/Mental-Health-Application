import test from 'node:test'
import assert from 'node:assert/strict'
import { VoiceSessionController } from '../src/voice/VoiceSessionController.js'

function response(body, ok = true) {
  return { ok, status: ok ? 200 : 502, json: async () => body }
}

function makeHarness({ fetchOverride, mediaOverride, audioOverride } = {}) {
  const order = []
  const sent = []
  const track = {
    enabled: true,
    stopped: false,
    stop() { this.stopped = true; order.push('track.stop') },
  }
  const stream = { getTracks: () => [track], getAudioTracks: () => [track] }
  const channel = {
    readyState: 'open',
    onmessage: null,
    send(text) {
      const message = JSON.parse(text)
      sent.push(message)
      if (message.type === 'session.close') {
        queueMicrotask(() => channel.onmessage?.({ data: JSON.stringify({ type: 'session.closed', reason: 'close_requested' }) }))
      }
    },
    close() { this.readyState = 'closed'; order.push('channel.close') },
  }
  const pc = {
    iceGatheringState: 'complete',
    signalingState: 'stable',
    localDescription: null,
    createDataChannel() { order.push('data-channel'); return channel },
    addTrack() { order.push('add-track') },
    async createOffer() { order.push('create-offer'); return { type: 'offer', sdp: 'offer-sdp' } },
    async setLocalDescription(offer) { order.push('set-local'); this.localDescription = offer },
    async setRemoteDescription(answer) {
      order.push('set-remote')
      assert.equal(answer.sdp, 'answer-sdp')
      queueMicrotask(() => channel.onmessage?.({ data: JSON.stringify({ type: 'session.started' }) }))
    },
    addEventListener() {},
    removeEventListener() {},
    close() { this.signalingState = 'closed'; order.push('peer.close') },
  }
  let fetchFn = async (url, options) => {
    order.push(url)
    if (url.endsWith('/voice/config')) return response({ configured: true, max_session_seconds: 300 })
    if (url.endsWith('/voice/sessions')) {
      assert.equal(options.method, 'POST')
      assert.deepEqual(JSON.parse(options.body), { sdp_offer: 'offer-sdp' })
      return response({ session_id: 'live_test', sdp_answer: 'answer-sdp', max_session_seconds: 300 })
    }
    return response({}, true)
  }
  if (fetchOverride) fetchFn = fetchOverride({ order, sent })
  const audioElement = audioOverride ?? { srcObject: null, pause() { order.push('audio.pause') }, async play() {} }
  const states = []
  const controller = new VoiceSessionController({
    fetchFn,
    getUserMedia: mediaOverride ?? (async constraints => {
      order.push('get-user-media')
      assert.deepEqual(constraints, { audio: true, video: false })
      return stream
    }),
    createPeerConnection: () => { order.push('peer-connection'); return pc },
    audioElement,
    onState: (value) => states.push(value),
  })
  return { controller, order, sent, track, stream, channel, pc, audioElement, states }
}

test('starts after explicit permission, creates the channel before the offer, waits for session.started, and mutes only the mic', async () => {
  const h = makeHarness()
  await h.controller.start()
  assert.equal(h.controller.state, 'active')
  assert.ok(h.order.indexOf('data-channel') < h.order.indexOf('create-offer'))
  assert.ok(h.order.indexOf('set-local') < h.order.findIndex(item => item.endsWith('/voice/sessions')))
  h.controller.mute()
  assert.equal(h.track.enabled, false)
  assert.equal(h.controller.state, 'muted')
  assert.equal(h.audioElement.srcObject, null)
  h.controller.mute()
  assert.equal(h.track.enabled, true)
  assert.equal(h.controller.state, 'active')
  await h.controller.end()
  assert.equal(h.sent.filter(item => item.type === 'session.close').length, 1)
  assert.equal(h.track.stopped, true)
  assert.equal(h.audioElement.srcObject, null)
  assert.equal(h.controller.state, 'closed')
})

test('does not request microphone permission when voice is unconfigured', async () => {
  const h = makeHarness({ fetchOverride: () => async () => response({ configured: false }, true) })
  await h.controller.start()
  assert.equal(h.controller.state, 'error')
  assert.equal(h.order.includes('get-user-media'), false)
  assert.match(h.controller.error, /not configured/)
})

test('microphone denial becomes an error and stops any tracks that were granted', async () => {
  const h = makeHarness({ mediaOverride: async () => { throw new Error('Microphone permission was denied.') } })
  await h.controller.start()
  assert.equal(h.controller.state, 'error')
  assert.match(h.controller.error, /permission was denied/)
})

test('duplicate Start during a permission request does not create a second stream', async () => {
  let grant
  let calls = 0
  const h = makeHarness({
    mediaOverride: () => { calls += 1; return new Promise(resolve => { grant = resolve }) },
  })
  const first = h.controller.start()
  await new Promise(resolve => setImmediate(resolve))
  await h.controller.start()
  assert.equal(calls, 1)
  grant(h.stream)
  await first
  assert.equal(h.controller.state, 'active')
  await h.controller.end()
})

test('End during a pending session request stops the mic and hangs up a late session without reviving state', async () => {
  let releaseSession
  const h = makeHarness({
    fetchOverride: ({ order }) => async (url, options) => {
      order.push(url)
      if (url.endsWith('/voice/config')) return response({ configured: true, max_session_seconds: 300 })
      if (url.endsWith('/voice/sessions')) return new Promise(resolve => { releaseSession = resolve })
      return response({}, true)
    },
  })
  const starting = h.controller.start()
  while (!releaseSession) await new Promise(resolve => setImmediate(resolve))
  await h.controller.end()
  assert.equal(h.track.stopped, true)
  releaseSession(response({ session_id: 'live_late', sdp_answer: 'answer-sdp', max_session_seconds: 300 }))
  await starting
  assert.equal(h.controller.state, 'closed')
  assert.ok(h.order.some(item => item.endsWith('/voice/sessions/live_late/hangup')))
  assert.equal(h.order.includes('set-remote'), false)
})

test('provider failure leaves voice in error and does not change text-chat state', async () => {
  const h = makeHarness({
    fetchOverride: ({ order }) => async (url) => {
      order.push(url)
      if (url.endsWith('/voice/config')) return response({ configured: true, max_session_seconds: 300 })
      return response({ detail: 'Voice provider rejected session setup' }, false)
    },
  })
  await h.controller.start()
  assert.equal(h.controller.state, 'error')
  assert.equal(h.track.stopped, true)
  assert.match(h.controller.error, /provider rejected/)
})

test('blocked remote audio exposes a user-gesture retry', async () => {
  let plays = 0
  let blocked
  const audioElement = { srcObject: null, pause() {}, play: async () => { plays += 1; if (plays === 1) throw new Error('autoplay blocked') } }
  const h = makeHarness({ audioOverride: audioElement })
  h.controller.onPlaybackBlocked = value => { blocked = value }
  await h.controller.start()
  h.pc.ontrack({ streams: [{ id: 'assistant-audio' }] })
  await new Promise(resolve => setImmediate(resolve))
  assert.equal(blocked, true)
  await h.controller.enableAssistantAudio()
  assert.equal(plays, 2)
  assert.equal(blocked, false)
  await h.controller.end()
})

test('repeated End shares one close operation and releases resources once', async () => {
  const h = makeHarness()
  await h.controller.start()
  await Promise.all([h.controller.end(), h.controller.end(), h.controller.end()])
  assert.equal(h.sent.filter(item => item.type === 'session.close').length, 1)
  assert.equal(h.order.filter(item => item === 'peer.close').length, 1)
  assert.equal(h.track.stopped, true)
  assert.equal(h.controller.state, 'closed')
})

test('configured duration automatically ends the provider session and releases the microphone', async () => {
  const h = makeHarness({
    fetchOverride: ({ order }) => async (url, options) => {
      order.push(url)
      if (url.endsWith('/voice/config')) return response({ configured: true, max_session_seconds: 0.02 })
      if (url.endsWith('/voice/sessions')) return response({ session_id: 'live_timer', sdp_answer: 'answer-sdp', max_session_seconds: 0.02 })
      return response({}, true)
    },
  })
  await h.controller.start()
  await new Promise(resolve => setTimeout(resolve, 50))
  assert.equal(h.controller.state, 'closed')
  assert.equal(h.track.stopped, true)
  assert.equal(h.sent.filter(item => item.type === 'session.close').length, 1)
})
