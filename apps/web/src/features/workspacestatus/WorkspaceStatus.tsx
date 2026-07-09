import { useEffect, useState } from 'react';
import { fetchPendingAuthorityActions } from '../../api';
import type { WorkspaceMode } from '../../shell/workspaces';

// AOS-UX-IA-001 (deliverable 4) — per-workspace Now / Next / Blocked. A compact
// rail summary scoped to the current workspace mode:
//   Now     — the surface you are looking at in this workspace.
//   Next    — the mode's first planned ("soon") surface (what's coming here).
//   Blocked — actions awaiting your approval (an operator-wide blocker); only
//             shown when there is at least one, so it stays quiet when clear.
export function WorkspaceStatus({
  mode,
  activeSurfaceLabel,
}: {
  mode: WorkspaceMode;
  activeSurfaceLabel: string;
}) {
  const [blocked, setBlocked] = useState<number | null>(null);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const pending = await fetchPendingAuthorityActions();
        if (!cancelled) {
          setBlocked(pending.length);
        }
      } catch {
        if (!cancelled) {
          setBlocked(null);
        }
      }
    };
    void load();
    const id = window.setInterval(() => void load(), 30000);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, []);

  const nowLabel = activeSurfaceLabel || '—';
  const nextPlanned = mode.surfaces.find((surface) => surface.status === 'soon');
  const nextLabel = nextPlanned?.label ?? 'nothing planned';

  return (
    <dl className="aos-wsstatus" data-testid="workspace-status" aria-label="Workspace status">
      <div className="aos-wsstatus-row">
        <dt>Now</dt>
        <dd data-testid="workspace-status-now">{nowLabel}</dd>
      </div>
      <div className="aos-wsstatus-row">
        <dt>Next</dt>
        <dd data-testid="workspace-status-next">{nextLabel}</dd>
      </div>
      {blocked && blocked > 0 ? (
        <div className="aos-wsstatus-row">
          <dt>Blocked</dt>
          <dd data-testid="workspace-status-blocked">
            <span className="aos-pill warn">{blocked} awaiting approval</span>
          </dd>
        </div>
      ) : null}
    </dl>
  );
}
