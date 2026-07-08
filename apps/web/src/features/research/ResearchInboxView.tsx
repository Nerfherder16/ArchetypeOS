import React, { useCallback, useEffect, useState } from 'react';
import { fetchProjects, fetchResearchNotes, type ResearchNote } from '../../api';

const errorMessage = (err: unknown): string =>
  err instanceof Error ? err.message : 'Request failed';

// A research note tagged with the human-readable name of the project it belongs
// to, so the aggregated inbox can show provenance (which project each note came
// from).
type InboxItem = ResearchNote & { projectName: string };

// Lit signal-bars for a 0..1 confidence, per the ReuseView primitive:
// round(confidence * 5), clamped to 0..5.
function litBars(confidence: number): number {
  const lit = Math.round(confidence * 5);
  return Math.max(0, Math.min(5, lit));
}

// Compact horizontal confidence meter reusing the `.aos-bars`/`.aos-bar` 5-bar
// primitive (tokens.css) plus the numeric readout. Ranks a note's confidence.
function ConfidenceMeter({ confidence }: { confidence: number }) {
  const lit = litBars(confidence);
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 9 }}>
      <div className="aos-bars" aria-hidden="true">
        {[0, 1, 2, 3, 4].map((i) => (
          <span key={i} className={i < lit ? 'aos-bar lit' : 'aos-bar'} />
        ))}
      </div>
      <span
        className="aos-mono"
        style={{ fontSize: 13, fontWeight: 600, letterSpacing: '-0.01em' }}
        aria-label={`confidence ${confidence.toFixed(2)}`}
      >
        {confidence.toFixed(2)}
      </span>
    </div>
  );
}

type LoadResult = {
  items: InboxItem[];
  projectCount: number;
};

// Aggregate every research note across the operator's projects into one
// confidence-ranked inbox. A per-project notes fetch that fails is SKIPPED via
// Promise.allSettled — one bad project never fails the whole inbox. Throws only
// if the top-level `fetchProjects()` itself fails (surfaced as the error state).
async function loadInbox(): Promise<LoadResult> {
  const projects = await fetchProjects();
  const settled = await Promise.allSettled(projects.map((p) => fetchResearchNotes(p.id)));
  const items: InboxItem[] = [];
  settled.forEach((result, index) => {
    if (result.status !== 'fulfilled') {
      return; // skip a project whose notes could not be loaded
    }
    const project = projects[index];
    for (const note of result.value) {
      items.push({ ...note, projectName: project.name });
    }
  });
  // Highest confidence first (stable numeric compare).
  items.sort((a, b) => b.confidence - a.confidence);
  return { items, projectCount: projects.length };
}

function ResearchNoteCard({ item }: { item: InboxItem }) {
  return (
    <li className="aos-hud glass aos-card" data-testid="research-note-card">
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 12, flexWrap: 'wrap' }}>
        <h3 style={{ margin: 0, fontSize: 15, fontWeight: 600 }}>{item.title}</h3>
        {item.freshness ? (
          <span className="aos-pill info">{item.freshness}</span>
        ) : null}
      </div>
      <span className="aos-eyebrow" style={{ display: 'block', marginTop: 6 }}>
        {item.projectName}
      </span>
      <div style={{ marginTop: 10 }}>
        <ConfidenceMeter confidence={item.confidence} />
      </div>
      {item.summary ? (
        <p
          className="aos-muted"
          style={{
            margin: '10px 0 0',
            fontSize: 13,
            display: '-webkit-box',
            WebkitLineClamp: 3,
            WebkitBoxOrient: 'vertical',
            overflow: 'hidden',
          }}
        >
          {item.summary}
        </p>
      ) : null}
      {/* AOS-CONTRACT-001: surface the findings + sources the backend records. */}
      {item.findings && item.findings.length > 0 ? (
        <ul className="aos-muted" data-testid="research-note-findings" style={{ margin: '8px 0 0', paddingLeft: 18, fontSize: 12.5 }}>
          {item.findings.slice(0, 4).map((finding, i) => (
            <li key={i}>{finding}</li>
          ))}
        </ul>
      ) : null}
      {item.sources && item.sources.length > 0 ? (
        <div className="aos-mono aos-muted" data-testid="research-note-sources" style={{ margin: '8px 0 0', fontSize: 11 }}>
          {item.sources.length} source{item.sources.length === 1 ? '' : 's'}: {item.sources.slice(0, 3).join(', ')}
          {item.sources.length > 3 ? ' …' : ''}
        </div>
      ) : null}
    </li>
  );
}

export function ResearchInboxView() {
  const [items, setItems] = useState<InboxItem[] | null>(null);
  const [projectCount, setProjectCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await loadInbox();
      setItems(result.items);
      setProjectCount(result.projectCount);
    } catch (err) {
      // Graceful degradation: a missing/absent API (static preview, backend
      // down) must never throw or blank the screen — surface a readable notice.
      setItems(null);
      setProjectCount(0);
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const total = items?.length ?? 0;
  const isEmpty = items !== null && items.length === 0;

  return (
    <section className="aos-view" data-testid="research-view">
      <div className="aos-view-head">
        <span className="aos-eyebrow" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ color: 'var(--signal)' }} aria-hidden="true">
            &#9672;
          </span>
          Research · Research Inbox
        </span>
        <h2 style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
          Research inbox
          {items !== null && total > 0 ? (
            <span className="aos-pill info" data-testid="research-count">
              {total} note{total === 1 ? '' : 's'} across {projectCount} project
              {projectCount === 1 ? '' : 's'}
            </span>
          ) : null}
        </h2>
      </div>

      {error ? (
        <div className="aos-hud glass aos-card">
          <span className="aos-eyebrow">Research inbox</span>
          <p role="alert" className="aos-error" data-testid="research-error" style={{ marginTop: 8 }}>
            Research unavailable: {error}
          </p>
          <p className="aos-muted" style={{ margin: '8px 0 0', fontSize: 13 }}>
            The inbox aggregates <span className="aos-mono">GET /projects</span> and each project&apos;s{' '}
            <span className="aos-mono">/research-notes</span>. Once the API is reachable, captured
            research notes collect here ranked by confidence.
          </p>
        </div>
      ) : loading && items === null ? (
        <div className="aos-hud glass aos-card">
          <p className="aos-muted" data-testid="research-loading" style={{ margin: 0 }}>
            Loading the research inbox…
          </p>
        </div>
      ) : isEmpty ? (
        <div className="aos-hud glass aos-card">
          <span className="aos-eyebrow">Research inbox</span>
          <p className="aos-muted" data-testid="research-empty" style={{ margin: '8px 0 0' }}>
            No research yet — notes captured for your projects will collect here.
          </p>
        </div>
      ) : items !== null ? (
        <ul className="aos-rows" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {items.map((item) => (
            <ResearchNoteCard key={item.id} item={item} />
          ))}
        </ul>
      ) : null}

      {/* Non-goal footnote (AOS-RES-001): this inbox surfaces the research notes
          the platform already stores, ranked by confidence. The Research
          Engine's web-sourced ranked dossiers, source-quality ladder, and
          continuous-research signals are planned engines — a future enrichment,
          not built here. */}
      <p className="aos-mono aos-muted" style={{ margin: '16px 0 0', fontSize: 11.5 }}>
        This inbox ranks stored <span className="aos-mono">research notes</span> by confidence. The
        Research Engine&apos;s web-sourced ranked dossiers, source-quality ladder, and
        continuous-research signals are a future enrichment.
      </p>
    </section>
  );
}
