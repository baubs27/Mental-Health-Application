<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { VoiceSessionController } from './voice/VoiceSessionController.js'

const steps = [
  { title: 'Stop', body: 'Pause for a moment. You can stop typing or reacting. You do not need to explain anything.' },
  { title: 'Take a step back', body: 'Give yourself a little space before responding. You can breathe, wait, or use another small pause.' },
  { title: 'Observe', body: 'Notice what is happening inside you and around you. You do not have to judge, label, or fix it.' },
  { title: 'Proceed mindfully', body: 'Choose one small next action, or decide to pause. You can change your mind at any point.' },
]

const view = ref(location.hash === '#support' ? 'support' : 'home')
const exercise = ref(null)
const currentStep = ref(1)
const elapsedSeconds = ref(0)
const exerciseMessages = ref([])
const question = ref('')
const sending = ref(false)
const starting = ref(false)
const exerciseError = ref('')
const historyItems = ref([])
const historyError = ref('')
const appConfig = ref(null)
const finished = ref(false)
let elapsedTimer
let voiceController

const voiceConfig = ref(null)
const voiceState = ref('idle')
const voiceError = ref('')
const playbackBlocked = ref(false)
const remoteAudio = ref(null)

const activeStep = computed(() => steps[currentStep.value - 1])
const elapsedLabel = computed(() => `${Math.floor(elapsedSeconds.value / 60)}:${String(elapsedSeconds.value % 60).padStart(2, '0')}`)
const exerciseActive = computed(() => Boolean(exercise.value && exercise.value.status === 'in_progress' && !finished.value))
const modelBadge = computed(() => {
  if (appConfig.value?.model_mode === 'openai') return `Live model · ${appConfig.value.text_model}`
  if (appConfig.value?.model_mode === 'fail') return 'Failure demo'
  return 'Demo model · deterministic'
})
const voiceStatus = computed(() => ({
  idle: 'Voice is ready when you choose to start.',
  permission: 'Waiting for microphone permission.',
  connecting: 'Connecting securely to the voice session.',
  active: 'Voice session active.',
  muted: 'Microphone muted. Assistant audio can still play.',
  closing: 'Closing the session and releasing the microphone.',
  closed: 'Voice session closed. The STOP exercise remains available.',
  error: voiceError.value || 'Voice could not start. Text guidance remains available.',
}[voiceState.value]))
const canStartVoice = computed(() => Boolean(voiceConfig.value?.configured)
  && ['idle', 'closed', 'error'].includes(voiceState.value))
const canMuteVoice = computed(() => ['active', 'muted'].includes(voiceState.value))
const canEndVoice = computed(() => ['permission', 'connecting', 'active', 'muted'].includes(voiceState.value))

async function loadHistory() {
  try {
    const response = await fetch('/api/history')
    if (!response.ok) throw new Error('History could not be loaded.')
    const result = await response.json()
    historyItems.value = result.sessions
    historyError.value = ''
  } catch {
    historyError.value = 'Session history is temporarily unavailable. Your current exercise can still run.'
  }
}

async function startExercise() {
  if (starting.value || exerciseActive.value) return
  starting.value = true
  exerciseError.value = ''
  try {
    const response = await fetch('/api/exercises', { method: 'POST' })
    if (!response.ok) throw new Error('The exercise could not be saved. Check that the local app is running, then try again.')
    exercise.value = await response.json()
    currentStep.value = exercise.value.current_step
    elapsedSeconds.value = 0
    exerciseMessages.value = []
    question.value = ''
    finished.value = false
    view.value = 'exercise'
    location.hash = 'exercise'
    updateElapsed()
    elapsedTimer = window.setInterval(updateElapsed, 250)
  } catch (error) {
    exerciseError.value = error.message || 'The exercise could not start.'
  } finally {
    starting.value = false
  }
}

function updateElapsed() {
  if (!exercise.value?.started_at || !exerciseActive.value) return
  elapsedSeconds.value = Math.max(0, Math.floor((Date.now() - Date.parse(exercise.value.started_at)) / 1000))
}

async function goToNextStep() {
  if (!exerciseActive.value) return
  exerciseError.value = ''
  if (currentStep.value === steps.length) {
    await finishExercise('completed')
    return
  }
  const nextStep = currentStep.value + 1
  try {
    const response = await fetch(`/api/exercises/${exercise.value.session_id}/step`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ step: nextStep }),
    })
    if (!response.ok) throw new Error('This step could not be saved. You can retry or leave the exercise.')
    currentStep.value = nextStep
    exercise.value.current_step = nextStep
  } catch (error) {
    exerciseError.value = error.message || 'This step could not be saved.'
  }
}

