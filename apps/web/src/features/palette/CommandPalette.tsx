import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { ViewId } from '../../shell/Shell';
import { WORKSPACE_MODES } from '../../shell/workspaces';

// AOS-UX-IA-001 (deliverable 1) — global command palette. A Cmd/Ctrl+K modal
// overlay to fuzzy-jump between the live surfaces without hunting the rail.
// Purely additive: it reads the same WORKSPACE_MODES the rail uses and calls the
// shell's `navigate` (the useHashRoute setter), so navigation stays URL-routed.

type PaletteItem = {
  view: ViewId;
  label: string;
  modeLabel: string;
};

// Flatten the workspace modes into the routable live surfaces, labelled with
// their mode so "Command" vs "Council" stay distinguishable while searching.
const LIVE_ITEMS: PaletteItem[] = WORKSPACE_MODES.flatMap((mode) =>
  mode.surfaces
    .filter((surface): surface is typeof surface & { view: ViewId } =>
      surface.status === 'live' && surface.view !== undefined,
    )
    .map((surface) => ({ view: surface.view, label: surface.label, modeLabel: mode.label })),
);

export function CommandPalette({ navigate }: { navigate: (view: ViewId) => void }) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [activeIndex, setActiveIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement | null>(null);
  // Restore focus to whatever was focused before the palette opened.
  const restoreFocusRef = useRef<HTMLElement | null>(null);

  const results = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) {
      return LIVE_ITEMS;
    }
    return LIVE_ITEMS.filter(
      (item) =>
        item.label.toLowerCase().includes(q) || item.modeLabel.toLowerCase().includes(q),
    );
  }, [query]);

  const close = useCallback(() => {
    setOpen(false);
    setQuery('');
    setActiveIndex(0);
    restoreFocusRef.current?.focus?.();
  }, []);

  const select = useCallback(
    (item: PaletteItem | undefined) => {
      if (!item) {
        return;
      }
      navigate(item.view);
      close();
    },
    [navigate, close],
  );

  // Global toggle: Cmd/Ctrl+K opens (or closes) the palette from anywhere.
  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault();
        setOpen((prev) => {
          if (!prev) {
            restoreFocusRef.current = document.activeElement as HTMLElement | null;
          }
          return !prev;
        });
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, []);

  // Focus the input when opened; reset the highlighted row.
  useEffect(() => {
    if (open) {
      setActiveIndex(0);
      // Focus after the modal paints.
      const id = window.setTimeout(() => inputRef.current?.focus(), 0);
      return () => window.clearTimeout(id);
    }
    return undefined;
  }, [open]);

  // Keep the highlight in range as the result set shrinks while typing.
  useEffect(() => {
    setActiveIndex((prev) => (prev >= results.length ? Math.max(0, results.length - 1) : prev));
  }, [results.length]);

  if (!open) {
    return null;
  }

  const onInputKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Escape') {
      event.preventDefault();
      close();
    } else if (event.key === 'ArrowDown') {
      event.preventDefault();
      setActiveIndex((prev) => (results.length === 0 ? 0 : (prev + 1) % results.length));
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      setActiveIndex((prev) => (results.length === 0 ? 0 : (prev - 1 + results.length) % results.length));
    } else if (event.key === 'Enter') {
      event.preventDefault();
      select(results[activeIndex]);
    }
  };

  return (
    <div
      className="aos-palette-backdrop"
      data-testid="command-palette-backdrop"
      onClick={close}
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 1000,
        display: 'flex',
        alignItems: 'flex-start',
        justifyContent: 'center',
        paddingTop: '12vh',
        background: 'rgba(0, 0, 0, 0.55)',
      }}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Command palette"
        data-testid="command-palette"
        className="aos-hud glass aos-card"
        onClick={(event) => event.stopPropagation()}
        style={{ width: 'min(560px, 92vw)', padding: 12 }}
      >
        <input
          ref={inputRef}
          type="text"
          className="aos-input"
          data-testid="command-palette-input"
          placeholder="Jump to a surface…"
          aria-label="Search surfaces"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          onKeyDown={onInputKeyDown}
          style={{ width: '100%' }}
        />
        {results.length === 0 ? (
          <p className="aos-muted" data-testid="command-palette-empty" style={{ margin: '10px 2px 2px' }}>
            No matching surfaces.
          </p>
        ) : (
          <ul className="aos-rows" style={{ marginTop: 10, maxHeight: '46vh', overflowY: 'auto' }}>
            {results.map((item, index) => (
              <li key={item.view}>
                <button
                  type="button"
                  data-testid="command-palette-item"
                  className={`aos-linkbtn${index === activeIndex ? ' sel' : ''}`}
                  aria-selected={index === activeIndex}
                  onMouseEnter={() => setActiveIndex(index)}
                  onClick={() => select(item)}
                  style={{ display: 'flex', justifyContent: 'space-between', width: '100%', gap: 12 }}
                >
                  <span>{item.label}</span>
                  <span className="aos-rowmeta">{item.modeLabel}</span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
