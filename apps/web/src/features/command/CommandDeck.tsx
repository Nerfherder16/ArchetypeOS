/*
 * CommandDeck — the Operations-mode home (AOS-UI-009).
 *
 * A Canvas 2D constellation: an Orchestrator core dot-sphere (cyan) orbited by
 * the six Council agent orbs, with a floor reflection, two-axis rotation,
 * free-floating orbits, faint tethers, ambient hand-off packets and a
 * voice-reactive expand/contract + "SPEAKING · <AGENT>" banner. Below it a
 * command console routes a typed/spoken task to the best-matching agent.
 *
 * Ported faithfully from the approved deck mock (deck_v3). React adaptations:
 *   - rAF loop + ResizeObserver + intervals start in a useEffect and are ALL
 *     torn down on cleanup (no leaks, no setState-after-unmount).
 *   - DPR-aware sizing (cap 2) with an offscreen buffer for the reflection.
 *   - prefers-reduced-motion → one static frame, no loop, no ambient/auto-speak.
 *   - The speaking envelope is driven directly on submit (NOT gated on TTS audio
 *     firing) so routing always animates; TTS onboundary word-pulses layer on
 *     top only when speechSynthesis is available. Voice (STT/TTS) degrades
 *     gracefully and never throws when the Web Speech APIs are absent.
 */
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { fetchSpeech, postVoiceTurn } from '../../api';
import { AGENTS, CORE_RGB, SHELL_RGB, fib, hexToRgb, routeForTask, type Point3 } from './orb';
import { sottoConfigured, startDictation, type DictationController } from './sottoDictation';

function prefersReducedMotion(): boolean {
  return (
    typeof window !== 'undefined' &&
    typeof window.matchMedia === 'function' &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches
  );
}

type Rgb = [number, number, number];

type Sat = {
  i: number;
  rgb: Rgb;
  rad: number;
  tilt: number;
  ph: number;
  vy: number;
  sz: number;
  label: string;
};

type Packet = { idx: number; t: number; col: Rgb };

type EngineHandle = {
  submit: (text: string) => void;
  toggleMic: () => void;
};

const QUICK_ACTIONS: { label: string; task: string }[] = [
  { label: '◇ Research', task: 'research the best vector database for our retrieval' },
  { label: '◇ Map arch', task: 'map the architecture of the pydantic-ai repo' },
  { label: '◇ Run gate', task: 'run the guardian gate on pr 92' },
  { label: '◇ Scout', task: 'scout github for mcp servers we could reuse' },
  { label: '◇ Security', task: 'threat model the exposed api surface' },
];

type CommandDeckProps = {
  projectId?: string | null;
  projectName?: string | null;
};

