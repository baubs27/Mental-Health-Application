<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { VoiceSessionController } from './voice/VoiceSessionController.js'

const chatInput = ref('')
const chatBusy = ref(false)
const chatMessages = ref([
  { role: 'assistant', text: 'I can explain the reviewed STOP steps. This coursework demo does not interpret personal situations.' },
])
const voiceConfig = ref(null)
const voiceState = ref('idle')
const voiceError = ref('')
const voiceSessionCreated = ref(false)
const voiceFinalizationConfirmed = ref(false)
const playbackBlocked = ref(false)
const showSupport = ref(false)
const remoteAudio = ref(null)
let voiceController

const voiceStatus = computed(() => ({
  idle: 'Voice is ready when you choose to start.',
  permission: 'Waiting for microphone permission.',
  connecting: 'Connecting securely to the voice session.',
  active: 'Voice session active.',
  muted: 'Microphone muted. Assistant audio can still play.',
  closing: 'Closing the session and releasing the microphone.',
  closed: 'Voice session closed. Text chat remains available.',
  error: voiceError.value || 'Voice could not start. Text chat remains available.',
}[voiceState.value]))

const canStart = computed(() => Boolean(voiceConfig.value?.configured)
  && ['idle', 'closed', 'error'].includes(voiceState.value))
const canMute = computed(() => ['active', 'muted'].includes(voiceState.value))
const canEnd = computed(() => ['permission', 'connecting', 'active', 'muted'].includes(voiceState.value))

async function loadVoiceConfig() {
  try {
    const response = await fetch('/api/voice/config')
    if (!response.ok) throw new Error()
    voiceConfig.value = await response.json()
  } catch {
    voiceConfig.value = { configured: false, max_session_seconds: 300 }
  }
}

async function sendMessage() {
  const message = chatInput.value.trim()
  if (!message || chatBusy.value) return
  chatMessages.value.push({ role: 'user', text: message })
  chatInput.value = ''
  chatBusy.value = true
  try {
    const response = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message }),
    })
    if (!response.ok) throw new Error()
    const result = await response.json()
    chatMessages.value.push({ role: 'assistant', text: result.reply })
  } catch {
    chatMessages.value.push({
      role: 'assistant',
      text: 'Text chat is available for explaining STOP: Stop; take a step back; observe inside and outside; proceed mindfully.',
    })
  } finally {
    chatBusy.value = false
  }
}

async function startVoice() {
  if (canStart.value) await voiceController?.start()
}

function toggleMute() {
  voiceController?.mute()
}

async function endVoice() {
  await voiceController?.end()
}

async function openSupport() {
  await endVoice()
  showSupport.value = true
}

function onPageExit() {
  void voiceController?.end()
}

onMounted(async () => {
  await loadVoiceConfig()
  voiceController = new VoiceSessionController({
    audioElement: remoteAudio.value,
    onState: ({ state, error }) => {
      voiceState.value = state
      voiceError.value = error
      voiceSessionCreated.value = voiceController?.sessionCreated ?? false
      voiceFinalizationConfirmed.value = voiceController?.finalizationConfirmed ?? false
    },
    onPlaybackBlocked: (blocked) => { playbackBlocked.value = blocked },
  })
  window.addEventListener('pagehide', onPageExit)
})

onBeforeUnmount(() => {
  window.removeEventListener('pagehide', onPageExit)
  void voiceController?.end()
})
</script>

