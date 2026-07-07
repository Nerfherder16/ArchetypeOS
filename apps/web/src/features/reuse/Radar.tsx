/*
 * Radar — the WebGL reuse instrument for the Reuse view (AOS-UI-002).
 *
 * A react-three-fiber <Canvas> that plots the live transfer candidates: each
 * blip's distance from center encodes reuse strength (1 − confidence, via
 * radarLayout). Blip color is tiered by design token — cyan for semantic-strong
 * candidates (has matched_terms), periwinkle for lexical-lean ones. The active
 * blip is enlarged/brightened; the hovered blip pulses. Clicking a blip selects
 * it; pointer over/out reports hover. Camera is tilted for depth.
 *
 * Graceful degradation: a WebGL capability check runs before mount and an error
 * boundary wraps the Canvas, so a missing/failed WebGL context renders a slim
 * static placeholder and NEVER crashes the Reuse view. prefers-reduced-motion
 * freezes the sweep/pulse/core animation.
 *
 * Scope: Reuse view only (not a generic reusable <Radar> — that is AOS-UI-003).
 */
import React, { Component, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import type { TransferRecommendation } from '../../api';
import { MAX_RADIUS, RING_COUNT, candidateToPolar, polarToXZ } from './radarLayout';

// Blip tier colors, mirrored from design/tokens.css (dark palette):
//   --signal  #2fd3e8 (cyan)      → semantic-strong (has matched_terms)
//   --lex     #5b8df0 (periwinkle)→ lexical-lean
// Hardcoded here because three needs numeric/string colors, not CSS vars.
const COLOR_SIGNAL = '#2fd3e8';
const COLOR_LEX = '#5b8df0';
const COLOR_FRAME = '#29456f';

type Vec3 = [number, number, number];

export type RadarProps = {
  candidates: TransferRecommendation[];
  activeIndex: number | null;
  hoveredIndex: number | null;
  onSelect: (index: number) => void;
  onHover: (index: number | null) => void;
};

function prefersReducedMotion(): boolean {
  if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') {
    return false;
  }
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

// Capability check: create a throwaway canvas and probe for a WebGL context.
// Runs before we ever mount <Canvas>, so a headless/unsupported environment
// degrades instead of throwing.
function webglAvailable(): boolean {
  if (typeof document === 'undefined') {
    return false;
  }
  try {
    const canvas = document.createElement('canvas');
    const gl =
      canvas.getContext('webgl') ??
      canvas.getContext('experimental-webgl');
    return gl !== null;
  } catch {
    return false;
  }
}

// One concentric reference ring, laid flat on the XZ plane.
function Ring({ radius }: { radius: number }) {
  return (
    <mesh rotation={[-Math.PI / 2, 0, 0]}>
      <ringGeometry args={[radius - 0.018, radius + 0.018, 96]} />
      <meshBasicMaterial color={COLOR_FRAME} transparent opacity={0.55} side={THREE.DoubleSide} />
    </mesh>
  );
}

// Rotating sweep wedge. Frozen under reduced motion.
function Sweep({ reduced }: { reduced: boolean }) {
  const ref = useRef<THREE.Mesh>(null);
  useFrame((_, delta) => {
    if (reduced || !ref.current) {
      return;
    }
    ref.current.rotation.z -= delta * 0.6;
  });
  return (
    <mesh ref={ref} rotation={[-Math.PI / 2, 0, 0]}>
      {/* circleGeometry wedge: [radius, segments, thetaStart, thetaLength] */}
      <circleGeometry args={[MAX_RADIUS, 48, 0, Math.PI / 4]} />
      <meshBasicMaterial
        color={COLOR_SIGNAL}
        transparent
        opacity={0.14}
        side={THREE.DoubleSide}
        depthWrite={false}
      />
    </mesh>
  );
}

// Pulsing core at the center. Static scale under reduced motion.
function Core({ reduced }: { reduced: boolean }) {
  const ref = useRef<THREE.Mesh>(null);
  useFrame((state) => {
    if (!ref.current) {
      return;
    }
    const pulse = reduced ? 1 : 1 + Math.sin(state.clock.elapsedTime * 2.4) * 0.16;
    ref.current.scale.setScalar(pulse);
  });
  return (
    <mesh ref={ref}>
      <sphereGeometry args={[0.16, 24, 24]} />
      <meshBasicMaterial color={COLOR_SIGNAL} toneMapped={false} />
    </mesh>
  );
}

type BlipProps = {
  index: number;
  position: Vec3;
  color: string;
  active: boolean;
  hovered: boolean;
  reduced: boolean;
  onSelect: (index: number) => void;
  onHover: (index: number | null) => void;
};

function Blip({
  index,
  position,
  color,
  active,
  hovered,
  reduced,
  onSelect,
  onHover,
}: BlipProps) {
  const ref = useRef<THREE.Mesh>(null);
  useFrame((state) => {
    if (!ref.current) {
      return;
    }
    const base = active ? 1.9 : 1;
    const pulse =
      !reduced && hovered ? 1 + Math.sin(state.clock.elapsedTime * 6) * 0.22 : 1;
    ref.current.scale.setScalar(base * pulse);
  });

  const emissiveIntensity = active ? 1.9 : hovered ? 1.25 : 0.7;

  return (
    <mesh
      ref={ref}
      position={position}
      onClick={(event) => {
        event.stopPropagation();
        onSelect(index);
      }}
      onPointerOver={(event) => {
        event.stopPropagation();
        onHover(index);
      }}
      onPointerOut={(event) => {
        event.stopPropagation();
        onHover(null);
      }}
    >
      <octahedronGeometry args={[0.2, 0]} />
      <meshStandardMaterial
        color={color}
        emissive={color}
        emissiveIntensity={emissiveIntensity}
        metalness={0.2}
        roughness={0.35}
        toneMapped={false}
      />
    </mesh>
  );
}

function RadarScene({ candidates, activeIndex, hoveredIndex, onSelect, onHover }: RadarProps) {
  const reduced = useMemo(prefersReducedMotion, []);

  const rings = useMemo(() => {
    const out: number[] = [];
    for (let i = 1; i <= RING_COUNT; i += 1) {
      out.push((i / RING_COUNT) * MAX_RADIUS);
    }
    return out;
  }, []);

  const blips = useMemo(
    () =>
      candidates.map((candidate, index) => {
        const { radius, angle } = candidateToPolar({
          confidence: candidate.confidence,
          index,
          total: candidates.length,
        });
        const { x, z } = polarToXZ(radius, angle);
        const position: Vec3 = [x, 0.08, z];
        const color = candidate.matched_terms.length > 0 ? COLOR_SIGNAL : COLOR_LEX;
        return { index, position, color };
      }),
    [candidates],
  );

  return (
    <>
      <ambientLight intensity={0.75} />
      <pointLight position={[0, 6, 2]} intensity={1.4} />
      {rings.map((radius) => (
        <Ring key={radius} radius={radius} />
      ))}
      <Sweep reduced={reduced} />
      <Core reduced={reduced} />
      {blips.map((blip) => (
        <Blip
          key={blip.index}
          index={blip.index}
          position={blip.position}
          color={blip.color}
          active={activeIndex === blip.index}
          hovered={hoveredIndex === blip.index}
          reduced={reduced}
          onSelect={onSelect}
          onHover={onHover}
        />
      ))}
    </>
  );
}

// Error boundary: if <Canvas> creation or a render throws (e.g. WebGL context
// loss the capability probe missed), swallow it and degrade silently. The
// cards remain fully functional — the radar is an enhancement, not a dependency.
class RadarErrorBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  constructor(props: { children: ReactNode }) {
    super(props);
    this.state = { failed: false };
  }

  static getDerivedStateFromError(): { failed: boolean } {
    return { failed: true };
  }

  render(): ReactNode {
    if (this.state.failed) {
      return <RadarPlaceholder />;
    }
    return this.props.children;
  }
}

