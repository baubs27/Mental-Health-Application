const API_ROOT = '/api'
const START_TIMEOUT_MS = 20000
const CLOSE_TIMEOUT_MS = 1200
const ICE_TIMEOUT_MS = 7000

const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

export class VoiceSessionController {
  constructor({
    fetchFn = (...args) => fetch(...args),
    getUserMedia = (...args) => navigator.mediaDevices.getUserMedia(...args),
    createPeerConnection = () => new RTCPeerConnection(),
    audioElement,
    onState = () => {},
    onPlaybackBlocked = () => {},
    setTimer = setTimeout,
    clearTimer = clearTimeout,
  }) {
    this.fetchFn = fetchFn
    this.getUserMedia = getUserMedia
    this.createPeerConnection = createPeerConnection
    this.audioElement = audioElement
    this.onState = onState
    this.onPlaybackBlocked = onPlaybackBlocked
    this.setTimer = setTimer
    this.clearTimer = clearTimer
    this.state = 'idle'
    this.error = ''
    this.attempt = 0
    this.endRequested = false
    this.startPromise = null
    this.endPromise = null
    this.stream = null
    this.peerConnection = null
    this.dataChannel = null
    this.sessionId = null
    this.maxTimer = null
    this.closedResolver = null
    this.closedObserved = false
    this.finalizationConfirmed = false
    this.sessionCreated = false
    this.hangupPromise = null
  }

  _setState(state, error = '') {
    this.state = state
    this.error = error
    this.onState({ state, error, sessionCreated: this.sessionCreated, finalizationConfirmed: this.finalizationConfirmed })
  }

  _newSessionWaiters() {
    this.closedObserved = false
    this.closedPromise = new Promise((resolve) => {
      this.closedResolver = resolve
    })
    this.startedPromise = new Promise((resolve, reject) => {
      this.startedResolver = resolve
      this.startedRejecter = reject
      this.startedTimer = this.setTimer(() => reject(new Error('The voice session did not become active.')), START_TIMEOUT_MS)
    })
    // Cancellation can happen before the start promise is awaited.
    this.startedPromise.catch(() => {})
  }

  async _getJson(url, options) {
    const response = await this.fetchFn(url, options)
    let body = {}
    try { body = await response.json() } catch { /* handled as a generic request failure */ }
    if (!response.ok) throw new Error(body.detail || 'The voice request failed.')
    return body
  }

  async start() {
    if (this.startPromise || ['permission', 'connecting', 'active', 'muted', 'closing'].includes(this.state)) return
    this.endRequested = false
    this.endPromise = null
    this.error = ''
    this.sessionId = null
    this.hangupPromise = null
    this.finalizationConfirmed = false
    this.sessionCreated = false
    const attempt = ++this.attempt
    this._setState('permission')
    const task = this._start(attempt)
    this.startPromise = task
    try {
      await task
    } finally {
      if (this.startPromise === task) this.startPromise = null
    }
  }

