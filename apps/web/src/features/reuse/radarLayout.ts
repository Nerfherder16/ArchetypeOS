/*
 * radarLayout — PURE, deterministic polar mapping for the Reuse radar (AOS-UI-002).
 *
 * No React, no three. Maps a reuse candidate to a blip position so the operator
 * reads portfolio reuse at a glance: distance from center encodes reuse strength
 * (`1 − confidence`) — a high-confidence candidate sits near the core, a weak one
 * drifts to the outer ring. Angle is a stable, even spread by index, so the same
 * candidate list always produces the same layout (deterministic screenshots/tests).
 */

// World-space radius of the outermost ring (three units). Blips never exceed it.
export const MAX_RADIUS = 4.2;

// Number of concentric reference rings the instrument draws.
export const RING_COUNT = 4;

// Reuse-strength band, as a fraction of MAX_RADIUS. The strongest candidate
// (confidence 1) sits at MIN_RADIUS_FACTOR (not dead-center, so it clears the
// pulsing core); the weakest (confidence 0) sits at MAX_RADIUS_FACTOR.
export const MIN_RADIUS_FACTOR = 0.35;
export const MAX_RADIUS_FACTOR = 1.0;

// Constant angular offset so the first blip does not sit exactly on the sweep
// origin. Deterministic — purely aesthetic, identical for every render.
export const ANGLE_OFFSET = Math.PI / 6;

export type PolarInput = {
  confidence: number;
  index: number;
  total: number;
};

export type Polar = {
  radius: number;
  angle: number;
};

const clamp01 = (value: number): number => {
  if (!Number.isFinite(value)) {
    return 0;
  }
  return Math.max(0, Math.min(1, value));
};

/**
 * Map a candidate to polar coordinates on the radar plane.
 *
 * - `radius` grows monotonically with `1 − confidence` (clamped to the
 *   MIN..MAX radius band). Higher confidence ⇒ smaller radius (nearer center).
 * - `angle` is an even spread by index over a full turn, plus a constant
 *   offset. Deterministic in all inputs.
 */
export function candidateToPolar({ confidence, index, total }: PolarInput): Polar {
  const strength = 1 - clamp01(confidence);
  const factor = MIN_RADIUS_FACTOR + strength * (MAX_RADIUS_FACTOR - MIN_RADIUS_FACTOR);
  const radius = factor * MAX_RADIUS;

  // Guard against total <= 0 so a lone/edge input still yields a finite angle.
  const slots = Math.max(1, Math.floor(total));
  const safeIndex = Number.isFinite(index) ? index : 0;
  const angle = ANGLE_OFFSET + (safeIndex / slots) * Math.PI * 2;

  return { radius, angle };
}

/** Project polar coordinates onto the radar's XZ plane (y is up in three). */
export function polarToXZ(radius: number, angle: number): { x: number; z: number } {
  return {
    x: radius * Math.cos(angle),
    z: radius * Math.sin(angle),
  };
}