async function sendQuestion() {
  const text = question.value.trim()
  if (!text || sending.value || !exerciseActive.value) return
  question.value = ''
  sending.value = true
  exerciseError.value = ''
  exerciseMessages.value.push({ role: 'user', content: text, request_status: 'complete' })
  const localIndex = exerciseMessages.value.length - 1
  try {
    const response = await fetch(`/api/exercises/${exercise.value.session_id}/messages`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text }),
    })
    const result = await response.json().catch(() => ({}))
    if (!response.ok) {
      exerciseMessages.value[localIndex].request_status = 'failed'
      exerciseError.value = result.detail?.message || result.detail || 'The model request failed. Your message is saved without a reply.'
      return
    }
    exerciseMessages.value.push({
      role: 'assistant',
      content: result.reply,
      request_status: 'complete',
      model_source: result.model_source,
    })
  } catch {
    exerciseMessages.value[localIndex].request_status = 'failed'
    exerciseError.value = 'The request did not reach the app. Check your connection; no reply was invented.'
  } finally {
    sending.value = false
    void loadHistory()
  }
}

async function finishExercise(status, { keepView = false } = {}) {
  if (!exercise.value || finished.value) return true
  exerciseError.value = ''
  try {
    const response = await fetch(`/api/exercises/${exercise.value.session_id}/finish`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status }),
    })
    const result = await response.json().catch(() => ({}))
    if (!response.ok) throw new Error('The session end could not be confirmed by the local database.')
    exercise.value = result
    finished.value = true
    window.clearInterval(elapsedTimer)
    elapsedSeconds.value = result.duration_seconds ?? elapsedSeconds.value
    await loadHistory()
    if (!keepView) {
      view.value = status === 'completed' ? 'complete' : 'home'
      location.hash = status === 'completed' ? 'complete' : ''
      if (status === 'left') exercise.value = null
    }
    return true
  } catch (error) {
    exerciseError.value = error.message || 'The session end could not be saved.'
    sendLeaveBeacon()
    return false
  }
}

function sendLeaveBeacon() {
  if (!exerciseActive.value) return
  const body = new Blob([JSON.stringify({ status: 'left' })], { type: 'application/json' })
  navigator.sendBeacon(`/api/exercises/${exercise.value.session_id}/finish`, body)
}

async function leaveExercise() {
  await finishExercise('left')
}

async function openSupport() {
  if (exerciseActive.value) await finishExercise('left', { keepView: true })
  view.value = 'support'
  location.hash = 'support'
}

function returnHome() {
  view.value = 'home'
  location.hash = ''
  exercise.value = null
  finished.value = false
  void loadHistory()
}

function onHashChange() {
  const next = location.hash.replace('#', '')
  if (next === 'support') view.value = 'support'
  else if (next === 'exercise' && exerciseActive.value) view.value = 'exercise'
  else if (next === 'complete' && finished.value) view.value = 'complete'
  else view.value = 'home'
}

function onPageHide() {
  sendLeaveBeacon()
  void voiceController?.end()
}

async function startVoice() { if (canStartVoice.value) await voiceController?.start() }
function toggleVoiceMute() { voiceController?.mute() }
async function endVoice() { await voiceController?.end() }
function formatDate(value) { return new Date(value).toLocaleString() }
function formatDuration(value) { return `${Math.floor((value || 0) / 60)}:${String((value || 0) % 60).padStart(2, '0')}` }
function modelLabel(source) { return source === 'openai' ? 'GPT-6 Luna' : 'Demo model (deterministic)' }

onMounted(async () => {
  window.addEventListener('hashchange', onHashChange)
  window.addEventListener('pagehide', onPageHide)
  try {
    const response = await fetch('/api/app/config')
    if (response.ok) appConfig.value = await response.json()
  } catch { /* the static STOP skill remains usable if FastAPI is offline */ }
  try {
    const response = await fetch('/api/voice/config')
    if (response.ok) voiceConfig.value = await response.json()
  } catch {
    voiceConfig.value = { configured: false, max_session_seconds: 300 }
  }
  voiceController = new VoiceSessionController({
    audioElement: remoteAudio.value,
    onState: ({ state, error }) => { voiceState.value = state; voiceError.value = error },
    onPlaybackBlocked: (blocked) => { playbackBlocked.value = blocked },
  })
  await loadHistory()
})