  async _start(attempt) {
    try {
      const config = await this._getJson(`${API_ROOT}/voice/config`)
      if (!config.configured) throw new Error('Voice is not configured. Text chat is still available.')
      if (this.endRequested || attempt !== this.attempt) return

      this.stream = await this.getUserMedia({ audio: true, video: false })
      if (this.endRequested || attempt !== this.attempt) {
        this._stopMicrophone()
        this._setState('closed')
        return
      }

      this._setState('connecting')
      this._newSessionWaiters()
      this.peerConnection = this.createPeerConnection()
      this.dataChannel = this.peerConnection.createDataChannel('oai-events')
      this.dataChannel.onmessage = (event) => this._handleEvent(event.data)
      this.dataChannel.onerror = () => this._fail('The voice connection reported an error.')
      this.dataChannel.onopen = () => {
        if (this.endRequested && this.sessionId) this._sendClose()
      }
      this.peerConnection.ontrack = (event) => {
        if (!this.audioElement) return
        this.audioElement.srcObject = event.streams?.[0] ?? null
        const playResult = this.audioElement.play()
        if (playResult?.catch) playResult.catch(() => this.onPlaybackBlocked(true))
      }
      for (const track of this.stream.getTracks()) this.peerConnection.addTrack(track, this.stream)

      const offer = await this.peerConnection.createOffer()
      await this.peerConnection.setLocalDescription(offer)
      await this._waitForIceGathering(this.peerConnection)
      if (this.endRequested || attempt !== this.attempt) {
        await this._cleanupLocal()
        this._setState('closed')
        return
      }

      const result = await this._getJson(`${API_ROOT}/voice/sessions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sdp_offer: this.peerConnection.localDescription.sdp }),
      })
      if (typeof result.session_id !== 'string' || typeof result.sdp_answer !== 'string') {
        throw new Error('The voice service returned an invalid session response.')
      }
      this.sessionId = result.session_id
      this.sessionCreated = true
      if (this.endRequested || attempt !== this.attempt) {
        await this._requestProviderHangup(result.session_id)
        await this._cleanupLocal()
        if (attempt === this.attempt) this._setState('closed')
        return
      }

      const durationSeconds = Number(result.max_session_seconds)
      await this.peerConnection.setRemoteDescription({ type: 'answer', sdp: result.sdp_answer })
      await this.startedPromise
      if (this.endRequested || attempt !== this.attempt) {
        if (!this.closedObserved) await this._requestProviderHangup(result.session_id)
        await this._cleanupLocal()
        return
      }
      this.clearTimer(this.startedTimer)
      this._setState('active')
      if (Number.isFinite(durationSeconds) && durationSeconds > 0) {
        this.maxTimer = this.setTimer(() => { void this.end() }, durationSeconds * 1000)
      }
    } catch (error) {
      if (this.endRequested || attempt !== this.attempt) {
        if (this.sessionId && !this.closedObserved) {
          const closeSent = await this._sendClose()
          if (closeSent && this.closedPromise) await Promise.race([this.closedPromise, wait(CLOSE_TIMEOUT_MS)])
          if (!this.closedObserved) await this._requestProviderHangup(this.sessionId)
        }
        await this._cleanupLocal()
        if (attempt === this.attempt) this._setState('closed')
        return
      }
      if (this.sessionId && !this.closedObserved) {
        const closeSent = await this._sendClose()
        if (closeSent && this.closedPromise) await Promise.race([this.closedPromise, wait(CLOSE_TIMEOUT_MS)])
        if (!this.closedObserved) await this._requestProviderHangup(this.sessionId)
      }
      await this._cleanupLocal()
      this._setState('error', error instanceof Error ? error.message : 'Voice could not start.')
    }
  }

  _handleEvent(raw) {
    let event
    try { event = JSON.parse(raw) } catch { return }
    if (event.type === 'session.started') {
      this.clearTimer(this.startedTimer)
      this.startedResolver?.()
    } else if (event.type === 'session.closed') {
      this.closedObserved = true
      this.finalizationConfirmed = true
      this.closedResolver?.(event)
      if (this.state === 'closing') this._setState('closed')
      else if (['active', 'muted'].includes(this.state)) {
        this.endRequested = true
        this._stopMicrophone()
        void this._cleanupLocal().then(() => this._setState('closed'))
      }
    } else if (event.type === 'error') {
      this._fail('The voice session returned an error.')
    }
  }

  _waitForIceGathering(peer) {
    if (peer.iceGatheringState === 'complete') return Promise.resolve()
    return new Promise((resolve, reject) => {
      const timer = this.setTimer(() => finish(new Error('ICE gathering timed out.')), ICE_TIMEOUT_MS)
      const handler = () => {
        if (peer.iceGatheringState === 'complete') finish()
      }
      const finish = (error) => {
        this.clearTimer(timer)
        peer.removeEventListener?.('icegatheringstatechange', handler)
        if (error) reject(error)
        else resolve()
      }
      peer.addEventListener?.('icegatheringstatechange', handler)
      if (!peer.addEventListener) peer.onicegatheringstatechange = handler
    })
  }

  async enableAssistantAudio() {
    try {
      await this.audioElement?.play()
      this.onPlaybackBlocked(false)
    } catch {
      this.onPlaybackBlocked(true)
    }
  }

  mute() {
    if (!['active', 'muted'].includes(this.state)) return
    const shouldMute = this.state === 'active'
    for (const track of this.stream?.getAudioTracks?.() ?? []) track.enabled = !shouldMute
    this._setState(shouldMute ? 'muted' : 'active')
  }

  async _sendClose() {
    if (this.dataChannel?.readyState !== 'open' || !this.sessionId) return false
    try {
      this.dataChannel.send(JSON.stringify({
        type: 'session.close',
        event_id: globalThis.crypto?.randomUUID?.() ?? `close_${Date.now()}`,
      }))
      return true
    } catch {
      return false
    }
  }

  async _requestProviderHangup(sessionId) {
    if (!sessionId) return
    if (!this.hangupPromise) {
      this.hangupPromise = this.fetchFn(`${API_ROOT}/voice/sessions/${encodeURIComponent(sessionId)}/hangup`, {
        method: 'POST',
      }).catch(() => null)
    }
    return this.hangupPromise
  }

  async end() {
    if (this.endPromise) return this.endPromise
    if (['idle', 'closed'].includes(this.state) && !this.startPromise) {
      await this._cleanupLocal()
      this._setState('closed')
      return
    }
    this.endRequested = true
    this._setState('closing')
    this._stopMicrophone()
    this.clearTimer(this.maxTimer)
    this.clearTimer(this.startedTimer)
    const task = (async () => {
      let requested = await this._sendClose()
      if (requested && this.closedPromise) {
        await Promise.race([this.closedPromise, wait(CLOSE_TIMEOUT_MS)])
      }
      if (!this.closedObserved && this.sessionId) await this._requestProviderHangup(this.sessionId)
      await this._cleanupLocal()
      this._setState('closed')
    })()
    this.endPromise = task
    try { await task } finally { if (this.endPromise === task) this.endPromise = null }
  }

  async _fail(message) {
    if (['closing', 'closed'].includes(this.state)) return
    this.endRequested = true
    this._setState('error', message)
    this._stopMicrophone()
    this.clearTimer(this.maxTimer)
    this.maxTimer = null
    if (this.sessionId) {
      const sent = await this._sendClose()
      if (sent && this.closedPromise) await Promise.race([this.closedPromise, wait(CLOSE_TIMEOUT_MS)])
      if (!this.closedObserved) await this._requestProviderHangup(this.sessionId)
    }
    await this._cleanupLocal()
    this._setState('error', message)
  }

  _stopMicrophone() {
    for (const track of this.stream?.getTracks?.() ?? []) {
      try { track.stop() } catch { /* continue releasing remaining tracks */ }
    }
  }

  async _cleanupLocal() {
    this.clearTimer(this.maxTimer)
    this.clearTimer(this.startedTimer)
    this._stopMicrophone()
    if (this.audioElement) {
      this.audioElement.pause?.()
      this.audioElement.srcObject = null
    }
    try { if (this.dataChannel?.readyState !== 'closed') this.dataChannel?.close?.() } catch { /* best effort */ }
    try { if (this.peerConnection?.signalingState !== 'closed') this.peerConnection?.close?.() } catch { /* best effort */ }
    this.stream = null
    this.dataChannel = null
    this.peerConnection = null
  }
}
