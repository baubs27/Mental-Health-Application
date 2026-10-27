<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { VoiceSessionController } from './voice/VoiceSessionController.js'

const steps = [
  { title: 'Stop', body: 'Pause for a moment. You do not need to explain anything.' },
  { title: 'Take a step back', body: 'Give yourself a little space before responding. You can wait or take a comfortable breath.' },
  { title: 'Observe', body: 'Notice what is happening inside and around you. You do not have to judge or fix it.' },
  { title: 'Proceed mindfully', body: 'Choose one small next action, or decide to pause. You can change your mind at any point.' },
]
const navItems = [
  { id: 'home', label: 'Home', icon: '⌂' }, { id: 'activities', label: 'Activities', icon: '✿' },
  { id: 'chat', label: 'Chat', icon: '♡' }, { id: 'history', label: 'History', icon: '◷' },
  { id: 'profile', label: 'Profile', icon: '○' }, { id: 'support', label: 'Crisis', icon: '!' },
]
const chatStarters = [
  'I’ve had a stressful day.',
  'I’m not sure where to start.',
  'Can you help me think through a situation?',
  'I just want to talk.',
]
const initialRoute = location.hash.slice(1)
const view = ref(initialRoute === 'support' ? 'support' : navItems.some(item => item.id === initialRoute) ? initialRoute : 'home')
const exercise = ref(null)
const breathingSession = ref(null)
const currentStep = ref(1)
const elapsedSeconds = ref(0)
const breathingSeconds = ref(0)
const breathingPhase = ref('Breathe in')
const exerciseMessages = ref([])
const question = ref('')
const chatSessions = ref([])
const activeChatSessionId = ref(null)
const chatMessages = ref([])
const chatText = ref('')
const chatSending = ref(false)
const chatError = ref('')
const savedChats = ref([])
const sending = ref(false)
const starting = ref(false)
const exerciseError = ref('')
const historyItems = ref([])
const checkins = ref([])
const historyError = ref('')
const appConfig = ref(null)
const finished = ref(false)
const breathingFinishing = ref(false)
const moodChoice = ref('')
const moodMessage = ref('')
const preferences = ref({ default_skill: 'paced_breathing', animate_breathing: true })
let elapsedTimer
let voiceController
const voiceConfig = ref(null)
const voiceState = ref('idle')
const voiceError = ref('')
const playbackBlocked = ref(false)
const remoteAudio = ref(null)

const activeStep = computed(() => steps[currentStep.value - 1])
const elapsedLabel = computed(() => formatDuration(elapsedSeconds.value))
const exerciseActive = computed(() => Boolean(exercise.value && exercise.value.status === 'in_progress' && !finished.value))
const breathingActive = computed(() => Boolean(breathingSession.value && breathingSession.value.status === 'in_progress'))
const selectedNav = computed(() => ['exercise', 'breathing', 'complete'].includes(view.value) ? '' : view.value)
const modelBadge = computed(() => appConfig.value?.model_mode === 'openai' ? `Live model · ${appConfig.value.text_model}` : appConfig.value?.model_mode === 'fail' ? 'Failure demo' : 'Demo model · deterministic')
const voiceStatus = computed(() => ({ idle: 'Voice is ready when you choose to start.', permission: 'Waiting for microphone permission.', connecting: 'Connecting securely to the voice session.', active: 'Voice session active.', muted: 'Microphone muted. Assistant audio can still play.', closing: 'Closing the session and releasing the microphone.', closed: 'Voice session closed. Text practice remains available.', error: voiceError.value || 'Voice could not start. Text guidance remains available.' }[voiceState.value]))
const canStartVoice = computed(() => Boolean(voiceConfig.value?.configured) && ['idle', 'closed', 'error'].includes(voiceState.value))
const canMuteVoice = computed(() => ['active', 'muted'].includes(voiceState.value))
const canEndVoice = computed(() => ['permission', 'connecting', 'active', 'muted'].includes(voiceState.value))
const monthSessions = computed(() => historyItems.value.filter(item => new Date(item.started_at).getMonth() === new Date().getMonth() && new Date(item.started_at).getFullYear() === new Date().getFullYear()))
const monthMinutes = computed(() => Math.round(monthSessions.value.reduce((sum, item) => sum + (item.duration_seconds || 0), 0) / 60))
const monthTitle = computed(() => new Date().toLocaleDateString(undefined, { month: 'long', year: 'numeric' }))