// Slim static placeholder shown when WebGL is unavailable or the Canvas fails.
function RadarPlaceholder() {
  return (
    <div
      className="aos-mono"
      style={{
        height: 60,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontSize: 11,
        color: 'var(--ink-3)',
        border: '1px dashed var(--frame)',
        background: 'color-mix(in srgb, var(--panel-2) 50%, transparent)',
      }}
    >
      reuse radar unavailable (WebGL) — candidates listed below
    </div>
  );
}

export function Radar({ candidates, activeIndex, hoveredIndex, onSelect, onHover }: RadarProps) {
  // Probe WebGL once, client-side, after mount so SSR/headless never throws.
  const [canRender, setCanRender] = useState(false);
  useEffect(() => {
    setCanRender(webglAvailable());
  }, []);

  return (
    <div
      className="aos-hud glass"
      data-testid="reuse-radar"
      style={{
        ['--cut' as string]: '13px',
        height: 300,
        marginBottom: 18,
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      <div
        className="aos-eyebrow"
        style={{ position: 'absolute', top: 10, left: 14, zIndex: 3, fontSize: 9, letterSpacing: '0.16em' }}
      >
        Portfolio reuse field
      </div>
      {canRender ? (
        <RadarErrorBoundary>
          <Canvas
            camera={{ position: [0, 6.5, 6.2], fov: 42, near: 0.1, far: 1000 }}
            style={{ width: '100%', height: '100%' }}
            gl={{ antialias: true, alpha: true }}
            onCreated={({ camera }) => {
              // Aim the tilted camera at the radar center explicitly, so the
              // depth view is stable and blip screen-projection is deterministic
              // (the e2e reproduces this exact camera to click a blip).
              camera.lookAt(0, 0, 0);
              camera.updateMatrixWorld(true);
            }}
          >
            <RadarScene
              candidates={candidates}
              activeIndex={activeIndex}
              hoveredIndex={hoveredIndex}
              onSelect={onSelect}
              onHover={onHover}
            />
          </Canvas>
        </RadarErrorBoundary>
      ) : (
        <RadarPlaceholder />
      )}
    </div>
  );
}