<template>
  <main class="app-shell">
    <header class="topbar">
      <div>
        <p class="eyebrow">IST 402 · Coursework prototype</p>
        <h1>Mental Health Skills</h1>
      </div>
      <button class="support-link" type="button" @click="openSupport">Crisis support</button>
    </header>

    <p class="notice">For fictional coursework scenarios only. This is not therapy, diagnosis, medical advice, or a monitored support service.</p>

    <section class="card chat-card" aria-labelledby="chat-title">
      <div class="section-heading">
        <div>
          <p class="eyebrow">Text chat</p>
          <h2 id="chat-title">Ask about STOP</h2>
        </div>
        <span class="tag">Available without voice</span>
      </div>
      <div class="chat-log" aria-live="polite" aria-label="Text chat messages">
        <article v-for="(item, index) in chatMessages" :key="index" class="message" :class="item.role">
          <p class="message-label">{{ item.role === 'assistant' ? 'App' : 'You' }}</p>
          <p>{{ item.text }}</p>
        </article>
      </div>
      <form class="chat-form" @submit.prevent="sendMessage">
        <label class="sr-only" for="chat-input">Your question</label>
        <input id="chat-input" v-model="chatInput" maxlength="1000" autocomplete="off" placeholder="Ask about one of the STOP steps" :disabled="chatBusy" />
        <button class="button secondary" type="submit" :disabled="chatBusy || !chatInput.trim()">{{ chatBusy ? 'Sending…' : 'Send' }}</button>
      </form>
      <p class="small-note">Text questions are answered from fixed, reviewed STOP information in this starter.</p>
    </section>

    <section class="card voice-card" aria-labelledby="voice-title">
      <div class="section-heading">
        <div>
          <p class="eyebrow">Optional · WebRTC</p>
          <h2 id="voice-title">Talk through a question</h2>
        </div>
        <span class="tag" :class="{ ready: voiceConfig?.configured }">{{ voiceConfig?.configured ? 'Configured' : 'Not configured' }}</span>
      </div>
      <p class="voice-description">Voice starts only when you select the microphone. You can mute or end at any time; audio and transcripts are not saved by this application.</p>
      <div class="voice-controls">
        <button class="button primary" type="button" :disabled="!canStart" @click="startVoice">
          <span aria-hidden="true">●</span> Start voice
        </button>
        <button class="button secondary" type="button" :disabled="!canMute" @click="toggleMute">
          {{ voiceState === 'muted' ? 'Unmute microphone' : 'Mute microphone' }}
        </button>
        <button class="button quiet" type="button" :disabled="!canEnd" @click="endVoice">End voice</button>
      </div>
      <p class="status" role="status" aria-live="polite">{{ voiceStatus }}</p>
      <p v-if="voiceError" class="error-message" role="alert">{{ voiceError }}</p>
      <p v-if="voiceState === 'closed' && voiceSessionCreated && !voiceFinalizationConfirmed" class="error-message" role="status">The microphone and local connection were released, but the provider did not confirm final closure.</p>
      <p v-if="voiceConfig && !voiceConfig.configured" class="small-note">Voice needs an API key configured on FastAPI. No key belongs in this browser.</p>
      <p v-if="voiceState === 'active' || voiceState === 'muted'" class="small-note">This session closes automatically within {{ Math.round((voiceConfig?.max_session_seconds ?? 300) / 60) }} minutes.</p>
      <button v-if="playbackBlocked" class="button secondary playback-button" type="button" @click="voiceController?.enableAssistantAudio()">Enable assistant audio</button>
      <audio ref="remoteAudio" autoplay playsinline class="audio-output" aria-label="Assistant voice audio"></audio>
    </section>

    <footer class="footer-note">No voice recording or transcript is stored in this app. Provider processing and retention are governed by the configured API account.</footer>

    <div v-if="showSupport" class="dialog-backdrop" @click.self="showSupport = false">
      <section class="support-dialog" role="dialog" aria-modal="true" aria-labelledby="support-title">
        <button class="dialog-close" type="button" aria-label="Close crisis support information" @click="showSupport = false">×</button>
        <p class="eyebrow">Independent of the model</p>
        <h2 id="support-title">Crisis support</h2>
        <p>If you may be in immediate danger, contact your local emergency services now. This coursework demo is not monitored and cannot provide emergency support.</p>
        <button class="button secondary" type="button" @click="showSupport = false">Return to the app</button>
      </section>
    </div>
  </main>
</template>