async function loadHistory() {
  try {
    const response = await fetch('/api/history')
    if (!response.ok) throw new Error()
    const result = await response.json()
    historyItems.value = result.sessions || []
    checkins.value = result.checkins || []
    savedChats.value = result.chats || []
    historyError.value = ''
  } catch {
    historyError.value = 'Your saved activity is temporarily unavailable. You can still use the practices.'
  }
}
async function loadChatSessions() {
  try {
    const response = await fetch('/api/chat/sessions')
    if (!response.ok) throw new Error()
    const result = await response.json()
    chatSessions.value = result.sessions || []
    const selected = chatSessions.value.find(item => item.session_id === activeChatSessionId.value)
      || chatSessions.value[0]
    if (selected) {
      activeChatSessionId.value = selected.session_id
      chatMessages.value = selected.messages || []
    } else if (!activeChatSessionId.value) chatMessages.value = []
  } catch { chatError.value = 'Saved conversations are temporarily unavailable.' }
}
function chooseChatSession(id) {
  const session = chatSessions.value.find(item => item.session_id === id)
  if (!session) return
  activeChatSessionId.value = id
  chatMessages.value = session.messages || []
  chatError.value = ''
}
function startNewConversation() {
  activeChatSessionId.value = null
  chatMessages.value = []
  chatText.value = ''
  chatError.value = ''
}
function chatTitle(session) {
  const first = session.messages?.find(item => item.role === 'user')?.content?.trim()
  return first ? (first.length > 48 ? `${first.slice(0, 48)}…` : first) : `Conversation · ${formatDate(session.created_at)}`
}
async function loadProfile() {
  try {
    const response = await fetch('/api/profile')
    if (response.ok) preferences.value = await response.json()
  } catch { /* defaults remain available */ }
}
async function saveProfile() {
  try {
    const response = await fetch('/api/profile', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(preferences.value) })
    if (!response.ok) throw new Error()
    preferences.value = await response.json()
  } catch { exerciseError.value = 'Your profile setting could not be saved. Please try again.' }
}
async function submitCheckin() {
  if (!moodChoice.value) return
  moodMessage.value = ''
  try {
    const response = await fetch('/api/mood-checkins', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ mood: moodChoice.value }) })
    if (!response.ok) throw new Error()
    moodChoice.value = ''
    moodMessage.value = 'Your check-in is saved. You can remove it from History.'
    await loadHistory()
  } catch { moodMessage.value = 'That check-in was not saved. You can try again or skip it.' }
}
async function deleteCheckin(id) {
  try {
    const response = await fetch(`/api/mood-checkins/${id}`, { method: 'DELETE' })
    if (!response.ok) throw new Error()
    checkins.value = checkins.value.filter(item => item.checkin_id !== id)
  } catch { historyError.value = 'This check-in could not be removed. Please retry.' }
}
async function startExercise() {
  if (starting.value || exerciseActive.value) return
  starting.value = true
  exerciseError.value = ''
  try {
    const response = await fetch('/api/exercises', { method: 'POST' })
    if (!response.ok) throw new Error('The practice could not be saved. Check that the local app is running, then try again.')
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
  } catch (error) { exerciseError.value = error.message || 'The practice could not start.' }
  finally { starting.value = false }
}
function updateElapsed() {
  if (!exercise.value?.started_at || !exerciseActive.value) return
  elapsedSeconds.value = Math.max(0, Math.floor((Date.now() - Date.parse(exercise.value.started_at)) / 1000))
}
async function goToNextStep() {
  if (!exerciseActive.value) return
  exerciseError.value = ''
  if (currentStep.value === steps.length) { await finishExercise('completed'); return }
  const next = currentStep.value + 1
  try {
    const response = await fetch(`/api/exercises/${exercise.value.session_id}/step`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ step: next }) })
    if (!response.ok) throw new Error('This step could not be saved. Retry or leave the practice.')
    currentStep.value = next
    exercise.value.current_step = next
  } catch (error) { exerciseError.value = error.message || 'This step could not be saved.' }
}
async function sendQuestion() {
  const message = question.value.trim()
  if (!message || sending.value || !exerciseActive.value) return
  question.value = ''
  sending.value = true
  exerciseError.value = ''
  exerciseMessages.value.push({ role: 'user', content: message, request_status: 'complete' })
  const index = exerciseMessages.value.length - 1
  try {
    const response = await fetch(`/api/exercises/${exercise.value.session_id}/messages`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ message }) })
    const result = await response.json().catch(() => ({}))
    if (!response.ok) {
      exerciseMessages.value[index].request_status = 'failed'
      exerciseError.value = result.detail?.message || result.detail || 'The model request failed. Your message is saved without a reply.'
      return
    }
    exerciseMessages.value.push({ role: 'assistant', content: result.reply, request_status: 'complete', model_source: result.model_source })
  } catch {
    exerciseMessages.value[index].request_status = 'failed'
    exerciseError.value = 'The request did not reach the app. Check your connection; no reply was invented.'
  } finally { sending.value = false; void loadHistory() }
}
async function sendChatMessage() {
  const message = chatText.value.trim()
  if (!message || chatSending.value) return
  chatText.value = ''
  chatSending.value = true
  chatError.value = ''
  chatMessages.value.push({ role: 'user', content: message, request_status: 'complete' })
  const localIndex = chatMessages.value.length - 1
  let messageRequestReachedServer = false
  try {
    if (!activeChatSessionId.value) {
      const start = await fetch('/api/chat/sessions', { method: 'POST' })
      if (!start.ok) throw new Error('A conversation could not be started. Please retry.')
      const session = await start.json()
      activeChatSessionId.value = session.session_id
    }
    const response = await fetch(`/api/chat/sessions/${activeChatSessionId.value}/messages`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message }),
    })
    messageRequestReachedServer = true
    const result = await response.json().catch(() => ({}))
    if (!response.ok) {
      chatMessages.value[localIndex].request_status = 'failed'
      chatError.value = result.detail?.message || result.detail || 'The AI could not reply. Your message is saved without a response.'
      return
    }
    chatMessages.value.push({ role: 'assistant', content: result.reply, request_status: 'complete', model_source: result.model_source })
  } catch (error) {
    chatMessages.value[localIndex].request_status = 'failed'
    chatError.value = error.message || 'The conversation could not reach the app. You can try again.'
  } finally {
    chatSending.value = false
    if (messageRequestReachedServer) {
      void loadChatSessions()
      void loadHistory()
    }
  }
}
async function finishExercise(status, { keepView = false } = {}) {
  if (!exercise.value || finished.value) return true
  exerciseError.value = ''
  try {
    const response = await fetch(`/api/exercises/${exercise.value.session_id}/finish`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ status }) })
    const result = await response.json().catch(() => ({}))
    if (!response.ok) throw new Error('The practice end could not be confirmed by the local database.')
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
  } catch (error) { exerciseError.value = error.message || 'The practice end could not be saved.'; sendLeaveBeacon(); return false }
}
async function leaveExercise() { await finishExercise('left') }
function sendLeaveBeacon() {
  if (exerciseActive.value) navigator.sendBeacon(`/api/exercises/${exercise.value.session_id}/finish`, new Blob([JSON.stringify({ status: 'left' })], { type: 'application/json' }))
  if (breathingActive.value) navigator.sendBeacon(`/api/breathing/sessions/${breathingSession.value.session_id}/finish`, new Blob([JSON.stringify({ status: 'left' })], { type: 'application/json' }))
}
async function startBreathing() {
  if (starting.value || breathingActive.value) return
  starting.value = true
  exerciseError.value = ''
  try {
    const response = await fetch('/api/breathing/sessions', { method: 'POST' })
    if (!response.ok) throw new Error('Paced breathing could not start. Please retry.')
    breathingSession.value = await response.json()
    breathingSeconds.value = 0
    view.value = 'breathing'
    location.hash = 'breathing'
    elapsedTimer = window.setInterval(updateBreathing, 150)
    updateBreathing()
  } catch (error) { exerciseError.value = error.message || 'Paced breathing could not start.' }
  finally { starting.value = false }
}
function updateBreathing() {
  if (!breathingSession.value?.started_at || !breathingActive.value) return
  breathingSeconds.value = Math.max(0, (Date.now() - Date.parse(breathingSession.value.started_at)) / 1000)
  const withinCycle = breathingSeconds.value % 10
  breathingPhase.value = withinCycle < 4 ? 'Breathe in gently' : 'Breathe out slowly'
  if (breathingSeconds.value >= 50 && !breathingFinishing.value) {
    window.clearInterval(elapsedTimer)
    void finishBreathing('completed')
  }
}
async function finishBreathing(status) {
  if (!breathingSession.value || !breathingActive.value || breathingFinishing.value) return true
  breathingFinishing.value = true
  try {
    const response = await fetch(`/api/breathing/sessions/${breathingSession.value.session_id}/finish`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ status }) })
    const result = await response.json().catch(() => ({}))
    if (!response.ok) throw new Error('The practice end could not be saved.')
    breathingSession.value = result
    window.clearInterval(elapsedTimer)
    breathingSeconds.value = result.duration_seconds
    await loadHistory()
    if (status === 'completed') { view.value = 'complete'; location.hash = 'complete' }
    else { breathingSession.value = null; view.value = 'home'; location.hash = '' }
    return true
  } catch (error) { exerciseError.value = error.message || 'The practice end could not be saved.'; sendLeaveBeacon(); return false }
  finally { breathingFinishing.value = false }
}
async function openSupport() {
  if (exerciseActive.value) await finishExercise('left', { keepView: true })
  if (breathingActive.value) await finishBreathing('left')
  view.value = 'support'
  location.hash = 'support'
}
async function navigate(id) {
  if (id === 'support') { await openSupport(); return }
  if (exerciseActive.value) await finishExercise('left', { keepView: true })
  if (breathingActive.value) await finishBreathing('left')
  exercise.value = null
  view.value = id
  location.hash = id === 'home' ? '' : id
  await loadHistory()
  if (id === 'chat') await loadChatSessions()
}
function returnHome() { void navigate('home') }
function onHashChange() {
  const next = location.hash.slice(1)
  if (next === 'support') view.value = 'support'
  else if (next === 'exercise' && exerciseActive.value) view.value = 'exercise'
  else if (next === 'breathing' && breathingActive.value) view.value = 'breathing'
  else if (next === 'complete' && finished.value) view.value = 'complete'
  else if (navItems.some(item => item.id === next)) view.value = next || 'home'
  else view.value = 'home'
}
function onPageHide() { sendLeaveBeacon(); void voiceController?.end() }
async function startVoice() { if (canStartVoice.value) await voiceController?.start() }
function toggleVoiceMute() { voiceController?.mute() }
async function endVoice() { await voiceController?.end() }
function formatDate(value) { return new Date(value).toLocaleString() }
function formatDuration(value) { const seconds = Math.max(0, Math.floor(value || 0)); return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}` }
function sessionName(item) { return item.skill === 'STOP' ? 'STOP practice' : 'Paced breathing' }
function modelLabel(source) { return source === 'openai' ? 'Live model' : 'Demo model (deterministic)' }

onMounted(async () => {
  window.addEventListener('hashchange', onHashChange)
  window.addEventListener('pagehide', onPageHide)
  try { const response = await fetch('/api/app/config'); if (response.ok) appConfig.value = await response.json() } catch { /* practices work without the model */ }
  try { const response = await fetch('/api/voice/config'); if (response.ok) voiceConfig.value = await response.json() }
  catch { voiceConfig.value = { configured: false, max_session_seconds: 300 } }
  voiceController = new VoiceSessionController({ audioElement: remoteAudio.value, onState: ({ state, error }) => { voiceState.value = state; voiceError.value = error }, onPlaybackBlocked: blocked => { playbackBlocked.value = blocked } })
  await Promise.all([loadHistory(), loadProfile(), loadChatSessions()])
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
      <a class="brand" href="#" @click.prevent="returnHome"><span class="brand-mark" aria-hidden="true"><svg viewBox="0 0 32 32" focusable="false"><path d="M16 27V14m0 7c-6 0-10-4-10-10 6 0 10 4 10 10Zm0-5c0-6 4-10 10-10 0 6-4 10-10 10Z"/></svg></span><span><span class="eyebrow">IST 402 · Coursework prototype</span><strong>Little Pause</strong></span></a>
      <button class="support-link" type="button" @click="openSupport">Crisis support</button>
    </header>

    <p class="notice">For fictional coursework scenarios only. This prototype is not therapy, diagnosis, medical advice, or monitored support.</p>

    <template v-if="view === 'support'">
      <section class="support-page" aria-labelledby="support-title"><p class="eyebrow">Here whenever you need it</p><h1 id="support-title">Crisis support</h1><p>If you may be in immediate danger, contact local emergency services or someone you trust now.</p><p>This coursework app is not monitored and cannot provide emergency support. You can leave any practice without completing it.</p><div class="support-options"><p><strong>In the United States and territories</strong><br>Call or text 988, or use the official Lifeline chat.</p><a class="button primary" href="tel:988">Call 988</a><a class="button secondary" href="sms:988">Text 988</a><a class="button secondary" href="https://988lifeline.org/get-help/" target="_blank" rel="noopener">Open 988 chat and help</a></div></section>
    </template>

    <template v-else-if="view === 'exercise' && exercise">
      <section class="card exercise-card"><div class="exercise-topline"><div><p class="eyebrow">STOP · Step {{ currentStep }} of 4</p><h1>{{ activeStep.title }}</h1></div><div class="timer" role="timer" aria-label="Practice duration">{{ elapsedLabel }}</div></div><div class="progress-track" role="progressbar" :aria-valuenow="currentStep" aria-valuemin="1" aria-valuemax="4" :aria-label="`Step ${currentStep} of 4`"><span :style="{ width: `${currentStep * 25}%` }"></span></div><p class="step-copy">{{ activeStep.body }}</p><div class="exercise-actions"><button class="button primary" type="button" @click="goToNextStep">{{ currentStep === 4 ? 'Complete STOP' : 'Continue' }}</button><button class="button quiet" type="button" @click="leaveExercise">Leave practice</button></div><p v-if="exerciseError" class="error-message" role="alert">{{ exerciseError }}</p></section>
      <section class="card model-card"><div class="section-heading"><div><p class="eyebrow">Optional AI conversation</p><h2>Talk about what’s on your mind</h2></div><span class="tag">{{ modelBadge }}</span></div><p class="small-note">You can ask about STOP, your day, or something else. Share only what you’re comfortable sharing. Messages are saved locally; in live mode your question and recent conversation are sent to OpenAI.</p><div class="chat-log" aria-live="polite" aria-label="Practice conversation"><article v-for="(item, index) in exerciseMessages" :key="index" class="message" :class="item.role"><p class="message-label">{{ item.role === 'user' ? 'You' : modelLabel(item.model_source) }}</p><p>{{ item.content }}</p><p v-if="item.request_status === 'failed'" class="failed-note">No reply was saved. You can try again or continue the practice.</p></article></div><form class="chat-form" @submit.prevent="sendQuestion"><label class="sr-only" for="exercise-question">Message the AI</label><input id="exercise-question" v-model="question" maxlength="2000" autocomplete="off" placeholder="What has been on your mind?" :disabled="sending || !exerciseActive"><button class="button secondary" type="submit" :disabled="sending || !question.trim()">{{ sending ? 'Sending…' : 'Send' }}</button></form><p v-if="exerciseError" class="error-message" role="alert">{{ exerciseError }}</p></section>
    </template>

    <template v-else-if="view === 'breathing' && breathingSession">
      <section class="card breathing-card"><p class="eyebrow">A short guided practice · 5 cycles</p><h1>Paced breathing</h1><p class="small-note">Breathe comfortably. There is no pause or breath hold. You can stop whenever you like.</p><div class="breath-stage"><div class="breath-orb" :class="{ animated: preferences.animate_breathing }" :style="{ '--breath-progress': `${Math.min(breathingSeconds % 10 / 10, 1) * 100}%` }" role="img" :aria-label="breathingPhase"><span>{{ breathingPhase }}</span></div></div><p class="breath-count">Cycle {{ Math.min(5, Math.floor(breathingSeconds / 10) + 1) }} of 5 · {{ formatDuration(breathingSeconds) }} / 0:50</p><button class="button quiet" type="button" @click="preferences.animate_breathing = !preferences.animate_breathing; saveProfile()">{{ preferences.animate_breathing ? 'Turn animation off' : 'Turn animation on' }}</button><button class="button quiet leave-breathing" type="button" @click="finishBreathing('left')">Stop practice</button><p v-if="exerciseError" class="error-message" role="alert">{{ exerciseError }}</p></section>
    </template>

    <template v-else-if="view === 'complete'"><section class="card completion-card"><p class="eyebrow">Session saved</p><h1>{{ exercise?.skill === 'STOP' ? 'You completed the STOP steps' : 'Practice complete' }}</h1><p>Recorded duration: <strong>{{ formatDuration(exercise?.duration_seconds ?? breathingSession?.duration_seconds) }}</strong>. Time is a record of the session, not a measure of wellbeing or improvement.</p><button class="button primary" type="button" @click="returnHome">Return home</button></section></template>

    <template v-else-if="view === 'home'">
      <section class="card welcome-card"><div class="welcome-copy"><p class="eyebrow">A gentle place to begin</p><h1>A little room to pause.</h1><p>Choose a small practice for this moment. You can stop at any time.</p></div><svg class="hero-plant" viewBox="0 0 180 170" aria-hidden="true"><path class="plant-stem" d="M91 166c3-38-2-70-22-105m25 105c-2-42 11-78 39-112m-48 70c-17-13-29-19-44-21m52 35c15-15 29-24 46-30"/><path class="plant-leaf plant-leaf-one" d="M69 75C43 69 34 50 38 32c24 2 39 17 36 41-1 4-2 5-5 2Z"/><path class="plant-leaf plant-leaf-two" d="M91 91c-5-27 8-45 29-52 9 23 2 43-21 54-4 2-6 1-8-2Z"/><path class="plant-leaf plant-leaf-three" d="M53 124c-20-1-32-14-35-32 20-4 36 5 41 24 1 4-1 7-6 8Z"/><path class="plant-leaf plant-leaf-four" d="M111 132c8-22 27-29 45-23-4 20-20 31-39 29-5 0-7-2-6-6Z"/></svg></section>
      <section class="card checkin-card"><div class="section-heading"><div><p class="eyebrow">Optional · your words for yourself</p><h2>How are you feeling?</h2></div><span aria-hidden="true">☀</span></div><p>Only you choose a check-in. The app does not infer how you feel.</p><div class="mood-options"><button v-for="mood in [{ id: 'low', text: 'A little low', icon: '☁' }, { id: 'steady', text: 'Somewhere in the middle', icon: '◒' }, { id: 'good', text: 'Doing okay', icon: '☀' }]" :key="mood.id" type="button" class="mood-button" :aria-pressed="moodChoice === mood.id" @click="moodChoice = mood.id"><span>{{ mood.icon }}</span>{{ mood.text }}</button></div><div class="checkin-submit"><button class="button primary" type="button" :disabled="!moodChoice" @click="submitCheckin">Save check-in</button><button class="button quiet" type="button" @click="moodChoice = ''; moodMessage = 'No check-in saved.'">Skip</button></div><p v-if="moodMessage" class="small-note" role="status">{{ moodMessage }}</p></section>
      <section v-if="preferences.default_skill === 'paced_breathing'" class="card featured-practice"><div><p class="eyebrow">Your usual practice · 50 seconds</p><h2>Paced breathing</h2><p>Five gentle cycles: breathe in for four seconds, out for six. No hold.</p><button class="button primary start-button" type="button" :disabled="starting" @click="startBreathing">{{ starting ? 'Opening…' : 'Open practice' }}</button></div><div class="feature-orb" aria-hidden="true">breathe</div></section>
      <section v-else class="card featured-practice"><div><p class="eyebrow">Your usual practice · four short steps</p><h2>STOP</h2><p>Pause, notice what is happening, and choose one small next action.</p><button class="button primary start-button" type="button" :disabled="starting" @click="startExercise">{{ starting ? 'Opening…' : 'Open practice' }}</button></div><div class="feature-orb leaf-orb" aria-hidden="true">✿</div></section>
      <section class="card quick-links"><p class="eyebrow">Nice to explore</p><button type="button" @click="navigate('chat')"><span>♡</span><span><strong>Talk it through</strong><small>Start a conversation about anything</small></span><b>›</b></button><button type="button" @click="navigate('history')"><span>◷</span><span><strong>Your days</strong><small>Check-ins and practice history</small></span><b>›</b></button><button type="button" @click="navigate('activities')"><span>✿</span><span><strong>Activities</strong><small>Explore short guided practices</small></span><b>›</b></button></section>
    </template>

    <template v-else-if="view === 'activities'"><section class="page-heading"><p class="eyebrow">Choose what fits this moment</p><h1>Activities</h1><p>There is no required order. You can leave any practice at any time.</p></section><section class="card activity-card"><div class="activity-icon">◌</div><div><p class="eyebrow">50 seconds · gentle pacing</p><h2>Paced breathing</h2><p>Follow an optional visual cue for five comfortable inhale/exhale cycles. No breath holds.</p><button class="button primary" type="button" :disabled="starting" @click="startBreathing">{{ starting ? 'Opening…' : 'Start paced breathing' }}</button></div></section><section class="card activity-card"><div class="activity-icon warm">✦</div><div><p class="eyebrow">Four short steps</p><h2>STOP</h2><p>A brief pause, notice, and choice. You do not need to share or explain anything.</p><button class="button secondary" type="button" :disabled="starting" @click="startExercise">{{ starting ? 'Opening…' : 'Start STOP' }}</button></div></section><p v-if="exerciseError" class="error-message" role="alert">{{ exerciseError }}</p></template>

    <template v-else-if="view === 'chat'">
      <section class="page-heading">
        <p class="eyebrow">Optional AI conversation</p>
        <h1>Talk about anything on your mind</h1>
        <p>Start with a prompt or write your own. You can change topics at any time; you don’t need to follow a skill guide.</p>
      </section>
      <section class="card open-chat-card">
        <div class="section-heading">
          <div><p class="eyebrow">A conversation at your pace</p><h2>{{ activeChatSessionId ? 'Your conversation' : 'Where would you like to start?' }}</h2></div>
          <button v-if="activeChatSessionId || chatMessages.length" class="button quiet refresh-button" type="button" @click="startNewConversation">New conversation</button>
        </div>
        <div v-if="!chatMessages.length" class="prompt-suggestions" aria-label="Conversation starters">
          <p class="eyebrow">Not sure what to say? Try one of these</p>
          <button v-for="prompt in chatStarters" :key="prompt" type="button" @click="chatText = prompt">{{ prompt }}</button>
        </div>
        <p class="small-note">This AI chat is not therapy or emergency support. Conversations save locally. In live mode, only this chat’s messages are sent to OpenAI; your profile and check-ins are not included. Share only what feels comfortable.</p>
        <div class="chat-log open-chat-log" aria-live="polite" aria-label="Conversation messages">
          <article v-for="(item, index) in chatMessages" :key="item.message_id || `${item.role}-${index}`" class="message" :class="item.role">
            <p class="message-label">{{ item.role === 'user' ? 'You' : modelLabel(item.model_source) }}</p>
            <p>{{ item.content }}</p>
            <p v-if="item.request_status === 'failed'" class="failed-note">No reply was saved. You can send another message or try again.</p>
          </article>
          <p v-if="chatSending" class="status" role="status">Thinking…</p>
        </div>
        <form class="chat-form open-chat-form" @submit.prevent="sendChatMessage">
          <label class="sr-only" for="open-chat-input">Your message</label>
          <input id="open-chat-input" v-model="chatText" maxlength="2000" autocomplete="off" placeholder="What would you like to talk about?" :disabled="chatSending">
          <button class="button primary" type="submit" :disabled="chatSending || !chatText.trim()">{{ chatSending ? 'Sending…' : 'Send' }}</button>
        </form>
        <p v-if="chatError" class="error-message" role="alert">{{ chatError }}</p>
      </section>
      <section v-if="chatSessions.length" class="card previous-chat-card">
        <div class="section-heading"><div><p class="eyebrow">Saved locally</p><h2>Recent conversations</h2></div></div>
        <button v-for="session in chatSessions" :key="session.session_id" class="conversation-choice" :class="{ selected: session.session_id === activeChatSessionId }" type="button" @click="chooseChatSession(session.session_id)">
          <span>{{ chatTitle(session) }}</span><small>{{ formatDate(session.created_at) }} · {{ session.messages.length }} messages</small>
        </button>
      </section>
      <section class="card voice-card">
        <div class="section-heading"><div><p class="eyebrow">Optional · WebRTC voice</p><h2>Talk by voice</h2></div><span class="tag" :class="{ ready: voiceConfig?.configured }">{{ voiceConfig?.configured ? 'Configured' : 'Not configured' }}</span></div>
        <p class="voice-description">Voice is a separate, opt-in conversation. This app does not save voice transcripts. Microphone access starts only when you choose Start voice.</p>
        <div class="voice-controls">
          <button class="button secondary" type="button" :disabled="!canStartVoice" @click="startVoice">Start voice</button>
          <button class="button secondary" type="button" :disabled="!canMuteVoice" @click="toggleVoiceMute">{{ voiceState === 'muted' ? 'Unmute microphone' : 'Mute microphone' }}</button>
          <button class="button quiet" type="button" :disabled="!canEndVoice" @click="endVoice">End voice</button>
        </div>
        <p class="status" role="status" aria-live="polite">{{ voiceStatus }}</p>
        <p v-if="voiceError" class="error-message" role="alert">{{ voiceError }}</p>
        <p v-if="voiceConfig && !voiceConfig.configured" class="small-note">Voice requires a server-side key. No key belongs in the browser.</p>
        <button v-if="playbackBlocked" class="button secondary" type="button" @click="voiceController?.enableAssistantAudio()">Enable assistant audio</button>
        <audio ref="remoteAudio" autoplay playsinline class="audio-output" aria-label="Assistant voice audio" />
      </section>
    </template>

    <template v-else-if="view === 'history'">
      <section class="page-heading"><p class="eyebrow">Your activity · stored on this device</p><h1>Your days</h1><p>History is a record of what you chose to do. It does not measure improvement.</p></section>
      <section class="card month-card">
        <p class="eyebrow">Your month in view</p><h2>{{ monthTitle }}</h2>
        <div class="month-stats"><div><strong>{{ checkins.filter(item => new Date(item.created_at).getMonth() === new Date().getMonth()).length }}</strong><span>check-ins</span></div><div><strong>{{ monthSessions.length }}</strong><span>practices</span></div><div><strong>{{ monthMinutes }}</strong><span>minutes</span></div></div>
      </section>
      <section class="card history-card">
        <div class="section-heading"><div><p class="eyebrow">Practice and check-in log</p><h2>Recent activity</h2></div><button class="button quiet refresh-button" type="button" @click="loadHistory">Refresh</button></div>
        <p v-if="historyError" class="error-message" role="alert">{{ historyError }}</p>
        <p v-else-if="!historyItems.length && !checkins.length && !savedChats.length" class="empty-state">There is no activity saved yet. You can start whenever you like.</p>
        <article v-for="item in historyItems" :key="item.session_id" class="history-entry">
          <div><strong>{{ sessionName(item) }}</strong><span class="history-meta">{{ formatDate(item.started_at) }} · {{ item.status }} · {{ formatDuration(item.duration_seconds) }}</span></div>
          <details v-if="item.messages?.length"><summary>View saved conversation ({{ item.messages.length }} turns)</summary><article v-for="message in item.messages" :key="message.message_id" class="history-message"><strong>{{ message.role === 'user' ? 'You' : modelLabel(message.model_source) }}</strong><p>{{ message.content }}</p><small v-if="message.request_status === 'failed'">Request failed; no answer was saved.</small></article></details>
        </article>
        <div v-if="savedChats.length" class="checkin-history">
          <p class="eyebrow">AI conversations</p>
          <details v-for="session in savedChats" :key="session.session_id" class="saved-chat-entry">
            <summary><span>{{ chatTitle(session) }}</span><small>{{ formatDate(session.created_at) }} · {{ session.messages.length }} messages</small></summary>
            <article v-for="message in session.messages" :key="message.message_id" class="history-message"><strong>{{ message.role === 'user' ? 'You' : modelLabel(message.model_source) }}</strong><p>{{ message.content }}</p><small v-if="message.request_status === 'failed'">No reply was saved for this message.</small></article>
          </details>
        </div>
        <div v-if="checkins.length" class="checkin-history"><p class="eyebrow">How you checked in</p><p v-for="item in checkins" :key="item.checkin_id" class="checkin-row"><span>{{ { low: 'A little low', steady: 'Somewhere in the middle', good: 'Doing okay' }[item.mood] }} · {{ formatDate(item.created_at) }}</span><button class="text-button" type="button" @click="deleteCheckin(item.checkin_id)">Remove</button></p></div>
      </section>
    </template>

    <template v-else-if="view === 'profile'"><section class="page-heading"><p class="eyebrow">Your choices stay yours</p><h1>Profile</h1><p>There is no account or diagnosis in this coursework demo. Settings are local to this installation.</p></section><section class="card profile-card"><p class="eyebrow">Practice preferences</p><label for="default-skill">Your usual practice</label><select id="default-skill" v-model="preferences.default_skill" @change="saveProfile"><option value="paced_breathing">Paced breathing</option><option value="STOP">STOP</option></select><p class="small-note">This only sets the featured practice. You can always choose a different activity.</p><label class="toggle-row"><span><strong>Animate breathing circle</strong><small>Turn off visual movement whenever you prefer.</small></span><input v-model="preferences.animate_breathing" type="checkbox" @change="saveProfile"></label><div class="profile-note"><strong>Screening is not included.</strong><p>This prototype does not score symptoms, assess safety, or make a diagnosis. Crisis support is always available separately.</p></div></section><section class="card profile-card"><p class="eyebrow">Your data</p><h2>Simple and local</h2><p>Check-ins, practice duration, and text conversations are saved in the local SQLite database for this coursework demonstration. They are not tied to a named account. Live model questions are sent to the configured provider.</p><button class="button quiet" type="button" @click="navigate('history')">Review or remove check-ins</button></section></template>

    <p v-if="['home', 'activities'].includes(view) && exerciseError" class="error-message" role="alert">{{ exerciseError }}</p>
    <footer v-if="!['exercise', 'breathing', 'complete', 'support'].includes(view)" class="footer-note">A small pause, at your pace. You can open crisis support at any time.</footer>
    <nav class="bottom-nav" aria-label="Main navigation"><button v-for="item in navItems" :key="item.id" type="button" :class="{ active: selectedNav === item.id, crisis: item.id === 'support' }" :aria-current="selectedNav === item.id ? 'page' : undefined" @click="navigate(item.id)"><span aria-hidden="true">{{ item.icon }}</span><small>{{ item.label }}</small></button></nav>
  </main>
</template>