onBeforeUnmount(() => {
  window.removeEventListener('hashchange', onHashChange)
  window.removeEventListener('pagehide', onPageHide)
  window.clearInterval(elapsedTimer)
  sendLeaveBeacon()
  void voiceController?.end()
})
</script>

<template>
  <main class="app-shell">
    <header class="topbar">
      <a class="brand" href="#" @click.prevent="returnHome">
        <span class="brand-mark" aria-hidden="true">S</span>
        <span><span class="eyebrow">IST 402 · Coursework prototype</span><strong>Mental Health Skills</strong></span>
      </a>
      <button class="support-link" type="button" @click="openSupport">Crisis support</button>
    </header>

    <template v-if="view === 'support'">
      <section class="support-page" aria-labelledby="support-title">
        <p class="eyebrow">Available without the model</p>
        <h1 id="support-title">Crisis support</h1>
        <p>If you may be in immediate danger, contact your local emergency services or a trusted person now.</p>
        <p>This coursework demo is not monitored and cannot provide emergency support. You can leave the exercise without completing it.</p>
        <button class="button secondary" type="button" @click="returnHome">Return to the app</button>
      </section>
    </template>

    <template v-else-if="view === 'exercise' && exercise">
      <p class="notice">Use a fictional example. This demo is not therapy, diagnosis, medical advice, or a monitored support service.</p>
      <section class="card exercise-card" aria-labelledby="exercise-title">
        <div class="exercise-topline">
          <div><p class="eyebrow">STOP · Step {{ currentStep }} of 4</p><h1 id="exercise-title">{{ activeStep.title }}</h1></div>
          <div class="timer" role="timer" aria-label="Exercise duration">{{ elapsedLabel }}</div>
        </div>
        <div class="progress-track" role="progressbar" :aria-valuenow="currentStep" aria-valuemin="1" aria-valuemax="4" :aria-label="`Step ${currentStep} of 4`"><span :style="{ width: `${currentStep * 25}%` }"></span></div>
        <p class="step-copy">{{ activeStep.body }}</p>
        <div class="exercise-actions">
          <button class="button primary" type="button" @click="goToNextStep">{{ currentStep === 4 ? 'Complete STOP' : 'Continue' }}</button>
          <button class="button quiet" type="button" @click="leaveExercise">Leave exercise</button>
        </div>
        <p v-if="exerciseError" class="error-message" role="alert">{{ exerciseError }}</p>
      </section>

      <section class="card model-card" aria-labelledby="model-title">
        <div class="section-heading"><div><p class="eyebrow">Optional model help</p><h2 id="model-title">Ask about a STOP step</h2></div><span class="tag">{{ modelBadge }}</span></div>
        <p class="small-note">The guide explains the reviewed skill; it does not decide your next action. Use a fictional example. Messages are saved locally. Live mode sends them to OpenAI.</p>
        <div class="chat-log exercise-chat" aria-live="polite" aria-label="Saved exercise conversation">
          <article v-for="(item, index) in exerciseMessages" :key="index" class="message" :class="item.role">
            <p class="message-label">{{ item.role === 'user' ? 'You' : modelLabel(item.model_source) }}</p>
            <p>{{ item.content }}</p>
            <p v-if="item.request_status === 'failed'" class="failed-note">No model reply was saved. You can try again or continue the exercise.</p>
          </article>
        </div>
        <form class="chat-form" @submit.prevent="sendQuestion">
          <label class="sr-only" for="exercise-question">Question about STOP</label>
          <input id="exercise-question" v-model="question" maxlength="2000" autocomplete="off" placeholder="What does Observe mean?" :disabled="sending || !exerciseActive" />
          <button class="button secondary" type="submit" :disabled="sending || !question.trim()">{{ sending ? 'Asking…' : 'Ask' }}</button>
        </form>
        <p v-if="exerciseError" class="error-message" role="alert">{{ exerciseError }}</p>
      </section>
    </template>

    <template v-else-if="view === 'complete'">
      <section class="card completion-card" aria-labelledby="complete-title">
        <p class="eyebrow">Session saved</p>
        <h1 id="complete-title">You completed the STOP steps</h1>
        <p>Recorded duration: <strong>{{ formatDuration(exercise?.duration_seconds) }}</strong>. Completing the steps does not measure mental health or improvement.</p>
        <button class="button primary" type="button" @click="returnHome">Return to the app</button>
      </section>
    </template>

    <template v-else>
      <p class="notice">For fictional coursework scenarios only. This is a learning prototype, not therapy, diagnosis, medical advice, or a monitored support service.</p>
      <section class="card welcome-card" aria-labelledby="welcome-title">
        <p class="eyebrow">A short guided practice</p>
        <h1 id="welcome-title">Try the STOP skill</h1>
        <p>Move through the four steps at your own pace. You can leave at any point or open Crisis support.</p>
        <button class="button primary start-button" type="button" :disabled="starting" @click="startExercise">{{ starting ? 'Starting…' : 'Start STOP' }}</button>
        <p v-if="exerciseError" class="error-message" role="alert">{{ exerciseError }}</p>
      </section>

      <section class="card steps-overview" aria-labelledby="steps-title">
        <div class="section-heading"><div><p class="eyebrow">Four steps · about 90 seconds</p><h2 id="steps-title">What to expect</h2></div><span class="tag">You stay in control</span></div>
        <ol><li v-for="(step, index) in steps" :key="step.title"><span class="step-number">{{ index + 1 }}</span><span><strong>{{ step.title }}</strong><small>{{ step.body }}</small></span></li></ol>
      </section>

      <section class="card history-card" aria-labelledby="history-title">
        <div class="section-heading"><div><p class="eyebrow">Local SQLite</p><h2 id="history-title">Recent sessions</h2></div><button class="button quiet refresh-button" type="button" @click="loadHistory">Refresh</button></div>
        <p class="small-note">Session status, measured duration, and conversation are stored on this computer for the coursework demo. Do not enter real personal details.</p>
        <p v-if="historyError" class="error-message" role="alert">{{ historyError }}</p>
        <p v-else-if="!historyItems.length" class="empty-state">No sessions saved yet.</p>
        <details v-for="item in historyItems" :key="item.session_id" class="history-entry">
          <summary><span>{{ formatDate(item.started_at) }} · {{ item.skill }} · {{ item.status }}</span><strong>{{ item.status === 'in_progress' ? 'In progress' : formatDuration(item.duration_seconds) }}</strong></summary>
          <p class="small-note">Step {{ item.current_step }} of 4 · session {{ item.session_id.slice(0, 8) }}</p>
          <article v-for="message in item.messages" :key="message.message_id" class="history-message">
            <strong>{{ message.role === 'user' ? 'You' : modelLabel(message.model_source) }}:</strong> {{ message.content }}
            <span v-if="message.request_status === 'failed'" class="failed-note">Model response failed; no assistant reply stored.</span>
          </article>
          <p v-if="!item.messages.length" class="small-note">No conversation messages in this session.</p>
        </details>
      </section>

      <section class="card voice-card" aria-labelledby="voice-title">
        <div class="section-heading"><div><p class="eyebrow">Optional · WebRTC</p><h2 id="voice-title">Talk through a question</h2></div><span class="tag" :class="{ ready: voiceConfig?.configured }">{{ voiceConfig?.configured ? 'Configured' : 'Not configured' }}</span></div>
        <p class="voice-description">Voice is a separate optional feature. Audio and transcripts are not saved by this app; text practice and the crisis route work without voice.</p>
        <div class="voice-controls">
          <button class="button primary" type="button" :disabled="!canStartVoice" @click="startVoice">Start voice</button>
          <button class="button secondary" type="button" :disabled="!canMuteVoice" @click="toggleVoiceMute">{{ voiceState === 'muted' ? 'Unmute microphone' : 'Mute microphone' }}</button>
          <button class="button quiet" type="button" :disabled="!canEndVoice" @click="endVoice">End voice</button>
        </div>
        <p class="status" role="status" aria-live="polite">{{ voiceStatus }}</p>
        <p v-if="voiceError" class="error-message" role="alert">{{ voiceError }}</p>
        <p v-if="voiceConfig && !voiceConfig.configured" class="small-note">Voice requires a server-side key. No key belongs in this browser.</p>
        <button v-if="playbackBlocked" class="button secondary playback-button" type="button" @click="voiceController?.enableAssistantAudio()">Enable assistant audio</button>
        <audio ref="remoteAudio" autoplay playsinline class="audio-output" aria-label="Assistant voice audio"></audio>
      </section>
    </template>

    <footer class="footer-note">This local prototype is for fictional examples. It does not diagnose or monitor people. Session and message data are stored in the local SQLite file; provider data handling depends on the configured API account.</footer>
  </main>
</template>