export function CommandDeck({ projectId = null, projectName = null }: CommandDeckProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const stageRef = useRef<HTMLDivElement>(null);
  const engineRef = useRef<EngineHandle | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  // submit() is created once in the mount effect below, so it reads the CURRENT
  // project through this ref rather than a stale closure over the first render
  // (AOS-VOICE-PROJECT-001).
  const projectRef = useRef<{ id: string | null; name: string | null }>({ id: projectId, name: projectName });
  useEffect(() => {
    projectRef.current = { id: projectId, name: projectName };
  }, [projectId, projectName]);

  const [routing, setRouting] = useState('STANDBY');
  const [speakingOn, setSpeakingOn] = useState(false);
  const [speakingName, setSpeakingName] = useState('ORCHESTRATOR');
  const [reply, setReply] = useState('orchestrator standing by');
  const [listening, setListening] = useState(false);
  const [voiceNote, setVoiceNote] = useState<string | null>(null);
  const [inputValue, setInputValue] = useState('');

  useEffect(() => {
    const canvas = canvasRef.current;
    const stage = stageRef.current;
    if (!canvas || !stage) {
      return undefined;
    }
    const ctx = canvas.getContext('2d');
    if (!ctx) {
      return undefined;
    }
    const reduced = prefersReducedMotion();

    // Offscreen buffer: the whole scene renders here, then it is drawn twice onto
    // the visible canvas (once mirrored below the floor line, once upright).
    const oc = document.createElement('canvas');
    const octx = oc.getContext('2d');
    if (!octx) {
      return undefined;
    }

    let W = 0;
    let H = 0;
    let raf = 0;
    let ambientTimer: ReturnType<typeof setInterval> | undefined;

    // Precompute the three dot-spheres and the satellite RGB table once.
    const CORE: Point3[] = fib(1300);
    const SHELL: Point3[] = fib(420);
    const SAT: Point3[] = fib(340);
    const SATS: Sat[] = AGENTS.map((a, i) => ({
      i,
      rgb: hexToRgb(a.color),
      rad: a.rad,
      tilt: a.tilt,
      ph: a.ph,
      vy: a.vy,
      sz: a.sz,
      label: a.label,
    }));

    // Mutable engine state (lives for this effect only).
    let tNow = 0;
    let mx = 0;
    let my = 0;
    let tmx = 0;
    let tmy = 0;
    let amp = 0;
    let ampTarget = 0;
    let wordPulse = 0;
    let speaking = false;
    let speakEnd = 0;
    let curSpeaker = -1; // -1 => core/orchestrator; else satellite index
    let selectedIdx = 0;
    let packets: Packet[] = [];

    const synth: SpeechSynthesis | undefined =
      typeof window !== 'undefined' ? window.speechSynthesis : undefined;
    const synthActive = (): boolean => {
      try {
        return !!synth && synth.speaking;
      } catch {
        return false;
      }
    };

    const resize = () => {
      const rect = canvas.getBoundingClientRect();
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      W = rect.width;
      H = rect.height;
      canvas.width = Math.max(1, Math.round(rect.width * dpr));
      canvas.height = Math.max(1, Math.round(rect.height * dpr));
      oc.width = canvas.width;
      oc.height = canvas.height;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      octx.setTransform(dpr, 0, 0, dpr, 0, 0);
      if (reduced) {
        present(speaking ? 0.5 : 0);
      }
    };

    const rot = (p: Point3, ay: number, ax: number): Point3 => {
      const [x, y, z] = p;
      const x1 = x * Math.cos(ay) + z * Math.sin(ay);
      const z1 = -x * Math.sin(ay) + z * Math.cos(ay);
      const y2 = y * Math.cos(ax) - z1 * Math.sin(ax);
      const z2 = y * Math.sin(ax) + z1 * Math.cos(ax);
      return [x1, y2, z2];
    };

    // Additive-glow dot-sphere into a 2D context.
    const sphere = (
      g: CanvasRenderingContext2D,
      cx: number,
      cy: number,
      R: number,
      pts: Point3[],
      ay: number,
      ax: number,
      rgb: Rgb,
      glow: number,
      a: number,
    ) => {
      const jit = a * 0.16;
      const proj: [number, number, number][] = [];
      for (let i = 0; i < pts.length; i += 1) {
        const [x, y, z] = rot(pts[i], ay, ax);
        const rr = 1 + Math.sin(i * 12.9898 + tNow * 0.12) * jit;
        proj.push([cx + x * R * rr, cy + y * R * rr, z]);
      }
      proj.sort((p, q) => p[2] - q[2]);
      const hg = g.createRadialGradient(cx, cy, 0, cx, cy, R * 1.85);
      hg.addColorStop(0, `rgba(${rgb[0]},${rgb[1]},${rgb[2]},${(0.13 + a * 0.14) * glow})`);
      hg.addColorStop(0.55, `rgba(${rgb[0]},${rgb[1]},${rgb[2]},${0.04 * glow})`);
      hg.addColorStop(1, 'rgba(0,0,0,0)');
      g.fillStyle = hg;
      g.beginPath();
      g.arc(cx, cy, R * 1.85, 0, 7);
      g.fill();
      g.globalCompositeOperation = 'lighter';
      for (let i = 0; i < proj.length; i += 1) {
        const z = proj[i][2];
        const d = (z + 1) / 2;
        const rim = 1 - Math.abs(z);
        const al = (0.05 + d * d * 0.72 + rim * 0.1) * glow;
        const s = (0.45 + d * 1.7) * (1 + a * 0.5);
        const br = Math.min(255, rgb[0] + (255 - rgb[0]) * (d * 0.5 + rim * 0.35));
        const bgc = Math.min(255, rgb[1] + (255 - rgb[1]) * (d * 0.5 + rim * 0.35));
        const bb = Math.min(255, rgb[2] + (255 - rgb[2]) * d * 0.35);
        g.beginPath();
        g.arc(proj[i][0], proj[i][1], s, 0, 7);
        g.fillStyle = `rgba(${br | 0},${bgc | 0},${bb | 0},${al})`;
        g.fill();
      }
      const cg = g.createRadialGradient(cx, cy, 0, cx, cy, R * 0.7);
      cg.addColorStop(0, `rgba(255,255,255,${(0.4 + a * 0.4) * glow})`);
      cg.addColorStop(0.38, `rgba(${rgb[0]},${rgb[1]},${rgb[2]},${(0.24 + a * 0.2) * glow})`);
      cg.addColorStop(1, 'rgba(0,0,0,0)');
      g.fillStyle = cg;
      g.beginPath();
      g.arc(cx, cy, R * 0.7, 0, 7);
      g.fill();
      g.globalCompositeOperation = 'source-over';
    };

    const bez = (p0: [number, number], p1: [number, number], p2: [number, number], t: number): [number, number] => {
      const u = 1 - t;
      return [
        u * u * p0[0] + 2 * u * t * p1[0] + t * t * p2[0],
        u * u * p0[1] + 2 * u * t * p1[1] + t * t * p2[1],
      ];
    };

    const beginSpeak = (idx: number, txtLen: number) => {
      speaking = true;
      curSpeaker = idx;
      setSpeakingName(idx < 0 ? 'ORCHESTRATOR' : SATS[idx].label);
      setSpeakingOn(true);
      speakEnd = tNow + Math.min(4200, 900 + txtLen * 55);
    };
    const endSpeak = () => {
      speaking = false;
      curSpeaker = -1;
      setSpeakingOn(false);
    };

    const fireHandoff = (idx: number) => {
      packets.push({ idx, t: 0, col: SATS[idx].rgb });
      setRouting(SATS[idx].label);
    };

    const renderScene = (
      cx: number,
      cy: number,
      R: number,
      orbitR: number,
      coreA: number,
      breathe: number,
    ) => {
      octx.clearRect(0, 0, W, H);
      const placed = SATS.map((s) => {
        const ang = s.ph + tNow * 0.0013;
        const ex = Math.cos(ang) * orbitR * s.rad;
        const ey = Math.sin(ang) * orbitR * s.rad * s.tilt + s.vy * orbitR;
        const depth = (Math.sin(ang) + 1) / 2;
        return {
          ...s,
          x: cx + ex + mx * (50 + s.i * 5),
          y: cy + ey + my * (34 + s.i * 4),
          depth,
        };
      });
      // Tethers.
      placed.forEach((s) => {
        const pulse =
          0.045 +
          Math.abs(Math.sin(tNow * 0.03 + s.i)) * 0.075 +
          (s.i === curSpeaker ? amp * 0.25 : 0);
        const gr = octx.createLinearGradient(cx, cy, s.x, s.y);
        gr.addColorStop(0, `rgba(${s.rgb[0]},${s.rgb[1]},${s.rgb[2]},${pulse})`);
        gr.addColorStop(1, `rgba(${s.rgb[0]},${s.rgb[1]},${s.rgb[2]},0)`);
        octx.strokeStyle = gr;
        octx.lineWidth = 1;
        octx.beginPath();
        octx.moveTo(cx, cy);
        octx.quadraticCurveTo((cx + s.x) / 2, (cy + s.y) / 2 - 20, s.x, s.y);
        octx.stroke();
      });
      const ord = [...placed].sort((a, b) => a.depth - b.depth);
      const drawSat = (s: (typeof placed)[number]) => {
        const sel = s.i === selectedIdx;
        const spk = s.i === curSpeaker;
        const sA = spk ? amp : 0;
        sphere(
          octx,
          s.x,
          s.y,
          R * s.sz * breathe * (1 + sA * 0.34),
          SAT,
          tNow * 0.01 + s.i,
          0.5,
          s.rgb,
          0.5 + s.depth * 0.5 + (sel ? 0.28 : 0) + (spk ? 0.35 : 0),
          sA,
        );
        if (s.depth >= 0.5) {
          octx.font = '600 8.5px "JetBrains Mono", monospace';
          octx.fillStyle = `rgba(${s.rgb[0]},${s.rgb[1]},${s.rgb[2]},.85)`;
          octx.textAlign = 'center';
          octx.fillText(s.label, s.x, s.y + R * s.sz * breathe + 14);
        }
      };
      ord.filter((s) => s.depth < 0.5).forEach(drawSat);
      sphere(
        octx,
        cx,
        cy,
        R * 1.16 * breathe * (1 + coreA * 0.2),
        SHELL,
        -tNow * 0.004,
        0.58,
        [SHELL_RGB[0], SHELL_RGB[1], SHELL_RGB[2]],
        0.2,
        coreA * 0.5,
      );
      sphere(
        octx,
        cx,
        cy,
        R * breathe * (1 + coreA * 0.34),
        CORE,
        tNow * 0.006,
        0.4 + Math.sin(tNow * 0.004) * 0.1,
        [CORE_RGB[0], CORE_RGB[1], CORE_RGB[2]],
        1,
        coreA,
      );
      ord.filter((s) => s.depth >= 0.5).forEach(drawSat);
      // Hand-off packets.
      packets = packets.filter((p) => p.t < 1);
      packets.forEach((pk) => {
        pk.t += 0.017;
        const s = placed[pk.idx];
        const mid: [number, number] = [(cx + s.x) / 2, (cy + s.y) / 2 - 36];
        const [px, py] = bez([cx, cy], mid, [s.x, s.y], pk.t);
        octx.globalCompositeOperation = 'lighter';
        for (let k = 0; k < 8; k += 1) {
          const tt = Math.max(0, pk.t - k * 0.028);
          const [tx, ty] = bez([cx, cy], mid, [s.x, s.y], tt);
          octx.beginPath();
          octx.arc(tx, ty, 3.6 - k * 0.38, 0, 7);
          octx.fillStyle = `rgba(${pk.col[0]},${pk.col[1]},${pk.col[2]},${(1 - k / 8) * 0.5 * (1 - pk.t) + 0.12})`;
          octx.fill();
        }
        octx.beginPath();
        octx.arc(px, py, 4.4, 0, 7);
        octx.fillStyle = '#fff';
        octx.shadowBlur = 15;
        octx.shadowColor = `rgb(${s.rgb[0]},${s.rgb[1]},${s.rgb[2]})`;
        octx.fill();
        octx.shadowBlur = 0;
        octx.globalCompositeOperation = 'source-over';
        if (pk.t > 0.95) {
          const fg = octx.createRadialGradient(s.x, s.y, 0, s.x, s.y, R);
          fg.addColorStop(0, `rgba(${pk.col[0]},${pk.col[1]},${pk.col[2]},.42)`);
          fg.addColorStop(1, 'rgba(0,0,0,0)');
          octx.fillStyle = fg;
          octx.beginPath();
          octx.arc(s.x, s.y, R, 0, 7);
          octx.fill();
        }
      });
    };

    // Composite the offscreen scene onto the visible canvas: mirrored reflection
    // faded into the ground, floor glow line, then the upright scene.
    const present = (ampNow: number) => {
      const cx = W / 2 + mx * 30;
      const cy = H * 0.44 + my * 20;
      const R = Math.min(W, H) * 0.16;
      const orbitR = Math.min(W * 0.34, H * 0.62);
      const coreA = curSpeaker < 0 ? ampNow : ampNow * 0.45;
      const breathe = 1 + Math.sin(tNow * 0.02) * 0.025;
      renderScene(cx, cy, R, orbitR, coreA, breathe);

      ctx.clearRect(0, 0, W, H);
      const floorY = H * 0.82;
      ctx.save();
      ctx.globalAlpha = 0.2;
      ctx.translate(0, floorY * 2);
      ctx.scale(1, -1);
      ctx.drawImage(oc, 0, 0, W, H);
      ctx.restore();
      const rg = ctx.createLinearGradient(0, floorY, 0, H);
      rg.addColorStop(0, 'rgba(4,2,3,0)');
      rg.addColorStop(1, 'rgba(4,2,3,1)');
      ctx.fillStyle = rg;
      ctx.fillRect(0, floorY, W, H - floorY);
      ctx.strokeStyle = 'rgba(255,60,90,.12)';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(W * 0.2, floorY);
      ctx.lineTo(W * 0.8, floorY);
      ctx.stroke();
      ctx.drawImage(oc, 0, 0, W, H);
    };

    const step = (ts: number) => {
      tNow = ts * 0.001 * 60 || tNow + 1;
      mx += (tmx - mx) * 0.06;
      my += (tmy - my) * 0.06;
      if (speaking) {
        const carrier =
          0.42 +
          0.3 * Math.sin(tNow * 0.34) +
          0.16 * Math.sin(tNow * 0.57 + 1) +
          0.1 * Math.sin(tNow * 1.1 + 2);
        ampTarget = Math.max(0.28, carrier) * 0.7 + wordPulse * 0.55;
        if (tNow > speakEnd && !synthActive()) {
          endSpeak();
        }
      } else {
        ampTarget = 0;
      }
      wordPulse *= 0.86;
      amp += (ampTarget - amp) * 0.22;
      present(amp);
    };

    const loop = (ts: number) => {
      step(ts);
      raf = requestAnimationFrame(loop);
    };

    // --- Voice (graceful, non-throwing) ---
    const browserSpeak = (txt: string) => {
      try {
        if (!synth || typeof window.SpeechSynthesisUtterance !== 'function') {
          return;
        }
        const u = new SpeechSynthesisUtterance(txt);
        u.rate = 1.03;
        u.pitch = 0.96;
        const voices = synth.getVoices();
        const v = voices.find((voice) => /en/i.test(voice.lang));
        if (v) {
          u.voice = v;
        }
        u.onboundary = () => {
          wordPulse = 1;
        };
        u.onend = () => endSpeak();
        synth.cancel();
        synth.speak(u);
      } catch {
        // TTS blocked — the amplitude envelope already runs from beginSpeak.
      }
    };

    // Server-side TTS first (Groq Orpheus, AOS-VOICE-004) for a natural voice;
    // fall back to the browser's speechSynthesis when TTS is unconfigured (204)
    // or audio playback fails. The amplitude envelope already runs from beginSpeak,
    // so a TTS miss never leaves the orb silent-looking.
    let ttsAudio: HTMLAudioElement | null = null;
    const speak = (txt: string, _idx: number) => {
      fetchSpeech(txt)
        .then((blob) => {
          if (!blob) {
            browserSpeak(txt);
            return;
          }
          try {
            const url = URL.createObjectURL(blob);
            ttsAudio = new Audio(url);
            ttsAudio.onended = () => {
              endSpeak();
              URL.revokeObjectURL(url);
              ttsAudio = null;
            };
            void ttsAudio.play().catch(() => {
              URL.revokeObjectURL(url);
              ttsAudio = null;
              browserSpeak(txt);
            });
          } catch {
            browserSpeak(txt);
          }
        })
        .catch(() => browserSpeak(txt));
    };

    const submit = (raw: string) => {
      const q = raw.trim();
      if (!q) {
        return;
      }
      const idx = routeForTask(q);
      selectedIdx = idx;
      // Orb visuals fire synchronously (routeForTask picks the agent) so routing
      // always animates regardless of the backend round-trip.
      fireHandoff(idx);
      setReply('routing…');
      beginSpeak(idx, 28);
      if (reduced) {
        // No loop is running; paint one frame that reflects the routed state.
        amp = 0.5;
        present(amp);
      }
      // Route the turn through the Voice Command Center backend (AOS-VOICE-001):
      // typed or Sotto-spoken both land here → intent + review-first inbox draft
      // + spoken reply. Failure is silent (the orb already animated), so the
      // console stays clean and the deck degrades to a local acknowledgement.
      postVoiceTurn(q, 'command-deck', projectRef.current.id ?? undefined)
        .then((item) => {
          const text = item.reply_text || `${AGENTS[idx].label} acknowledged.`;
          setReply(`${AGENTS[idx].label} ▸ ${text}`);
          speak(text, idx);
        })
        .catch(() => {
          setReply(`${AGENTS[idx].label} ▸ captured for review`);
          speak('captured for review', idx);
        });
    };

    // --- Speech to text via Sotto (AOS-VOICE-002) ---
    // Push-to-talk: first tap opens the Sotto stream (16 kHz PCM16 over WS), a
    // second tap finalizes → onFinal delivers the transcript, which is submitted
    // through the same backend path as a typed command. Degrades to type-only
    // when Sotto is not configured or the mic is denied.
    let dictation: DictationController | null = null;
    const toggleMic = () => {
      if (dictation) {
        dictation.stop();
        dictation = null;
        return;
      }
      if (!sottoConfigured()) {
        setVoiceNote('voice unavailable — type instead');
        return;
      }
      setVoiceNote('listening…');
      setListening(true);
      startDictation({
        onPartial: (text) => setInputValue(text),
        onFinal: (text) => {
          dictation = null;
          setListening(false);
          setVoiceNote(null);
          setInputValue('');
          submit(text);
        },
        onError: (msg) => {
          dictation = null;
          setListening(false);
          setVoiceNote(msg);
        },
      })
        .then((ctrl) => {
          dictation = ctrl;
        })
        .catch(() => {
          // onError already surfaced the reason (not configured / mic denied).
          dictation = null;
          setListening(false);
        });
    };

    engineRef.current = { submit, toggleMic };

    const onMouseMove = (e: MouseEvent) => {
      const rect = canvas.getBoundingClientRect();
      tmx = (e.clientX - rect.left) / rect.width - 0.5;
      tmy = (e.clientY - rect.top) / rect.height - 0.5;
    };

    const ro = new ResizeObserver(resize);
    ro.observe(canvas);
    resize();

    if (reduced) {
      // Static deck: a single frame, no loop, no ambient life, no auto-speak.
      present(0);
    } else {
      window.addEventListener('mousemove', onMouseMove);
      raf = requestAnimationFrame(loop);
      // Ambient hand-offs: the deck breathes when idle (visible speak, no audio).
      ambientTimer = setInterval(() => {
        if (speaking) {
          return;
        }
        const idx = Math.floor(Math.random() * SATS.length);
        fireHandoff(idx);
        beginSpeak(idx, 20);
      }, 3200);
    }

    return () => {
      if (raf) {
        cancelAnimationFrame(raf);
      }
      if (ambientTimer) {
        clearInterval(ambientTimer);
      }
      ro.disconnect();
      window.removeEventListener('mousemove', onMouseMove);
      try {
        dictation?.cancel();
      } catch {
        /* ignore */
      }
      try {
        ttsAudio?.pause();
      } catch {
        /* ignore */
      }
      try {
        synth?.cancel();
      } catch {
        /* ignore */
      }
      engineRef.current = null;
    };
  }, []);

  const handleSubmit = useCallback(() => {
    engineRef.current?.submit(inputValue);
    setInputValue('');
  }, [inputValue]);

  const handleQuick = useCallback((task: string) => {
    setInputValue('');
    engineRef.current?.submit(task);
  }, []);

  return (
    <div className="aos-view cmd-deck" data-testid="command-deck">
      <style>{`
        .cmd-deck{display:flex;flex-direction:column;gap:14px;height:100%}
        .cmd-stage{position:relative;flex:1;min-height:320px;overflow:hidden;border-radius:14px;
          background:radial-gradient(1200px 700px at 50% 120%,color-mix(in srgb,var(--signal) 8%,transparent),transparent 60%),var(--panel);
          border:1px solid var(--frame)}
        .cmd-stage canvas{position:absolute;inset:0;width:100%;height:100%;display:block}
        .cmd-slab{position:absolute;z-index:2;pointer-events:none}
        .cmd-slab.lt{left:16px;top:14px}
        .cmd-slab.rt{right:16px;top:14px;text-align:right}
        .cmd-routing{font-size:30px;line-height:.9;letter-spacing:.02em;color:var(--signal-bright);
          text-shadow:0 0 22px color-mix(in srgb,var(--signal) 40%,transparent)}
        .cmd-speaking{position:absolute;left:50%;top:14px;transform:translateX(-50%);z-index:3;
          display:flex;align-items:center;gap:8px;padding:6px 14px;border-radius:20px;
          font-family:var(--mono,ui-monospace,monospace);font-size:9px;letter-spacing:.22em;text-transform:uppercase;
          color:var(--signal-bright);background:color-mix(in srgb,var(--signal) 12%,var(--panel-2));
          box-shadow:inset 0 0 0 1px color-mix(in srgb,var(--signal) 30%,var(--frame)),0 0 22px -8px var(--signal)}
        .cmd-speaking i{width:7px;height:7px;border-radius:50%;background:var(--signal);
          box-shadow:0 0 10px var(--signal);animation:cmdBlip 1s infinite}
        @keyframes cmdBlip{0%,100%{opacity:1}50%{opacity:.3}}
        @media(prefers-reduced-motion:reduce){.cmd-speaking i{animation:none}}
        .cmd-console{display:flex;flex-direction:column;gap:10px}
        .cmd-chips{display:flex;gap:8px;flex-wrap:wrap}
        .cmd-chip{font-family:var(--mono,monospace);font-size:11px;letter-spacing:.04em;
          padding:5px 10px;border-radius:8px;cursor:pointer;color:var(--ink-2);
          background:var(--panel-2);border:1px solid var(--frame)}
        .cmd-chip:hover{color:var(--signal-bright);border-color:var(--signal)}
        .cmd-row{display:flex;align-items:center;gap:10px;padding:9px 13px;border-radius:11px;
          background:var(--panel);border:1px solid var(--frame)}
        .cmd-row:focus-within{border-color:var(--signal);
          box-shadow:0 0 24px -12px var(--signal)}
        .cmd-prompt{font-size:20px;color:var(--signal);flex:none}
        .cmd-input{flex:1;background:transparent;border:0;outline:0;color:var(--ink);
          font-family:var(--mono,monospace);font-size:13px}
        .cmd-mic,.cmd-send{border:0;cursor:pointer;border-radius:9px;height:34px}
        .cmd-mic{width:34px;display:grid;place-items:center;color:var(--signal);
          background:var(--panel-2);border:1px solid var(--frame)}
        .cmd-mic.on{color:var(--panel);background:var(--red)}
        .cmd-send{padding:0 16px;color:var(--panel);font-weight:600;letter-spacing:.04em;
          background:linear-gradient(180deg,var(--signal-bright),var(--signal-deep))}
        .cmd-reply{font-family:var(--mono,monospace);font-size:11px;color:var(--signal-bright);
          opacity:.9;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:340px}
        .cmd-note{font-family:var(--mono,monospace);font-size:10px;color:var(--ink-3)}
        .cmd-scope{font-size:11px;letter-spacing:.03em;color:var(--ink-2);opacity:.9}
      `}</style>

      <div className="cmd-stage" ref={stageRef}>
        <div className="cmd-slab lt">
          <span className="aos-eyebrow">Constellation</span>
        </div>
        <div className="cmd-slab rt">
          <span className="aos-eyebrow">Now routing</span>
          <div className="cmd-routing aos-display" data-testid="command-routing">
            {routing}
          </div>
        </div>
        {speakingOn ? (
          <div className="cmd-speaking" data-testid="command-speaking">
            <i aria-hidden="true" />
            <span>SPEAKING · {speakingName}</span>
          </div>
        ) : null}
        <canvas ref={canvasRef} aria-label="Council constellation" />
      </div>

      <div className="cmd-console">
        <div className="cmd-scope aos-mono" data-testid="command-scope">
          {projectName ? (
            <>
              <span aria-hidden="true" style={{ color: 'var(--signal)' }}>&#9679;</span> capture scoped to{' '}
              <span className="aos-strong">{projectName}</span>
            </>
          ) : (
            <>
              <span aria-hidden="true" style={{ color: 'var(--ink-3)' }}>&#9675;</span> global capture (no project selected)
            </>
          )}
        </div>
        <div className="cmd-chips" role="group" aria-label="Quick actions">
          {QUICK_ACTIONS.map((qa) => (
            <button
              key={qa.label}
              type="button"
              className="cmd-chip"
              data-testid={`command-quick-${qa.task.split(' ')[0]}`}
              onClick={() => handleQuick(qa.task)}
            >
              {qa.label}
            </button>
          ))}
        </div>
        <div className="cmd-row">
          <span className="cmd-prompt" aria-hidden="true">
            ›
          </span>
          <input
            ref={inputRef}
            className="cmd-input"
            data-testid="command-input"
            type="text"
            autoComplete="off"
            placeholder="Speak to the Orchestrator — type a task or hit the mic…"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                handleSubmit();
              }
            }}
          />
          <span className="cmd-reply" aria-live="polite">
            ◦ {voiceNote ?? reply}
          </span>
          <button
            type="button"
            className={listening ? 'cmd-mic on' : 'cmd-mic'}
            data-testid="command-mic"
            aria-label="Toggle voice input"
            aria-pressed={listening}
            onClick={() => engineRef.current?.toggleMic()}
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="9" y="3" width="6" height="11" rx="3" />
              <path d="M6 11a6 6 0 0 0 12 0M12 17v4" />
            </svg>
          </button>
          <button type="button" className="cmd-send" data-testid="command-send" onClick={handleSubmit}>
            SEND
          </button>
        </div>
      </div>
    </div>
  );
}
