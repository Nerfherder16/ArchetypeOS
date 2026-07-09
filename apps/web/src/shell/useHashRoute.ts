import { useCallback, useEffect, useState } from 'react';
import type { ViewId } from './Shell';

// AOS-WEB-SPINE-001 (slice 1) — URL routing for the active view. The Control Tower
// previously held the active view in bare component state, so views were not
// deep-linkable and browser back/forward did nothing. This hook backs the same
// state with the URL hash (`#/<view>`), so a view can be linked/bookmarked and
// the back button navigates between views. Behavior-preserving: with no (or an
// unknown) hash it resolves to the same default the app used before.

// The canonical set of routable views. Kept in sync with the `ViewId` union in
// Shell.tsx (a runtime guard so an unknown hash can never select a dead view).
export const VIEW_IDS: readonly ViewId[] = [
  'command',
  'overview',
  'repositories',
  'architecture',
  'council',
  'knowledge',
  'reuse',
  'digest',
  'scheduling',
  'providers',
  'approvals',
  'activity',
  'research',
  'voice-inbox',
  'nodes',
] as const;

const DEFAULT_VIEW: ViewId = 'overview';

function isViewId(value: string): value is ViewId {
  return (VIEW_IDS as readonly string[]).includes(value);
}

// Parse `#/nodes` (or legacy `#nodes`) → 'nodes'. Unknown/empty → the default.
export function viewFromHash(hash: string): ViewId {
  const raw = hash.replace(/^#\/?/, '').trim();
  return isViewId(raw) ? raw : DEFAULT_VIEW;
}

/**
 * Hash-backed active-view routing. Returns the current view and a setter that
 * updates the URL hash; browser back/forward and manual hash edits are honored.
 */
export function useHashRoute(): [ViewId, (view: ViewId) => void] {
  const [view, setView] = useState<ViewId>(() =>
    typeof window === 'undefined' ? DEFAULT_VIEW : viewFromHash(window.location.hash),
  );

  useEffect(() => {
    const onHashChange = () => setView(viewFromHash(window.location.hash));
    window.addEventListener('hashchange', onHashChange);
    return () => window.removeEventListener('hashchange', onHashChange);
  }, []);

  const navigate = useCallback((next: ViewId) => {
    // Update React state synchronously so in-app navigation is instant (the same
    // behavior as the previous bare `setActiveView`); then sync the URL hash. The
    // hashchange listener still drives EXTERNAL changes (back/forward, manual hash
    // edits). Setting the hash re-fires `setView(next)` — idempotent, no re-render.
    setView(next);
    const target = `#/${next}`;
    if (window.location.hash !== target) {
      window.location.hash = target;
    }
  }, []);

  return [view, navigate];
}
