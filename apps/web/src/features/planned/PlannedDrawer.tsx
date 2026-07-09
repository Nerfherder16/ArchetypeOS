import { useEffect } from 'react';
import type { Surface } from '../../shell/workspaces';
import { PLANNED_SURFACES } from '../../shell/planned';

// AOS-UX-IA-001 (deliverable 2) — the Planned drawer. Clicking a "soon" surface
// in the rail opens this side panel with an honest description of what the
// planned surface is intended to be, instead of the chip being a dead control.
// Purely presentational: App owns the selected-surface state and passes it in.
export function PlannedDrawer({
  surface,
  onClose,
}: {
  surface: Surface | null;
  onClose: () => void;
}) {
  // Close on Escape while open.
  useEffect(() => {
    if (!surface) {
      return undefined;
    }
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onClose();
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [surface, onClose]);

  if (!surface) {
    return null;
  }

  const info = PLANNED_SURFACES[surface.id];
  const summary =
    info?.summary ??
    'This surface is on the system map but not built yet. It will appear here once it ships.';

  return (
    <div
      className="aos-drawer-backdrop"
      data-testid="planned-drawer-backdrop"
      onClick={onClose}
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 1000,
        display: 'flex',
        justifyContent: 'flex-end',
        background: 'rgba(0, 0, 0, 0.5)',
      }}
    >
      <aside
        role="dialog"
        aria-modal="true"
        aria-label={`Planned surface: ${surface.label}`}
        data-testid="planned-drawer"
        className="aos-hud glass"
        onClick={(event) => event.stopPropagation()}
        style={{
          width: 'min(420px, 92vw)',
          height: '100%',
          padding: 20,
          overflowY: 'auto',
          borderLeft: '1px solid var(--frame)',
        }}
      >
        <div
          style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}
        >
          <span className="aos-pill info" data-testid="planned-drawer-badge">Planned</span>
          <button
            type="button"
            className="aos-btn-ghost aos-btn-sm"
            data-testid="planned-drawer-close"
            aria-label="Close"
            onClick={onClose}
          >
            Close
          </button>
        </div>

        <h2 style={{ margin: '14px 0 4px' }} data-testid="planned-drawer-title">
          {surface.label}
        </h2>

        {info?.phase ? (
          <p className="aos-mono aos-muted" data-testid="planned-drawer-phase" style={{ margin: '0 0 12px' }}>
            {info.phase}
          </p>
        ) : null}

        <p style={{ margin: '0 0 12px', lineHeight: 1.5 }} data-testid="planned-drawer-summary">
          {summary}
        </p>

        {info?.ticket ? (
          <p className="aos-mono aos-muted" data-testid="planned-drawer-ticket" style={{ margin: 0 }}>
            {info.ticket}
          </p>
        ) : null}

        <p className="aos-muted" style={{ marginTop: 16, fontSize: 12 }}>
          Not built yet — this is a planned surface from the system map.
        </p>
      </aside>
    </div>
  );
}
