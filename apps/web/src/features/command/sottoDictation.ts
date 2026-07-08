/*
 * Sotto STT client (AOS-VOICE-002).
 *
 * Streams 16 kHz mono PCM16 from the mic to a self-hosted Sotto server
 * (faster-whisper over WebSocket, tailnet only) and surfaces the final
 * transcript. Ported from Sotto's own web client (clients/web/src/dictate.ts),
 * parameterised for ArchetypeOS: Sotto runs on a DIFFERENT host than this app,
 * so the WS URL and token come from build-time env (VITE_SOTTO_WS_URL,
 * VITE_SOTTO_TOKEN) instead of `location.host`. When the URL is unset the client
 * reports "not configured" and the CommandDeck falls back to type-only input.
 *
 * The token is a tailnet-shared secret embedded at build time; acceptable here
 * because both this app and Sotto are reachable only on the private tailnet.
 */

const SOTTO_WS_URL: string = (import.meta.env.VITE_SOTTO_WS_URL as string | undefined) ?? '';
const SOTTO_TOKEN: string = (import.meta.env.VITE_SOTTO_TOKEN as string | undefined) ?? '';

export interface DictationHandlers {
  onPartial: (text: string) => void;
  onFinal: (transcript: string) => void;
  onError: (message: string) => void;
}

export interface DictationController {
  stop: () => void;
  cancel: () => void;
}

/** True when a Sotto endpoint is configured; else voice input is unavailable. */
export function sottoConfigured(): boolean {
  return SOTTO_WS_URL.trim().length > 0;
}

function dictateUrl(): string {
  // Accept either a bare base ("ws://host:8210") or a full path; normalise to
  // the /ws/dictate endpoint with the token query param.
  const base = SOTTO_WS_URL.replace(/\/+$/, '');
  const path = base.endsWith('/ws/dictate') ? base : `${base}/ws/dictate`;
  return `${path}?token=${encodeURIComponent(SOTTO_TOKEN)}`;
}

function floatToPcm16(input: Float32Array): ArrayBuffer {
  const buf = new ArrayBuffer(input.length * 2);
  const view = new DataView(buf);
  for (let i = 0; i < input.length; i += 1) {
    const s = Math.max(-1, Math.min(1, input[i]));
    view.setInt16(i * 2, s < 0 ? s * 0x8000 : s * 0x7fff, true);
  }
  return buf;
}

// Resample to 16 kHz. Passthrough when the context already runs at 16 kHz;
// otherwise cheap window-average decimation (anti-alias enough for speech).
function downsampleTo16k(input: Float32Array, inRate: number): Float32Array {
  if (inRate === 16000) return input;
  const ratio = inRate / 16000;
  const outLen = Math.floor(input.length / ratio);
  const out = new Float32Array(outLen);
  for (let i = 0; i < outLen; i += 1) {
    const start = Math.floor(i * ratio);
    const end = Math.floor((i + 1) * ratio);
    let sum = 0;
    let n = 0;
    for (let j = start; j < end && j < input.length; j += 1) {
      sum += input[j];
      n += 1;
    }
    out[i] = n ? sum / n : (input[start] ?? 0);
  }
  return out;
}

/**
 * Capture the mic, stream 16 kHz PCM16 to Sotto's /ws/dictate, and surface
 * partials + the formatted final transcript. Call stop() to finalize or
 * cancel() to abort. Rejects (and calls onError) when Sotto is not configured
 * or the mic permission is denied.
 */
export async function startDictation(handlers: DictationHandlers): Promise<DictationController> {
  if (!sottoConfigured()) {
    handlers.onError('voice unavailable — type instead');
    throw new Error('sotto not configured');
  }

  const AudioCtx: typeof AudioContext =
    window.AudioContext ?? (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
  const ctx = new AudioCtx({ sampleRate: 16000 });
  let stream: MediaStream;
  try {
    stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  } catch {
    ctx.close();
    handlers.onError('microphone permission denied');
    throw new Error('mic denied');
  }

  const ws = new WebSocket(dictateUrl());
  ws.binaryType = 'arraybuffer';
  let closed = false;

  const source = ctx.createMediaStreamSource(stream);
  const processor = ctx.createScriptProcessor(2048, 1, 1);
  const mute = ctx.createGain();
  mute.gain.value = 0;

  processor.onaudioprocess = (e) => {
    if (ws.readyState !== WebSocket.OPEN) return;
    const pcm = downsampleTo16k(e.inputBuffer.getChannelData(0), ctx.sampleRate);
    ws.send(floatToPcm16(pcm));
  };

  function teardownAudio() {
    processor.disconnect();
    source.disconnect();
    mute.disconnect();
    stream.getTracks().forEach((t) => t.stop());
    ctx.close();
  }

  ws.onopen = () => {
    // "rules" tier: deterministic punctuation/casing, no LLM formatting pass —
    // lowest latency, and ArchetypeOS does its own intent reasoning downstream.
    ws.send(
      JSON.stringify({
        sample_rate: 16000,
        language: null,
        mode: 'ptt',
        format: 'rules',
        before_text: '',
        after_text: '',
        selected_text: '',
        app_hint: 'archetypeos-command-deck',
      }),
    );
    source.connect(processor);
    processor.connect(mute);
    mute.connect(ctx.destination);
  };

  ws.onmessage = (ev) => {
    let event: { event?: string; text?: string; detail?: string };
    try {
      event = JSON.parse(ev.data as string);
    } catch {
      return;
    }
    if (event.event === 'partial' && typeof event.text === 'string') {
      handlers.onPartial(event.text);
    } else if (event.event === 'final' && typeof event.text === 'string') {
      handlers.onFinal(event.text);
    } else if (event.event === 'error') {
      handlers.onError(event.detail ?? 'voice server error');
    }
  };

  ws.onerror = () => {
    if (!closed) handlers.onError('voice connection failed');
  };

  return {
    stop: () => {
      if (closed) return;
      closed = true;
      teardownAudio();
      if (ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ event: 'end' }));
    },
    cancel: () => {
      if (closed) return;
      closed = true;
      teardownAudio();
      if (ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ event: 'cancel' }));
      ws.close();
    },
  };
}
