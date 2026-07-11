#!/usr/bin/env node
// AOS-WEB-LOCK-001 — dependency-lock consistency check.
//
// Guards the reproducible-build invariant so the npm/cli#4828 regression (a
// lockfile missing Rollup's platform-specific native binary → "Cannot find module
// @rollup/rollup-linux-x64-musl" at `vite build`) cannot silently return. Runs in
// CI before `npm ci` (pure node, no install needed). Exits non-zero on any breach.

import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const webDir = join(dirname(fileURLToPath(import.meta.url)), "..");
const pkg = JSON.parse(readFileSync(join(webDir, "package.json"), "utf8"));
const lock = JSON.parse(readFileSync(join(webDir, "package-lock.json"), "utf8"));

const errors = [];

// 1. Modern lockfile format (npm v7+ / lockfileVersion 3 is what `npm ci` expects).
if (!(lock.lockfileVersion >= 3)) {
  errors.push(`lockfileVersion must be >= 3, got ${lock.lockfileVersion}`);
}

// 2. The lockfile must describe THIS package (name/version in sync).
if (lock.name !== pkg.name) {
  errors.push(`lockfile name ${lock.name} != package.json name ${pkg.name}`);
}
if (lock.version !== pkg.version) {
  errors.push(`lockfile version ${lock.version} != package.json version ${pkg.version}`);
}

// 3. The Rollup platform native that BOTH build environments use must be present
//    as a locked package: the glibc binary for the node:22-slim Docker build stage
//    AND the CI ubuntu runner (both glibc). Its absence is the npm/cli#4828
//    regression that made a musl `npm ci` fail — building on glibc keeps the lock's
//    host-recorded gnu binary correct. (npm records only the host platform's
//    native, so we do NOT require musl — the build stage is deliberately glibc.)
const REQUIRED_ROLLUP_NATIVES = [
  "@rollup/rollup-linux-x64-gnu",
];
const packages = lock.packages || {};
for (const name of REQUIRED_ROLLUP_NATIVES) {
  const present = Object.keys(packages).some((k) => k.endsWith(`node_modules/${name}`));
  if (!present) {
    errors.push(`lockfile is missing required Rollup native ${name} (npm/cli#4828 regression)`);
  }
}

if (errors.length) {
  console.error("check-lockfile: FAIL");
  for (const e of errors) console.error("  - " + e);
  console.error("\nRegenerate with `npm install` (Node 22 / npm 10+) and commit apps/web/package-lock.json.");
  process.exit(1);
}

console.log("check-lockfile: OK (lockfileVersion %d, %d locked packages, Rollup natives present)",
  lock.lockfileVersion, Object.keys(packages).length);
